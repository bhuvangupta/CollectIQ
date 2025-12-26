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
    days: int = Query(30, ge=7, le=90),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent performance metrics."""
    org_id = current_user.organization_id

    if not date_from:
        date_from = datetime.utcnow() - timedelta(days=days)
    if not date_to:
        date_to = datetime.utcnow()

    result = await db.execute(
        select(
            Communication.agent_id,
            func.count(Communication.id).label("total_calls"),
            func.sum(Communication.duration_seconds).label("total_duration"),
            func.count(case(
                (Communication.status == "completed", 1)
            )).label("connected_calls"),
            func.count(case(
                (Communication.outcome == "promise_to_pay", 1)
            )).label("promises_secured")
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
                "talk_time_minutes": (row[2] or 0) // 60,
                "connected_calls": row[3] or 0,
                "promises_secured": row[4] or 0,
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


# ============================================================================
# Campaign Analytics
# ============================================================================

@router.get("/campaigns/overview")
async def get_campaigns_overview(
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get overview analytics for all campaigns."""
    org_id = current_user.organization_id
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get all campaigns in period
    result = await db.execute(
        select(Campaign).where(
            Campaign.organization_id == org_id,
            Campaign.created_at >= start_date
        )
    )
    campaigns = result.scalars().all()

    # Aggregate stats
    total_campaigns = len(campaigns)
    total_attempted = sum(c.total_attempted for c in campaigns)
    total_contacted = sum(c.total_contacted for c in campaigns)
    total_successful = sum(c.total_successful for c in campaigns)
    total_cost = sum(float(c.actual_cost or 0) for c in campaigns)

    # By type breakdown
    by_type = {}
    for c in campaigns:
        t = c.campaign_type or "unknown"
        if t not in by_type:
            by_type[t] = {"count": 0, "attempted": 0, "contacted": 0, "successful": 0}
        by_type[t]["count"] += 1
        by_type[t]["attempted"] += c.total_attempted
        by_type[t]["contacted"] += c.total_contacted
        by_type[t]["successful"] += c.total_successful

    # By status breakdown
    by_status = {}
    for c in campaigns:
        s = c.status or "unknown"
        if s not in by_status:
            by_status[s] = 0
        by_status[s] += 1

    return {
        "period_days": days,
        "total_campaigns": total_campaigns,
        "total_attempted": total_attempted,
        "total_contacted": total_contacted,
        "total_successful": total_successful,
        "total_cost": round(total_cost, 2),
        "overall_contact_rate": round((total_contacted / total_attempted * 100) if total_attempted else 0, 2),
        "overall_success_rate": round((total_successful / total_contacted * 100) if total_contacted else 0, 2),
        "cost_per_contact": round((total_cost / total_contacted) if total_contacted else 0, 2),
        "cost_per_success": round((total_cost / total_successful) if total_successful else 0, 2),
        "by_type": by_type,
        "by_status": by_status
    }


