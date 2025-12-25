from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case as sql_case
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_manager
from app.models.user import User
from app.models.communication import Communication
from app.models.case import Case, CaseAssignment
from app.models.payment import Payment

router = APIRouter()


class AgentMetrics(BaseModel):
    agent_id: UUID
    agent_name: str
    total_calls: int = 0
    connected_calls: int = 0
    connect_rate: float = 0.0
    total_talk_time_minutes: int = 0
    avg_call_duration_seconds: float = 0.0
    calls_per_hour: float = 0.0
    total_sms: int = 0
    total_whatsapp: int = 0
    cases_assigned: int = 0
    cases_resolved: int = 0
    resolution_rate: float = 0.0
    promises_obtained: int = 0
    amount_collected: float = 0.0
    quality_score: float = 0.0


class LeaderboardEntry(BaseModel):
    rank: int
    agent_id: UUID
    agent_name: str
    avatar_url: Optional[str] = None
    metric_value: float
    metric_label: str


class AgentPerformanceResponse(BaseModel):
    agents: List[AgentMetrics]
    leaderboard_calls: List[LeaderboardEntry]
    leaderboard_collections: List[LeaderboardEntry]
    leaderboard_resolution: List[LeaderboardEntry]
    org_totals: dict


class AgentDetailResponse(BaseModel):
    agent: AgentMetrics
    daily_stats: List[dict]
    hourly_distribution: List[dict]
    outcome_distribution: dict
    recent_calls: List[dict]


