from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import asyncio

from celery import shared_task
from sqlalchemy import select, update, or_, and_
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.core.config import settings

# Outcomes that should trigger retry
RETRYABLE_OUTCOMES = ["no_answer", "busy", "voicemail", "failed", "network_error"]


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

        now = datetime.utcnow()

        # Get pending borrowers OR those due for retry
        pending = session.execute(
            select(CampaignBorrower).where(
                CampaignBorrower.campaign_id == campaign_id,
                or_(
                    CampaignBorrower.status == "pending",
                    and_(
                        CampaignBorrower.status == "retry_scheduled",
                        CampaignBorrower.next_attempt_at <= now
                    )
                ),
                CampaignBorrower.attempt_count < campaign.max_attempts_per_borrower
            )
            .order_by(CampaignBorrower.next_attempt_at.asc().nullsfirst())
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
    """Initiate a single campaign call using the configured provider."""
    import httpx
    import os

    session = get_sync_session()

    try:
        # Get campaign to check provider
        from app.models.campaign import Campaign
        campaign = session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        ).scalar_one_or_none()

        # Determine which provider to use
        provider = None
        if campaign:
            provider = campaign.telephony_provider

        if not provider:
            provider = os.getenv("VOICE_AI_PROVIDER", "bolna")

        # For AI calls, use appropriate Voice AI provider
        if use_ai and borrower_context:
            if provider == "exotel":
                result = _make_exotel_call(
                    phone_number=phone_number,
                    borrower_context=borrower_context,
                    campaign_id=campaign_id,
                    campaign_borrower_id=campaign_borrower_id
                )
            else:
                # Default to Bolna
                result = _make_voice_ai_call(
                    phone_number=phone_number,
                    borrower_context=borrower_context,
                    campaign_id=campaign_id,
                    campaign_borrower_id=campaign_borrower_id
                )

            if result.get("success"):
                # Update campaign borrower with call ID
                from app.models.campaign import CampaignBorrower
                cb = session.execute(
                    select(CampaignBorrower).where(
                        CampaignBorrower.id == campaign_borrower_id
                    )
                ).scalar_one_or_none()

                if cb:
                    cb.status = "in_progress"
                    cb.outcome_details = {"call_id": result.get("call_id")}
                    session.commit()

                return result
            else:
                raise Exception(result.get("message", "Voice AI call failed"))

        # For non-AI calls, use telephony service
        call_request = {
            "to_number": phone_number,
            "use_ai": use_ai,
            "campaign_id": campaign_id,
            "campaign_borrower_id": campaign_borrower_id
        }

        if borrower_context:
            call_request.update(borrower_context)

        response = httpx.post(
            f"{settings.telephony_url}/calls/initiate",
            json=call_request,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        # Update campaign borrower status on failure
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
        except Exception:
            pass

        raise
    finally:
        session.close()


def _make_voice_ai_call(
    phone_number: str,
    borrower_context: dict,
    campaign_id: str,
    campaign_borrower_id: str
) -> dict:
    """Make a Voice AI call using the configured provider."""
    import httpx
    import os

    # Use Voice AI provider API
    provider = os.getenv("VOICE_AI_PROVIDER", "bolna").lower()

    if provider == "bolna":
        api_key = os.getenv("BOLNA_API_KEY")
        agent_id = os.getenv("BOLNA_AGENT_ID")

        if not api_key or not agent_id:
            return {"success": False, "message": "BOLNA_API_KEY or BOLNA_AGENT_ID not configured"}

        payload = {
            "agent_id": agent_id,
            "recipient_phone_number": phone_number,
            "user_data": {
                "borrower_name": borrower_context.get("borrower_name", "Customer"),
                "outstanding_amount": str(borrower_context.get("outstanding_amount", 0)),
                "emi_amount": str(borrower_context.get("emi_amount", 0)),
                "dpd": str(borrower_context.get("dpd", 0)),
                "loan_type": borrower_context.get("loan_type", "Loan"),
                "case_id": borrower_context.get("case_id", ""),
                "campaign_id": campaign_id,
                "campaign_borrower_id": campaign_borrower_id
            }
        }

        try:
            response = httpx.post(
                "https://api.bolna.ai/call",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )

            print(f"[Voice AI] Call response: {response.status_code} - {response.text}")

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail") or error_data.get("message") or str(error_data)
                except Exception:
                    error_msg = response.text
                return {"success": False, "message": error_msg}

            data = response.json()
            return {
                "success": True,
                "call_id": data.get("execution_id"),
                "status": data.get("status", "queued")
            }

        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": False, "message": f"Unknown provider: {provider}"}


def _make_exotel_call(
    phone_number: str,
    borrower_context: dict,
    campaign_id: str,
    campaign_borrower_id: str
) -> dict:
    """Make a call using direct Exotel integration."""
    import httpx
    import os
    import base64

    api_key = os.getenv("EXOTEL_API_KEY")
    api_token = os.getenv("EXOTEL_API_TOKEN")
    sid = os.getenv("EXOTEL_SID")
    subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api")
    caller_id = os.getenv("EXOTEL_CALLER_ID")
    webhook_url = os.getenv("EXOTEL_WEBHOOK_URL")

    if not all([api_key, api_token, sid, caller_id]):
        return {"success": False, "message": "Exotel configuration incomplete"}

    # Build auth header
    credentials = f"{api_key}:{api_token}"
    encoded = base64.b64encode(credentials.encode()).decode()

    # Prepare call data with custom field for callback
    custom_field = f"{campaign_id}:{campaign_borrower_id}"

    data = {
        "From": caller_id,
        "To": phone_number,
        "CallerId": caller_id,
        "TimeLimit": "300",
        "Record": "true",
        "CustomField": custom_field,
    }

    if webhook_url:
        data["StatusCallback"] = f"{webhook_url}/status"

    try:
        response = httpx.post(
            f"https://{subdomain}.exotel.com/v1/Accounts/{sid}/Calls/connect.json",
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=data,
            timeout=30.0
        )

        print(f"[Exotel] Call response: {response.status_code} - {response.text}")

        if response.status_code >= 400:
            return {"success": False, "message": response.text}

        result = response.json()
        call_data = result.get("Call", {})

        return {
            "success": True,
            "call_id": call_data.get("Sid"),
            "status": call_data.get("Status", "queued")
        }

    except Exception as e:
        return {"success": False, "message": str(e)}


@celery_app.task(name="app.tasks.campaign_tasks.schedule_retry")
def schedule_retry(
    campaign_id: str,
    campaign_borrower_id: str,
    outcome: str
):
    """Schedule a retry for a failed call attempt."""
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

        # Check if max attempts reached
        if cb.attempt_count >= campaign.max_attempts_per_borrower:
            cb.status = "failed"
            cb.last_attempt_outcome = outcome
            campaign.total_failed += 1
            session.commit()
            return {"status": "max_attempts_reached"}

        # Get retry delays from campaign
        retry_delays = campaign.retry_delays_minutes or [30, 120, 480]
        delay_idx = min(cb.attempt_count - 1, len(retry_delays) - 1)
        delay_minutes = retry_delays[delay_idx]

        # Schedule retry
        cb.status = "retry_scheduled"
        cb.next_attempt_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        cb.last_attempt_outcome = outcome

        session.commit()

        return {
            "status": "retry_scheduled",
            "next_attempt_at": cb.next_attempt_at.isoformat(),
            "delay_minutes": delay_minutes
        }

    finally:
        session.close()


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

        # Check if this is a retryable outcome
        if outcome in RETRYABLE_OUTCOMES:
            # Schedule retry instead of marking completed
            cb.last_attempt_outcome = outcome
            session.commit()

            # Trigger retry scheduling
            schedule_retry.delay(campaign_id, campaign_borrower_id, outcome)
            return {"status": "retry_scheduled", "outcome": outcome}

        # Update campaign borrower as completed
        cb.status = "completed"
        cb.outcome = outcome
        cb.outcome_details = details
        cb.last_attempt_outcome = outcome

        # Update campaign stats
        campaign.total_contacted += 1
        if outcome in ["promise_to_pay", "payment_done", "callback_scheduled"]:
            campaign.total_successful += 1

        # Update results summary
        results = campaign.results_summary or {}
        results[outcome] = results.get(outcome, 0) + 1
        campaign.results_summary = results

        session.commit()

        return {"status": "success", "outcome": outcome}

    finally:
        session.close()