@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed analytics for a specific campaign."""
    from app.models.campaign import CampaignBorrower
    org_id = current_user.organization_id

    # Get campaign
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == org_id
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get hourly breakdown
    hourly_result = await db.execute(
        select(
            func.extract("hour", CampaignBorrower.last_attempt_at).label("hour"),
            func.count(CampaignBorrower.id).label("attempts"),
            func.sum(case((CampaignBorrower.status == "completed", 1), else_=0)).label("completed")
        )
        .where(CampaignBorrower.campaign_id == campaign_id)
        .where(CampaignBorrower.last_attempt_at.isnot(None))
        .group_by(func.extract("hour", CampaignBorrower.last_attempt_at))
        .order_by("hour")
    )
    hourly = [{"hour": int(r[0]), "attempts": r[1], "completed": r[2] or 0} for r in hourly_result.all()]

    # Get daily trend
    daily_result = await db.execute(
        select(
            func.date(CampaignBorrower.last_attempt_at).label("date"),
            func.count(CampaignBorrower.id).label("attempts"),
            func.sum(case((CampaignBorrower.status == "completed", 1), else_=0)).label("completed")
        )
        .where(CampaignBorrower.campaign_id == campaign_id)
        .where(CampaignBorrower.last_attempt_at.isnot(None))
        .group_by(func.date(CampaignBorrower.last_attempt_at))
        .order_by("date")
    )
    daily = [{"date": str(r[0]), "attempts": r[1], "completed": r[2] or 0} for r in daily_result.all()]

    # Get outcome breakdown
    outcome_result = await db.execute(
        select(
            CampaignBorrower.outcome,
            func.count(CampaignBorrower.id)
        )
        .where(CampaignBorrower.campaign_id == campaign_id)
        .where(CampaignBorrower.outcome.isnot(None))
        .group_by(CampaignBorrower.outcome)
    )
    outcomes = {r[0]: r[1] for r in outcome_result.all()}

    # Get status breakdown
    status_result = await db.execute(
        select(
            CampaignBorrower.status,
            func.count(CampaignBorrower.id)
        )
        .where(CampaignBorrower.campaign_id == campaign_id)
        .group_by(CampaignBorrower.status)
    )
    statuses = {r[0]: r[1] for r in status_result.all()}

    # Conversion funnel
    total_targets = await db.scalar(
        select(func.count(CampaignBorrower.id))
        .where(CampaignBorrower.campaign_id == campaign_id)
    ) or 0

    attempted = campaign.total_attempted
    contacted = campaign.total_contacted
    successful = campaign.total_successful
    failed = campaign.total_failed or 0

    # Build funnel array for frontend visualization
    funnel_data = [
        {"stage": "targets", "count": total_targets, "percentage": 100.0},
        {"stage": "attempted", "count": attempted, "percentage": round((attempted / total_targets * 100) if total_targets else 0, 1)},
        {"stage": "contacted", "count": contacted, "percentage": round((contacted / total_targets * 100) if total_targets else 0, 1)},
        {"stage": "successful", "count": successful, "percentage": round((successful / total_targets * 100) if total_targets else 0, 1)},
    ]

    # Calculate avg duration from communications
    avg_duration_result = await db.execute(
        select(func.avg(Communication.duration_seconds))
        .where(Communication.campaign_id == campaign_id)
        .where(Communication.duration_seconds.isnot(None))
    )
    avg_duration = avg_duration_result.scalar() or 0

    # Transform hourly data to match frontend format
    hourly_trend = [
        {
            "hour": h["hour"],
            "attempts": h["attempts"],
            "successes": h["completed"],
            "success_rate": round((h["completed"] / h["attempts"] * 100) if h["attempts"] else 0, 1)
        }
        for h in hourly
    ]

    # Transform daily data to match frontend format
    daily_trend = [
        {
            "date": d["date"],
            "attempts": d["attempts"],
            "successes": d["completed"],
            "success_rate": round((d["completed"] / d["attempts"] * 100) if d["attempts"] else 0, 1)
        }
        for d in daily
    ]

    return {
        "campaign": {
            "id": str(campaign.id),
            "name": campaign.name,
            "campaign_type": campaign.campaign_type,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
            "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None
        },
        "stats": {
            "total_targets": total_targets,
            "total_attempted": attempted,
            "total_successful": successful,
            "total_failed": failed,
            "success_rate": round((successful / contacted * 100) if contacted else 0, 1),
            "avg_duration_seconds": float(avg_duration),
            "total_cost": float(campaign.actual_cost or 0)
        },
        "funnel": funnel_data,
        "hourly_trend": hourly_trend,
        "daily_trend": daily_trend,
        "outcomes": outcomes,
        "statuses": statuses
    }


# ============================================================================
# Transcript Search
# ============================================================================

@router.get("/transcripts/search")
async def search_transcripts(
    query: str = Query(..., min_length=2, alias="query", description="Search query"),
    channel: Optional[str] = Query(None, description="Filter by channel: call, sms, whatsapp"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search across call transcripts and message content."""
    from app.models.borrower import Borrower

    org_id = current_user.organization_id
    q = query  # Rename to avoid conflict with sqlalchemy query

    # Build search query
    db_query = select(Communication).where(
        Communication.organization_id == org_id
    )

    # Search in transcript, ai_summary, message_content
    from sqlalchemy import or_
    search_filter = or_(
        Communication.transcript.ilike(f"%{q}%"),
        Communication.ai_summary.ilike(f"%{q}%"),
        Communication.message_content.ilike(f"%{q}%"),
        Communication.notes.ilike(f"%{q}%")
    )
    db_query = db_query.where(search_filter)

    # Apply filters
    if channel:
        db_query = db_query.where(Communication.channel == channel)
    if outcome:
        db_query = db_query.where(Communication.outcome == outcome)
    if date_from:
        db_query = db_query.where(Communication.initiated_at >= date_from)
    if date_to:
        db_query = db_query.where(Communication.initiated_at <= date_to)

    # Get total count
    count_query = select(func.count()).select_from(db_query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply limit and ordering
    db_query = db_query.order_by(Communication.initiated_at.desc()).limit(limit)

    result = await db.execute(db_query)
    communications = result.scalars().all()

    # Build response matching frontend TranscriptSearchResult interface
    results = []
    for comm in communications:
        # Get borrower name
        borrower_name = "Unknown"
        if comm.borrower_id:
            b_result = await db.execute(
                select(Borrower.full_name).where(Borrower.id == comm.borrower_id)
            )
            borrower_name = b_result.scalar_one_or_none() or "Unknown"

        # Get case info
        case_id = None
        case_number = None
        if comm.case_id:
            case_result = await db.execute(
                select(Case.id, Case.case_number).where(Case.id == comm.case_id)
            )
            case_row = case_result.first()
            if case_row:
                case_id = str(case_row[0])
                case_number = case_row[1]

        # Find matching snippet and count matches
        snippet = ""
        match_count = 0
        for field in [comm.transcript, comm.ai_summary, comm.message_content, comm.notes]:
            if field and q.lower() in field.lower():
                # Count matches
                match_count += field.lower().count(q.lower())
                # Extract snippet around first match if not already found
                if not snippet:
                    idx = field.lower().find(q.lower())
                    start = max(0, idx - 50)
                    end = min(len(field), idx + len(q) + 100)
                    snippet = ("..." if start > 0 else "") + field[start:end] + ("..." if end < len(field) else "")

        results.append({
            "communication_id": str(comm.id),
            "case_id": case_id,
            "case_number": case_number or "N/A",
            "borrower_name": borrower_name,
            "channel": comm.channel,
            "initiated_at": comm.initiated_at.isoformat() if comm.initiated_at else None,
            "duration_seconds": comm.duration_seconds or 0,
            "is_ai_handled": comm.is_ai_handled,
            "transcript_snippet": snippet,
            "match_count": match_count
        })

    return {
        "results": results,
        "total": total,
        "query": q
    }


@router.get("/transcripts/{communication_id}")
async def get_transcript(
    communication_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full transcript for a communication."""
    from app.models.borrower import Borrower

    org_id = current_user.organization_id

    result = await db.execute(
        select(Communication).where(
            Communication.id == communication_id,
            Communication.organization_id == org_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Communication not found")

    # Get borrower info
    borrower_name = None
    if comm.borrower_id:
        b_result = await db.execute(
            select(Borrower).where(Borrower.id == comm.borrower_id)
        )
        borrower = b_result.scalar_one_or_none()
        if borrower:
            borrower_name = borrower.full_name

    return {
        "id": str(comm.id),
        "channel": comm.channel,
        "direction": comm.direction,
        "borrower_id": str(comm.borrower_id) if comm.borrower_id else None,
        "borrower_name": borrower_name,
        "to_number": comm.to_number,
        "from_number": comm.from_number,
        "status": comm.status,
        "outcome": comm.outcome,
        "disposition": comm.disposition,
        "sub_disposition": comm.sub_disposition,
        "duration_seconds": comm.duration_seconds,
        "is_ai_handled": comm.is_ai_handled,
        "initiated_at": comm.initiated_at.isoformat() if comm.initiated_at else None,
        "ended_at": comm.ended_at.isoformat() if comm.ended_at else None,
        "transcript": comm.transcript,
        "ai_summary": comm.ai_summary,
        "ai_entities": comm.ai_entities,
        "message_content": comm.message_content,
        "notes": comm.notes,
        "recording_url": comm.recording_url,
        "sentiment": comm.sentiment
    }
