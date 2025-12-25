from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.models.loan import Loan
from app.models.case import Case
from app.models.communication import Communication
from app.models.payment import Payment


async def calculate_collection_metrics(
    db: AsyncSession,
    org_id: UUID,
    date_from: datetime,
    date_to: datetime
) -> Dict[str, Any]:
    """Calculate collection performance metrics."""

    # Total collected
    total_collected = await db.scalar(
        select(func.sum(Payment.amount))
        .where(Payment.organization_id == org_id)
        .where(Payment.payment_date >= date_from.date())
        .where(Payment.payment_date <= date_to.date())
        .where(Payment.status == "confirmed")
    ) or Decimal(0)

    # Total outstanding at start (approximate)
    total_outstanding = await db.scalar(
        select(func.sum(Loan.total_outstanding))
        .where(Loan.organization_id == org_id)
        .where(Loan.status == "active")
    ) or Decimal(0)

    # Collection rate
    collection_rate = (float(total_collected) / float(total_outstanding) * 100) if total_outstanding else 0

    # Cases resolved
    cases_resolved = await db.scalar(
        select(func.count(Case.id))
        .where(Case.organization_id == org_id)
        .where(Case.status == "resolved")
        .where(Case.resolution_date >= date_from)
        .where(Case.resolution_date <= date_to)
    ) or 0

    # Contact attempts
    total_attempts = await db.scalar(
        select(func.count(Communication.id))
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
        .where(Communication.initiated_at >= date_from)
        .where(Communication.initiated_at <= date_to)
    ) or 0

    successful_contacts = await db.scalar(
        select(func.count(Communication.id))
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
        .where(Communication.status == "completed")
        .where(Communication.duration_seconds > 0)
        .where(Communication.initiated_at >= date_from)
        .where(Communication.initiated_at <= date_to)
    ) or 0

    contact_rate = (successful_contacts / total_attempts * 100) if total_attempts else 0

    return {
        "total_collected": float(total_collected),
        "total_outstanding": float(total_outstanding),
        "collection_rate": round(collection_rate, 2),
        "cases_resolved": cases_resolved,
        "total_attempts": total_attempts,
        "successful_contacts": successful_contacts,
        "contact_rate": round(contact_rate, 2)
    }


async def get_agent_leaderboard(
    db: AsyncSession,
    org_id: UUID,
    date_from: datetime,
    date_to: datetime,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get agent performance leaderboard."""

    from app.models.user import User

    result = await db.execute(
        select(
            Communication.agent_id,
            func.count(Communication.id).label("total_calls"),
            func.sum(Communication.duration_seconds).label("total_duration"),
            func.count(func.nullif(Communication.outcome == "promise_to_pay", False)).label("promises")
        )
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
        .where(Communication.agent_id.isnot(None))
        .where(Communication.initiated_at >= date_from)
        .where(Communication.initiated_at <= date_to)
        .group_by(Communication.agent_id)
        .order_by(func.count(Communication.id).desc())
        .limit(limit)
    )

    leaderboard = []
    for row in result.all():
        # Get agent name
        agent_result = await db.execute(
            select(User).where(User.id == row[0])
        )
        agent = agent_result.scalar_one_or_none()

        if agent:
            leaderboard.append({
                "agent_id": str(row[0]),
                "agent_name": agent.full_name,
                "total_calls": row[1],
                "total_duration_minutes": row[2] // 60 if row[2] else 0,
                "promises_secured": row[3] or 0
            })

    return leaderboard


async def get_bucket_flow(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30
) -> Dict[str, Any]:
    """Analyze bucket movement over time (roll rates)."""

    # This would ideally use TimescaleDB time_bucket function
    # For now, simplified implementation

    current_distribution = {}
    result = await db.execute(
        select(Loan.bucket, func.count(Loan.id))
        .where(Loan.organization_id == org_id)
        .where(Loan.status == "active")
        .group_by(Loan.bucket)
    )

    for row in result.all():
        current_distribution[row[0] or "unknown"] = row[1]

    return {
        "current_distribution": current_distribution,
        "period_days": days
        # TODO: Add historical tracking for roll rate calculation
    }


def calculate_efficiency_score(
    contact_rate: float,
    promise_rate: float,
    collection_rate: float,
    avg_handle_time: float
) -> float:
    """Calculate overall efficiency score (0-100)."""

    # Weighted scoring
    weights = {
        "contact_rate": 0.25,
        "promise_rate": 0.25,
        "collection_rate": 0.35,
        "handle_time": 0.15
    }

    # Normalize handle time (lower is better, assume 5 min is optimal)
    handle_time_score = max(0, min(100, (300 - avg_handle_time) / 3))

    score = (
        contact_rate * weights["contact_rate"] +
        promise_rate * weights["promise_rate"] +
        collection_rate * weights["collection_rate"] +
        handle_time_score * weights["handle_time"]
    )

    return round(min(100, max(0, score)), 2)
