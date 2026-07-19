"""Celery application configuration with Redis broker and beat schedule placeholder."""

from celery import Celery

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

# Default beat schedule (tasks.py may extend/override on import)
app.conf.beat_schedule = {
    "process-outbox": {
        "task": "app.worker.tasks.process_outbox",
        "schedule": 15.0,
    },
    "process-scheduled": {
        "task": "app.worker.tasks.process_scheduled",
        "schedule": 60.0,
    },
}
