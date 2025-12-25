from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import asyncio

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.core.config import settings


def get_sync_session():
    """Get synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.sync_database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(name="app.tasks.campaign_tasks.check_and_execute_campaigns")
def check_and_execute_campaigns():
    """Check for scheduled campaigns and execute them."""
    session = get_sync_session()

    try:
        from app.models.campaign import Campaign

        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%a").lower()

        # Find campaigns that should be running
        campaigns = session.execute(
            select(Campaign).where(
                Campaign.status.in_(["scheduled", "running"]),
                Campaign.scheduled_start <= now,
                Campaign.allowed_start_time <= current_time,
                Campaign.allowed_end_time >= current_time
            )
        ).scalars().all()

        for campaign in campaigns:
            # Check if current day is allowed
            if current_day not in campaign.allowed_days:
                continue

            # Check if campaign should end
            if campaign.scheduled_end and campaign.scheduled_end <= now:
                campaign.status = "completed"
                campaign.actual_end = now
                continue

            # Start campaign if scheduled
            if campaign.status == "scheduled":
                campaign.status = "running"
                campaign.actual_start = now

            # Execute campaign calls
            execute_campaign_batch.delay(str(campaign.id))

        session.commit()

    finally:
        session.close()


@celery_app.task(name="app.tasks.campaign_tasks.execute_campaign_batch")
def execute_campaign_batch(campaign_id: str, batch_size: int = 10):
    """Execute a batch of campaign calls."""
    session = get_sync_session()

    try:
        from app.models.campaign import Campaign, CampaignBorrower
        from app.models.borrower import Borrower

        campaign = session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        ).scalar_one_or_none()

        if not campaign or campaign.status != "running":
            return {"status": "skipped", "reason": "Campaign not running"}

        # Get pending borrowers
        pending = session.execute(
            select(CampaignBorrower).where(
                CampaignBorrower.campaign_id == campaign_id,
                CampaignBorrower.status == "pending",
                CampaignBorrower.attempt_count < campaign.max_attempts_per_borrower
            )
            .order_by(CampaignBorrower.priority.desc())
            .limit(batch_size)
        ).scalars().all()

        if not pending:
            # No more pending - mark campaign complete
            campaign.status = "completed"
            campaign.actual_end = datetime.utcnow()
            session.commit()
            return {"status": "completed", "reason": "No pending borrowers"}

        calls_initiated = 0

        for cb in pending:
            # Get borrower with loan info
            borrower = session.execute(
                select(Borrower).where(Borrower.id == cb.borrower_id)
            ).scalar_one_or_none()

            if not borrower or borrower.do_not_call:
                cb.status = "skipped"
                continue

            # Build borrower context for AI calls
            borrower_context = None
            if campaign.ai_enabled:
                # Get loan and case info for context
                from app.models.loan import Loan
                from app.models.case import Case

                loan = session.execute(
                    select(Loan).where(Loan.borrower_id == borrower.id)
                    .order_by(Loan.created_at.desc())
                ).scalars().first()

                # Get active case for this borrower
                case = session.execute(
                    select(Case).where(
                        Case.borrower_id == borrower.id,
                        Case.status.notin_(["closed", "resolved"])
                    ).order_by(Case.created_at.desc())
                ).scalars().first()

                borrower_context = {
                    "borrower_id": str(borrower.id),
                    "case_id": str(case.id) if case else None,
                    "borrower_name": borrower.name,
                    "outstanding_amount": float(loan.outstanding_amount) if loan else 0,
                    "emi_amount": float(loan.emi_amount) if loan else 0,
                    "dpd": loan.dpd if loan else 0,
                    "loan_type": loan.loan_type if loan else "Loan",
                    "language": borrower.preferred_language or "hi"
                }

            # Queue the call
            initiate_campaign_call.delay(
                str(campaign_id),
                str(cb.id),
                borrower.primary_phone,
                campaign.ai_enabled,
                borrower_context
            )

            cb.status = "queued"
            cb.attempt_count += 1
            cb.last_attempt_at = datetime.utcnow()
            calls_initiated += 1

        # Update campaign stats
        campaign.total_attempted += calls_initiated

        session.commit()

        return {"status": "success", "calls_initiated": calls_initiated}

    finally:
        session.close()


@celery_app.task(name="app.tasks.campaign_tasks.initiate_campaign_call")
def initiate_campaign_call(
    campaign_id: str,
    campaign_borrower_id: str,
    phone_number: str,
    use_ai: bool,
    borrower_context: dict = None
):
    """Initiate a single campaign call."""
    import httpx

    try:
        # Build call request with borrower context for AI
        call_request = {
            "to_number": phone_number,
            "use_ai": use_ai,
            "campaign_id": campaign_id,
            "campaign_borrower_id": campaign_borrower_id
        }

        # Add borrower context if provided (for AI calls)
        if borrower_context:
            call_request.update(borrower_context)

        # Call telephony service
        response = httpx.post(
            f"{settings.telephony_url}/calls/initiate",
            json=call_request,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        # Update campaign borrower status on failure
        session = get_sync_session()
        try:
            from app.models.campaign import CampaignBorrower
            cb = session.execute(
                select(CampaignBorrower).where(
                    CampaignBorrower.id == campaign_borrower_id
                )
            ).scalar_one_or_none()

            if cb:
                cb.status = "failed"
                cb.outcome_details = {"error": str(e)}
                session.commit()
        finally:
            session.close()

        raise


@celery_app.task(name="app.tasks.campaign_tasks.update_loan_buckets")
def update_loan_buckets():
    """Update all loan buckets based on current DPD."""
    session = get_sync_session()

    try:
        from app.models.loan import Loan

        # Get all active loans
        loans = session.execute(
            select(Loan).where(Loan.status == "active")
        ).scalars().all()

        updated = 0
        for loan in loans:
            old_bucket = loan.bucket
            loan.update_bucket()
            if loan.bucket != old_bucket:
                updated += 1

        session.commit()

        return {"status": "success", "updated": updated}

    finally:
        session.close()


@celery_app.task(name="app.tasks.campaign_tasks.handle_call_completion")
def handle_call_completion(
    campaign_id: str,
    campaign_borrower_id: str,
    outcome: str,
    details: dict
):
    """Handle campaign call completion."""
    session = get_sync_session()

    try:
        from app.models.campaign import Campaign, CampaignBorrower

        campaign = session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        ).scalar_one_or_none()

        cb = session.execute(
            select(CampaignBorrower).where(
                CampaignBorrower.id == campaign_borrower_id
            )
        ).scalar_one_or_none()

        if not campaign or not cb:
            return {"status": "error", "reason": "Not found"}

        # Update campaign borrower
        cb.status = "completed"
        cb.outcome = outcome
        cb.outcome_details = details

        # Update campaign stats
        campaign.total_contacted += 1
        if outcome in ["promise_to_pay", "payment_done"]:
            campaign.total_successful += 1

        # Update results summary
        results = campaign.results_summary or {}
        results[outcome] = results.get(outcome, 0) + 1
        campaign.results_summary = results

        session.commit()

        return {"status": "success"}

    finally:
        session.close()