@router.get("", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent performance metrics for the organization."""
    org_id = current_user.organization_id

    # Default to last 30 days
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    # Get all agents in the organization
    agents_result = await db.execute(
        select(User).where(
            User.organization_id == org_id,
            User.role.in_(["agent", "manager", "admin"]),
            User.is_active == True
        )
    )
    agents = agents_result.scalars().all()

    agent_metrics = []
    for agent in agents:
        metrics = await _calculate_agent_metrics(db, agent, date_from, date_to)
        agent_metrics.append(metrics)

    # Sort for leaderboards
    leaderboard_calls = sorted(agent_metrics, key=lambda x: x.total_calls, reverse=True)[:10]
    leaderboard_collections = sorted(agent_metrics, key=lambda x: x.amount_collected, reverse=True)[:10]
    leaderboard_resolution = sorted(agent_metrics, key=lambda x: x.resolution_rate, reverse=True)[:10]

    # Calculate org totals
    org_totals = {
        "total_calls": sum(a.total_calls for a in agent_metrics),
        "total_connected": sum(a.connected_calls for a in agent_metrics),
        "total_talk_time": sum(a.total_talk_time_minutes for a in agent_metrics),
        "total_collected": sum(a.amount_collected for a in agent_metrics),
        "total_cases_resolved": sum(a.cases_resolved for a in agent_metrics),
        "avg_connect_rate": sum(a.connect_rate for a in agent_metrics) / len(agent_metrics) if agent_metrics else 0,
    }

    return AgentPerformanceResponse(
        agents=agent_metrics,
        leaderboard_calls=[
            LeaderboardEntry(
                rank=i+1,
                agent_id=a.agent_id,
                agent_name=a.agent_name,
                metric_value=a.total_calls,
                metric_label="calls"
            ) for i, a in enumerate(leaderboard_calls)
        ],
        leaderboard_collections=[
            LeaderboardEntry(
                rank=i+1,
                agent_id=a.agent_id,
                agent_name=a.agent_name,
                metric_value=a.amount_collected,
                metric_label="collected"
            ) for i, a in enumerate(leaderboard_collections)
        ],
        leaderboard_resolution=[
            LeaderboardEntry(
                rank=i+1,
                agent_id=a.agent_id,
                agent_name=a.agent_name,
                metric_value=a.resolution_rate,
                metric_label="resolution %"
            ) for i, a in enumerate(leaderboard_resolution)
        ],
        org_totals=org_totals
    )


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent_detail(
    agent_id: UUID,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed performance metrics for a specific agent."""
    org_id = current_user.organization_id

    # Default to last 30 days
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    # Get agent
    agent_result = await db.execute(
        select(User).where(
            User.id == agent_id,
            User.organization_id == org_id
        )
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    metrics = await _calculate_agent_metrics(db, agent, date_from, date_to)

    # Get daily stats
    daily_stats = await _get_daily_stats(db, agent_id, date_from, date_to)

    # Get hourly distribution
    hourly_distribution = await _get_hourly_distribution(db, agent_id, date_from, date_to)

    # Get outcome distribution
    outcome_distribution = await _get_outcome_distribution(db, agent_id, date_from, date_to)

    # Get recent calls
    recent_calls = await _get_recent_calls(db, agent_id, limit=20)

    return AgentDetailResponse(
        agent=metrics,
        daily_stats=daily_stats,
        hourly_distribution=hourly_distribution,
        outcome_distribution=outcome_distribution,
        recent_calls=recent_calls
    )


async def _calculate_agent_metrics(
    db: AsyncSession,
    agent: User,
    date_from: datetime,
    date_to: datetime
) -> AgentMetrics:
    """Calculate performance metrics for an agent."""
    agent_id = agent.id

    # Get call stats
    call_stats = await db.execute(
        select(
            func.count(Communication.id).label("total_calls"),
            func.sum(
                sql_case(
                    (Communication.status == "completed", 1),
                    else_=0
                )
            ).label("connected_calls"),
            func.sum(Communication.duration_seconds).label("total_duration")
        ).where(
            Communication.agent_id == agent_id,
            Communication.channel == "call",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    )
    call_row = call_stats.first()
    total_calls = call_row.total_calls or 0
    connected_calls = call_row.connected_calls or 0
    total_duration = call_row.total_duration or 0

    # Get SMS/WhatsApp counts
    msg_stats = await db.execute(
        select(
            Communication.channel,
            func.count(Communication.id)
        ).where(
            Communication.agent_id == agent_id,
            Communication.channel.in_(["sms", "whatsapp"]),
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        ).group_by(Communication.channel)
    )
    msg_counts = {row[0]: row[1] for row in msg_stats.all()}

    # Get case stats
    case_stats = await db.execute(
        select(
            func.count(CaseAssignment.id).label("assigned"),
        ).where(
            CaseAssignment.agent_id == agent_id,
            CaseAssignment.assigned_at >= date_from,
            CaseAssignment.assigned_at <= date_to
        )
    )
    case_row = case_stats.first()
    cases_assigned = case_row.assigned if case_row else 0

    # Get resolved cases
    resolved_stats = await db.execute(
        select(func.count(Case.id)).where(
            Case.id.in_(
                select(CaseAssignment.case_id).where(
                    CaseAssignment.agent_id == agent_id,
                    CaseAssignment.is_active == True
                )
            ),
            Case.status == "resolved",
            Case.resolution_date >= date_from,
            Case.resolution_date <= date_to
        )
    )
    cases_resolved = resolved_stats.scalar() or 0

    # Get promises (PTP outcomes)
    promises_stats = await db.execute(
        select(func.count(Communication.id)).where(
            Communication.agent_id == agent_id,
            Communication.outcome == "promise_to_pay",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    )
    promises_obtained = promises_stats.scalar() or 0

    # Get amount collected (from payments linked to agent's cases)
    # This is simplified - in production you'd track which agent collected
    amount_collected = 0.0  # Would need Payment tracking per agent

    # Calculate derived metrics
    connect_rate = (connected_calls / total_calls * 100) if total_calls > 0 else 0
    avg_duration = (total_duration / connected_calls) if connected_calls > 0 else 0
    resolution_rate = (cases_resolved / cases_assigned * 100) if cases_assigned > 0 else 0

    # Calculate calls per hour (assuming 8-hour workday over the period)
    days_in_period = (date_to - date_from).days or 1
    work_hours = days_in_period * 8
    calls_per_hour = total_calls / work_hours if work_hours > 0 else 0

    # Quality score (composite metric)
    quality_score = _calculate_quality_score(
        connect_rate=connect_rate,
        resolution_rate=resolution_rate,
        avg_duration=avg_duration,
        promises_obtained=promises_obtained,
        total_calls=total_calls
    )

    return AgentMetrics(
        agent_id=agent_id,
        agent_name=agent.full_name,
        total_calls=total_calls,
        connected_calls=connected_calls,
        connect_rate=round(connect_rate, 1),
        total_talk_time_minutes=total_duration // 60,
        avg_call_duration_seconds=round(avg_duration, 1),
        calls_per_hour=round(calls_per_hour, 1),
        total_sms=msg_counts.get("sms", 0),
        total_whatsapp=msg_counts.get("whatsapp", 0),
        cases_assigned=cases_assigned,
        cases_resolved=cases_resolved,
        resolution_rate=round(resolution_rate, 1),
        promises_obtained=promises_obtained,
        amount_collected=amount_collected,
        quality_score=round(quality_score, 1)
    )


def _calculate_quality_score(
    connect_rate: float,
    resolution_rate: float,
    avg_duration: float,
    promises_obtained: int,
    total_calls: int
) -> float:
    """Calculate a composite quality score (0-100)."""
    # Weighted scoring
    # Connect rate: 25% (target: 40%+)
    connect_score = min(connect_rate / 40 * 25, 25)

    # Resolution rate: 30% (target: 20%+)
    resolution_score = min(resolution_rate / 20 * 30, 30)

    # Avg call duration: 20% (target: 120-300 seconds is optimal)
    if 120 <= avg_duration <= 300:
        duration_score = 20
    elif avg_duration < 120:
        duration_score = (avg_duration / 120) * 20
    else:
        duration_score = max(0, 20 - (avg_duration - 300) / 60)

    # Promise rate: 25% (target: 10% of calls)
    promise_rate = (promises_obtained / total_calls * 100) if total_calls > 0 else 0
    promise_score = min(promise_rate / 10 * 25, 25)

    return connect_score + resolution_score + duration_score + promise_score


async def _get_daily_stats(
    db: AsyncSession,
    agent_id: UUID,
    date_from: datetime,
    date_to: datetime
) -> List[dict]:
    """Get daily call stats for an agent."""
    result = await db.execute(
        select(
            func.date(Communication.initiated_at).label("date"),
            func.count(Communication.id).label("total_calls"),
            func.sum(
                sql_case(
                    (Communication.status == "completed", 1),
                    else_=0
                )
            ).label("connected"),
            func.sum(Communication.duration_seconds).label("duration")
        ).where(
            Communication.agent_id == agent_id,
            Communication.channel == "call",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        ).group_by(func.date(Communication.initiated_at))
        .order_by(func.date(Communication.initiated_at))
    )

    return [
        {
            "date": str(row.date),
            "total_calls": row.total_calls or 0,
            "connected": row.connected or 0,
            "duration_minutes": (row.duration or 0) // 60
        }
        for row in result.all()
    ]


async def _get_hourly_distribution(
    db: AsyncSession,
    agent_id: UUID,
    date_from: datetime,
    date_to: datetime
) -> List[dict]:
    """Get hourly call distribution for an agent."""
    result = await db.execute(
        select(
            func.extract("hour", Communication.initiated_at).label("hour"),
            func.count(Communication.id).label("calls"),
            func.sum(
                sql_case(
                    (Communication.status == "completed", 1),
                    else_=0
                )
            ).label("connected")
        ).where(
            Communication.agent_id == agent_id,
            Communication.channel == "call",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        ).group_by(func.extract("hour", Communication.initiated_at))
        .order_by(func.extract("hour", Communication.initiated_at))
    )

    return [
        {
            "hour": int(row.hour),
            "calls": row.calls or 0,
            "connected": row.connected or 0
        }
        for row in result.all()
    ]


async def _get_outcome_distribution(
    db: AsyncSession,
    agent_id: UUID,
    date_from: datetime,
    date_to: datetime
) -> dict:
    """Get outcome distribution for an agent's calls."""
    result = await db.execute(
        select(
            Communication.outcome,
            func.count(Communication.id)
        ).where(
            Communication.agent_id == agent_id,
            Communication.channel == "call",
            Communication.outcome.isnot(None),
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        ).group_by(Communication.outcome)
    )

    return {row[0]: row[1] for row in result.all()}


async def _get_recent_calls(
    db: AsyncSession,
    agent_id: UUID,
    limit: int = 20
) -> List[dict]:
    """Get recent calls for an agent."""
    from app.models.borrower import Borrower

    result = await db.execute(
        select(Communication)
        .where(
            Communication.agent_id == agent_id,
            Communication.channel == "call"
        )
        .order_by(Communication.initiated_at.desc())
        .limit(limit)
    )
    comms = result.scalars().all()

    calls = []
    for comm in comms:
        borrower_name = None
        if comm.borrower_id:
            borrower_result = await db.execute(
                select(Borrower).where(Borrower.id == comm.borrower_id)
            )
            borrower = borrower_result.scalar_one_or_none()
            if borrower:
                borrower_name = borrower.full_name

        calls.append({
            "id": str(comm.id),
            "borrower_name": borrower_name,
            "phone": comm.to_number,
            "status": comm.status,
            "outcome": comm.outcome,
            "duration_seconds": comm.duration_seconds,
            "initiated_at": comm.initiated_at.isoformat() if comm.initiated_at else None,
            "is_ai_handled": comm.is_ai_handled
        })

    return calls
