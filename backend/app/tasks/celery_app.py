from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "loan_collection",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=[
        "app.tasks.campaign_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.transcription_tasks",
        "app.tasks.report_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 min soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# DEV MODE: Run tasks synchronously without Redis/Worker
if settings.debug:
    celery_app.conf.update(
        task_always_eager=True,  # Run tasks immediately, not via broker
        task_eager_propagates=True,  # Propagate exceptions
    )

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Check and execute scheduled campaigns every minute
    "execute-campaigns": {
        "task": "app.tasks.campaign_tasks.check_and_execute_campaigns",
        "schedule": 60.0,  # Every minute
    },

    # Send payment reminders at 9 AM daily
    "daily-payment-reminders": {
        "task": "app.tasks.notification_tasks.send_daily_reminders",
        "schedule": crontab(hour=9, minute=0),
    },

    # Process pending transcriptions every 5 minutes
    "process-transcriptions": {
        "task": "app.tasks.transcription_tasks.process_pending_transcriptions",
        "schedule": 300.0,  # Every 5 minutes
    },

    # Generate daily reports at midnight
    "generate-daily-report": {
        "task": "app.tasks.report_tasks.generate_daily_report",
        "schedule": crontab(hour=0, minute=30),
    },

    # Update loan buckets based on DPD at 1 AM
    "update-loan-buckets": {
        "task": "app.tasks.campaign_tasks.update_loan_buckets",
        "schedule": crontab(hour=1, minute=0),
    },

    # Check for broken promises at 10 AM
    "check-broken-promises": {
        "task": "app.tasks.notification_tasks.check_broken_promises",
        "schedule": crontab(hour=10, minute=0),
    },
}
