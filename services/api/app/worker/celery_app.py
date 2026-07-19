"""Celery application configuration with Redis broker and beat schedule placeholder."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

app = Celery(
    "realestate_worker",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=["app.worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

# Beat schedule placeholder — tasks will be populated in later phases
app.conf.beat_schedule = {}

# Example scheduled task (uncomment when tasks exist):
# app.conf.beat_schedule["health_check"] = {
#     "task": "app.worker.tasks.health_check",
#     "schedule": crontab(minute="*/5"),
# }
