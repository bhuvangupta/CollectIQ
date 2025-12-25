from datetime import datetime, date, timedelta
from celery import shared_task
from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.tasks.campaign_tasks import get_sync_session
from app.core.config import settings


@celery_app.task(name="app.tasks.notification_tasks.send_daily_reminders")
def send_daily_reminders():
    """Send daily payment reminders for upcoming due dates."""
    session = get_sync_session()

    try:
        from app.models.loan import Loan
        from app.models.borrower import Borrower

        today = date.today()
        reminder_date = today + timedelta(days=3)  # 3 days before due

        # Find loans with upcoming due dates
        loans = session.execute(
            select(Loan).where(
                Loan.status == "active",
                Loan.next_due_date == reminder_date
            )
        ).scalars().all()

        sent = 0
        for loan in loans:
            borrower = session.execute(
                select(Borrower).where(Borrower.id == loan.borrower_id)
            ).scalar_one_or_none()

            if not borrower or borrower.do_not_sms:
                continue

            # Queue SMS
            send_sms_notification.delay(
                borrower.primary_phone,
                f"Dear {borrower.first_name}, your EMI of Rs {loan.emi_amount} "
                f"for loan {loan.loan_account_number} is due on {loan.next_due_date}. "
                f"Please pay on time to avoid late fees."
            )
            sent += 1

        return {"status": "success", "reminders_sent": sent}

    finally:
        session.close()


@celery_app.task(name="app.tasks.notification_tasks.send_sms_notification")
def send_sms_notification(phone_number: str, message: str):
    """Send an SMS notification."""
    import httpx

    try:
        response = httpx.post(
            f"{settings.telephony_url}/sms/send",
            json={
                "to_number": phone_number,
                "message": message
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.notification_tasks.send_whatsapp_notification")
def send_whatsapp_notification(
    phone_number: str,
    template_id: str,
    params: dict
):
    """Send a WhatsApp notification."""
    import httpx

    try:
        response = httpx.post(
            f"{settings.telephony_url}/whatsapp/send",
            json={
                "to_number": phone_number,
                "template_id": template_id,
                "template_params": params
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.notification_tasks.check_broken_promises")
def check_broken_promises():
    """Check for broken payment promises and update statuses."""
    session = get_sync_session()

    try:
        from app.models.payment import PaymentPromise
        from app.models.case import Case, CaseNote

        today = date.today()

        # Find overdue promises
        overdue_promises = session.execute(
            select(PaymentPromise).where(
                PaymentPromise.status == "pending",
                PaymentPromise.promised_date < today
            )
        ).scalars().all()

        broken = 0
        for promise in overdue_promises:
            promise.status = "broken"
            broken += 1

            # Add note to case if linked
            if promise.case_id:
                case = session.execute(
                    select(Case).where(Case.id == promise.case_id)
                ).scalar_one_or_none()

                if case:
                    note = CaseNote(
                        case_id=case.id,
                        content=f"Payment promise of Rs {promise.promised_amount} "
                                f"for {promise.promised_date} was broken.",
                        note_type="system",
                        is_system=True
                    )
                    session.add(note)

        session.commit()

        return {"status": "success", "broken_promises": broken}

    finally:
        session.close()


@celery_app.task(name="app.tasks.notification_tasks.send_promise_reminder")
def send_promise_reminder(promise_id: str):
    """Send reminder for upcoming promise date."""
    session = get_sync_session()

    try:
        from app.models.payment import PaymentPromise
        from app.models.borrower import Borrower
        from app.models.loan import Loan

        promise = session.execute(
            select(PaymentPromise).where(PaymentPromise.id == promise_id)
        ).scalar_one_or_none()

        if not promise or promise.status != "pending":
            return {"status": "skipped"}

        borrower = session.execute(
            select(Borrower).where(Borrower.id == promise.borrower_id)
        ).scalar_one_or_none()

        loan = session.execute(
            select(Loan).where(Loan.id == promise.loan_id)
        ).scalar_one_or_none()

        if borrower and not borrower.do_not_sms:
            send_sms_notification.delay(
                borrower.primary_phone,
                f"Dear {borrower.first_name}, this is a reminder that your "
                f"payment of Rs {promise.promised_amount} is due tomorrow. "
                f"Please ensure timely payment."
            )

            promise.reminder_sent = True
            promise.reminder_date = datetime.utcnow()
            session.commit()

            return {"status": "sent"}

        return {"status": "skipped"}

    finally:
        session.close()
