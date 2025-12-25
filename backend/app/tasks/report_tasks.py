from datetime import datetime, date, timedelta
from decimal import Decimal
from celery import shared_task
from sqlalchemy import select, func

from app.tasks.celery_app import celery_app
from app.tasks.campaign_tasks import get_sync_session
from app.core.config import settings


@celery_app.task(name="app.tasks.report_tasks.generate_daily_report")
def generate_daily_report():
    """Generate daily collection report for all organizations."""
    session = get_sync_session()

    try:
        from app.models.organization import Organization

        organizations = session.execute(
            select(Organization).where(Organization.is_active == True)
        ).scalars().all()

        for org in organizations:
            generate_org_daily_report.delay(str(org.id))

        return {"status": "success", "orgs_processed": len(organizations)}

    finally:
        session.close()


@celery_app.task(name="app.tasks.report_tasks.generate_org_daily_report")
def generate_org_daily_report(org_id: str):
    """Generate daily report for a specific organization."""
    session = get_sync_session()

    try:
        from app.models.loan import Loan
        from app.models.case import Case
        from app.models.communication import Communication
        from app.models.payment import Payment
        from app.models.campaign import Campaign

        yesterday = date.today() - timedelta(days=1)
        start_of_day = datetime.combine(yesterday, datetime.min.time())
        end_of_day = datetime.combine(yesterday, datetime.max.time())

        # Portfolio summary
        total_outstanding = session.execute(
            select(func.sum(Loan.total_outstanding)).where(
                Loan.organization_id == org_id,
                Loan.status == "active"
            )
        ).scalar() or Decimal(0)

        total_overdue = session.execute(
            select(func.sum(Loan.overdue_amount)).where(
                Loan.organization_id == org_id,
                Loan.status == "active"
            )
        ).scalar() or Decimal(0)

        # Collection summary
        collected = session.execute(
            select(func.sum(Payment.amount)).where(
                Payment.organization_id == org_id,
                Payment.payment_date == yesterday,
                Payment.status == "confirmed"
            )
        ).scalar() or Decimal(0)

        # Cases summary
        cases_opened = session.execute(
            select(func.count(Case.id)).where(
                Case.organization_id == org_id,
                Case.created_at >= start_of_day,
                Case.created_at <= end_of_day
            )
        ).scalar() or 0

        cases_resolved = session.execute(
            select(func.count(Case.id)).where(
                Case.organization_id == org_id,
                Case.resolution_date >= start_of_day,
                Case.resolution_date <= end_of_day
            )
        ).scalar() or 0

        # Communications summary
        total_calls = session.execute(
            select(func.count(Communication.id)).where(
                Communication.organization_id == org_id,
                Communication.channel == "call",
                Communication.initiated_at >= start_of_day,
                Communication.initiated_at <= end_of_day
            )
        ).scalar() or 0

        connected_calls = session.execute(
            select(func.count(Communication.id)).where(
                Communication.organization_id == org_id,
                Communication.channel == "call",
                Communication.status == "completed",
                Communication.duration_seconds > 0,
                Communication.initiated_at >= start_of_day,
                Communication.initiated_at <= end_of_day
            )
        ).scalar() or 0

        total_talk_time = session.execute(
            select(func.sum(Communication.duration_seconds)).where(
                Communication.organization_id == org_id,
                Communication.channel == "call",
                Communication.initiated_at >= start_of_day,
                Communication.initiated_at <= end_of_day
            )
        ).scalar() or 0

        # Bucket distribution
        bucket_dist = {}
        bucket_result = session.execute(
            select(Loan.bucket, func.count(Loan.id)).where(
                Loan.organization_id == org_id,
                Loan.status == "active"
            ).group_by(Loan.bucket)
        )
        for row in bucket_result:
            bucket_dist[row[0] or "unknown"] = row[1]

        # Campaign summary
        active_campaigns = session.execute(
            select(func.count(Campaign.id)).where(
                Campaign.organization_id == org_id,
                Campaign.status == "running"
            )
        ).scalar() or 0

        report_data = {
            "report_date": yesterday.isoformat(),
            "organization_id": org_id,
            "portfolio": {
                "total_outstanding": float(total_outstanding),
                "total_overdue": float(total_overdue),
                "overdue_percentage": round(float(total_overdue) / float(total_outstanding) * 100, 2) if total_outstanding else 0
            },
            "collection": {
                "amount_collected": float(collected),
                "collection_rate": round(float(collected) / float(total_overdue) * 100, 2) if total_overdue else 0
            },
            "cases": {
                "opened": cases_opened,
                "resolved": cases_resolved,
                "net_change": cases_opened - cases_resolved
            },
            "communications": {
                "total_calls": total_calls,
                "connected_calls": connected_calls,
                "contact_rate": round(connected_calls / total_calls * 100, 2) if total_calls else 0,
                "total_talk_time_minutes": total_talk_time // 60
            },
            "bucket_distribution": bucket_dist,
            "active_campaigns": active_campaigns,
            "generated_at": datetime.utcnow().isoformat()
        }

        # TODO: Store report in database or send via email
        # For now, just return the data
        return report_data

    finally:
        session.close()


