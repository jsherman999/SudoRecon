"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from backend.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "sudoguard",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_time_limit - 60,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "check-expired-provisions": {
        "task": "backend.tasks.maintenance_tasks.check_expired_provisions",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "cleanup-old-jobs": {
        "task": "backend.tasks.maintenance_tasks.cleanup_old_jobs",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

# Auto-discover tasks
celery_app.autodiscover_tasks(["backend.tasks"])
