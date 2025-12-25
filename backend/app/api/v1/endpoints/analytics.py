from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_agent_case_ids
from app.models.user import User
from app.models.loan import Loan
from app.models.case import Case
from app.models.communication import Communication
from app.models.payment import Payment
from app.models.campaign import Campaign

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics. Agents see stats for their assigned cases only."""
    org_id = current_user.organization_id
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    # Agent role: get assigned case IDs for filtering
    agent_case_ids = await get_agent_case_ids(current_user, db)
    is_agent = agent_case_ids is not None

    # For agents, we need loan IDs from their assigned cases
    agent_loan_ids = None
    if is_agent:
        if not agent_case_ids:
            # No assigned cases - return zeros
            return {
                "portfolio": {"total_outstanding": 0, "total_overdue": 0, "active_loans": 0, "overdue_percentage": 0},
                "cases": {"open_cases": 0, "resolved_today": 0},
                "collections": {"collected_this_month": 0},
                "communications": {"calls_today": 0, "successful_contacts_today": 0, "contact_rate": 0},
                "campaigns": {"active": 0}
            }
        # Get loan IDs for agent's assigned cases
        loan_result = await db.execute(
            select(Case.loan_id).where(Case.id.in_(agent_case_ids))
        )
        agent_loan_ids = [row[0] for row in loan_result.all()]

    # Portfolio stats
    portfolio_query = select(func.sum(Loan.total_outstanding)).where(
        Loan.organization_id == org_id, Loan.status == "active"
    )
    if agent_loan_ids is not None:
        portfolio_query = portfolio_query.where(Loan.id.in_(agent_loan_ids))
    total_outstanding = await db.scalar(portfolio_query) or 0

    overdue_query = select(func.sum(Loan.overdue_amount)).where(
        Loan.organization_id == org_id, Loan.status == "active"
    )
    if agent_loan_ids is not None:
        overdue_query = overdue_query.where(Loan.id.in_(agent_loan_ids))
    total_overdue = await db.scalar(overdue_query) or 0

    loans_query = select(func.count(Loan.id)).where(
        Loan.organization_id == org_id, Loan.status == "active"
    )
    if agent_loan_ids is not None:
        loans_query = loans_query.where(Loan.id.in_(agent_loan_ids))
    active_loans = await db.scalar(loans_query) or 0

    # Case stats
    open_query = select(func.count(Case.id)).where(
        Case.organization_id == org_id, Case.status.in_(["open", "in_progress"])
    )
    if agent_case_ids is not None:
        open_query = open_query.where(Case.id.in_(agent_case_ids))
    open_cases = await db.scalar(open_query) or 0

    resolved_query = select(func.count(Case.id)).where(
        Case.organization_id == org_id, Case.status == "resolved",
        func.date(Case.resolution_date) == today
    )
    if agent_case_ids is not None:
        resolved_query = resolved_query.where(Case.id.in_(agent_case_ids))
    resolved_today = await db.scalar(resolved_query) or 0

    # Collection stats (this month) - filter by loan
    collection_query = select(func.sum(Payment.amount)).where(
        Payment.organization_id == org_id, Payment.payment_date >= month_start,
        Payment.status == "confirmed"
    )
    if agent_loan_ids is not None:
        collection_query = collection_query.where(Payment.loan_id.in_(agent_loan_ids))
    collected_this_month = await db.scalar(collection_query) or 0

    # Communication stats (today) - filter by agent or case
    calls_query = select(func.count(Communication.id)).where(
        Communication.organization_id == org_id, Communication.channel == "call",
        func.date(Communication.initiated_at) == today
    )
    if is_agent:
        from sqlalchemy import or_
        calls_query = calls_query.where(
            or_(
                Communication.case_id.in_(agent_case_ids) if agent_case_ids else False,
                Communication.agent_id == current_user.id
            )
        )
    calls_today = await db.scalar(calls_query) or 0

    contacts_query = select(func.count(Communication.id)).where(
        Communication.organization_id == org_id, Communication.channel == "call",
        Communication.status == "completed", Communication.duration_seconds > 0,
        func.date(Communication.initiated_at) == today
    )
    if is_agent:
        from sqlalchemy import or_
        contacts_query = contacts_query.where(
            or_(
                Communication.case_id.in_(agent_case_ids) if agent_case_ids else False,
                Communication.agent_id == current_user.id
            )
        )
    successful_contacts_today = await db.scalar(contacts_query) or 0

    # Active campaigns - only show for managers/admins
    active_campaigns = 0
    if not is_agent:
        active_campaigns = await db.scalar(
            select(func.count(Campaign.id))
            .where(Campaign.organization_id == org_id)
            .where(Campaign.status == "running")
        ) or 0

    return {
        "portfolio": {
            "total_outstanding": float(total_outstanding),
            "total_overdue": float(total_overdue),
            "active_loans": active_loans,
            "overdue_percentage": round((float(total_overdue) / float(total_outstanding) * 100) if total_outstanding else 0, 2)
        },
        "cases": {
            "open_cases": open_cases,
            "resolved_today": resolved_today
        },
        "collections": {
            "collected_this_month": float(collected_this_month),
        },
        "communications": {
            "calls_today": calls_today,
            "successful_contacts_today": successful_contacts_today,
            "contact_rate": round((successful_contacts_today / calls_today * 100) if calls_today else 0, 2)
        },
        "campaigns": {
            "active": active_campaigns
        }
    }


@router.get("/portfolio/bucket-distribution")
async def get_bucket_distribution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get loan distribution by DPD bucket."""
    org_id = current_user.organization_id

    result = await db.execute(
        select(
            Loan.bucket,
            func.count(Loan.id).label("count"),
            func.sum(Loan.total_outstanding).label("outstanding"),
            func.sum(Loan.overdue_amount).label("overdue")
        )
        .where(Loan.organization_id == org_id)
        .where(Loan.status == "active")
        .group_by(Loan.bucket)
    )

    buckets = []
    for row in result.all():
        buckets.append({
            "bucket": row[0] or "unknown",
            "count": row[1],
            "outstanding": float(row[2] or 0),
            "overdue": float(row[3] or 0)
        })

    return {"buckets": buckets}