@celery_app.task(name="app.tasks.report_tasks.export_cases_report")
def export_cases_report(org_id: str, filters: dict):
    """Export cases report to Excel/CSV."""
    session = get_sync_session()

    try:
        import pandas as pd
        from io import BytesIO
        from app.models.case import Case
        from app.models.loan import Loan
        from app.models.borrower import Borrower

        query = select(Case, Loan, Borrower).join(
            Loan, Case.loan_id == Loan.id
        ).join(
            Borrower, Loan.borrower_id == Borrower.id
        ).where(
            Case.organization_id == org_id
        )

        # Apply filters
        if filters.get("status"):
            query = query.where(Case.status == filters["status"])
        if filters.get("bucket"):
            query = query.where(Loan.bucket == filters["bucket"])

        result = session.execute(query)

        data = []
        for case, loan, borrower in result:
            data.append({
                "Case Number": case.case_number,
                "Status": case.status,
                "Priority": case.priority,
                "Borrower Name": borrower.full_name,
                "Phone": borrower.primary_phone,
                "Loan Account": loan.loan_account_number,
                "Loan Type": loan.loan_type,
                "Outstanding": float(loan.total_outstanding) if loan.total_outstanding else 0,
                "Overdue": float(loan.overdue_amount),
                "DPD": loan.dpd,
                "Bucket": loan.bucket,
                "Total Attempts": case.total_attempts,
                "Last Contact": case.last_contact_date.isoformat() if case.last_contact_date else "",
                "Created": case.created_at.isoformat()
            })

        df = pd.DataFrame(data)

        # Generate Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cases')

        # TODO: Upload to MinIO and return URL
        file_data = output.getvalue()

        return {
            "status": "success",
            "rows": len(data),
            "file_size": len(file_data)
        }

    finally:
        session.close()


@celery_app.task(name="app.tasks.report_tasks.generate_agent_performance_report")
def generate_agent_performance_report(org_id: str, date_from: str, date_to: str):
    """Generate agent performance report."""
    session = get_sync_session()

    try:
        from app.models.user import User
        from app.models.communication import Communication
        from datetime import datetime

        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)

        # Get all agents
        agents = session.execute(
            select(User).where(
                User.organization_id == org_id,
                User.role.in_(["agent", "manager"]),
                User.is_active == True
            )
        ).scalars().all()

        agent_data = []
        for agent in agents:
            # Get communication stats
            total_calls = session.execute(
                select(func.count(Communication.id)).where(
                    Communication.agent_id == agent.id,
                    Communication.channel == "call",
                    Communication.initiated_at >= start_date,
                    Communication.initiated_at <= end_date
                )
            ).scalar() or 0

            connected = session.execute(
                select(func.count(Communication.id)).where(
                    Communication.agent_id == agent.id,
                    Communication.channel == "call",
                    Communication.status == "completed",
                    Communication.duration_seconds > 0,
                    Communication.initiated_at >= start_date,
                    Communication.initiated_at <= end_date
                )
            ).scalar() or 0

            talk_time = session.execute(
                select(func.sum(Communication.duration_seconds)).where(
                    Communication.agent_id == agent.id,
                    Communication.channel == "call",
                    Communication.initiated_at >= start_date,
                    Communication.initiated_at <= end_date
                )
            ).scalar() or 0

            promises = session.execute(
                select(func.count(Communication.id)).where(
                    Communication.agent_id == agent.id,
                    Communication.outcome == "promise_to_pay",
                    Communication.initiated_at >= start_date,
                    Communication.initiated_at <= end_date
                )
            ).scalar() or 0

            agent_data.append({
                "agent_id": str(agent.id),
                "agent_name": agent.full_name,
                "total_calls": total_calls,
                "connected_calls": connected,
                "contact_rate": round(connected / total_calls * 100, 2) if total_calls else 0,
                "talk_time_minutes": talk_time // 60,
                "avg_call_duration": round(talk_time / connected, 0) if connected else 0,
                "promises_secured": promises,
                "promise_rate": round(promises / connected * 100, 2) if connected else 0
            })

        return {
            "status": "success",
            "period": {"from": date_from, "to": date_to},
            "agents": agent_data
        }

    finally:
        session.close()