@router.get("/collections/trend")
async def get_collections_trend(
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily collection trend."""
    org_id = current_user.organization_id
    start_date = datetime.utcnow().date() - timedelta(days=days)

    result = await db.execute(
        select(
            Payment.payment_date,
            func.sum(Payment.amount).label("amount"),
            func.count(Payment.id).label("count")
        )
        .where(Payment.organization_id == org_id)
        .where(Payment.payment_date >= start_date)
        .where(Payment.status == "confirmed")
        .group_by(Payment.payment_date)
        .order_by(Payment.payment_date)
    )

    trend = []
    for row in result.all():
        trend.append({
            "date": row[0].isoformat(),
            "amount": float(row[1]),
            "count": row[2]
        })

    return {"trend": trend}


@router.get("/agents/performance")
async def get_agent_performance(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent performance metrics."""
    org_id = current_user.organization_id

    if not date_from:
        date_from = datetime.utcnow() - timedelta(days=30)
    if not date_to:
        date_to = datetime.utcnow()

    result = await db.execute(
        select(
            Communication.agent_id,
            func.count(Communication.id).label("total_calls"),
            func.sum(Communication.duration_seconds).label("total_duration"),
            func.count(case(
                (Communication.status == "completed", 1)
            )).label("connected_calls")
        )
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
        .where(Communication.agent_id.isnot(None))
        .where(Communication.initiated_at >= date_from)
        .where(Communication.initiated_at <= date_to)
        .group_by(Communication.agent_id)
    )

    agents = []
    for row in result.all():
        from app.models.user import User as UserModel
        agent_result = await db.execute(
            select(UserModel).where(UserModel.id == row[0])
        )
        agent = agent_result.scalar_one_or_none()

        if agent:
            agents.append({
                "agent_id": str(row[0]),
                "agent_name": agent.full_name,
                "total_calls": row[1],
                "total_duration_minutes": row[2] // 60 if row[2] else 0,
                "connected_calls": row[3] or 0,
                "contact_rate": round((row[3] / row[1] * 100) if row[1] else 0, 2)
            })

    return {"agents": agents}


@router.get("/communications/hourly")
async def get_hourly_distribution(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get hourly distribution of calls."""
    org_id = current_user.organization_id
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.extract("hour", Communication.initiated_at).label("hour"),
            func.count(Communication.id).label("count"),
            func.count(case(
                (Communication.status == "completed", 1)
            )).label("connected")
        )
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
        .where(Communication.initiated_at >= start_date)
        .group_by(func.extract("hour", Communication.initiated_at))
        .order_by("hour")
    )

    hourly = []
    for row in result.all():
        hourly.append({
            "hour": int(row[0]),
            "total": row[1],
            "connected": row[2] or 0,
            "contact_rate": round((row[2] / row[1] * 100) if row[1] else 0, 2)
        })

    return {"hourly": hourly}


@router.get("/disposition/breakdown")
async def get_disposition_breakdown(
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call disposition breakdown."""
    org_id = current_user.organization_id
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            Communication.disposition,
            Communication.sub_disposition,
            func.count(Communication.id).label("count")
        )
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
        .where(Communication.initiated_at >= start_date)
        .where(Communication.disposition.isnot(None))
        .group_by(Communication.disposition, Communication.sub_disposition)
    )

    dispositions = {}
    for row in result.all():
        disp = row[0]
        sub_disp = row[1]
        count = row[2]

        if disp not in dispositions:
            dispositions[disp] = {"total": 0, "sub_dispositions": {}}

        dispositions[disp]["total"] += count
        if sub_disp:
            dispositions[disp]["sub_dispositions"][sub_disp] = count

    return {"dispositions": dispositions}
