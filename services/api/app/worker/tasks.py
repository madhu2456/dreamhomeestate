"""Celery task definitions — outbox processor, job executor, scheduled publishing."""

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.models import JobStatus, PublicationJob, PublicationOutbox
from app.services.lock import acquire_lock, job_lock_key, outbox_lock_key, release_lock, scheduled_lock_key
from app.services.publication import PublicationService
from app.worker.celery_app import app

logger = structlog.get_logger(__name__)

settings = get_settings()

_engine = None
_session_factory = None


def _get_session_factory():
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_async_engine(
            settings.database_url,
            poolclass=NullPool,
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def _run_in_async(func, *args, **kwargs):
    session_factory = _get_session_factory()
    async with session_factory() as db:
        return await func(db, *args, **kwargs)


@app.task(name="app.worker.tasks.health_check")
def health_check() -> dict:
    """Simple health-check task for beat scheduler."""
    logger.info("health_check_task_ran")
    return {"status": "ok"}


@app.task(name="app.worker.tasks.process_outbox", bind=True, max_retries=3, default_retry_delay=30)
def process_outbox(self) -> dict:
    """Process pending publication outbox entries."""
    lock_owner = None
    try:
        lock_owner = asyncio.run(acquire_lock(outbox_lock_key(), ttl_seconds=60))
        if not lock_owner:
            logger.info("outbox_lock_contended", message="Another worker holds the outbox lock")
            return {"processed": 0, "failed": 0, "skipped": True}
    except Exception:
        logger.warning("outbox_lock_error", message="Could not acquire outbox lock, proceeding anyway")

    processed = 0
    failed = 0

    async def _process():
        nonlocal processed, failed
        session_factory = _get_session_factory()
        async with session_factory() as db:
            from app.repositories.publication import PublicationOutboxRepository

            repo = PublicationOutboxRepository(db)
            entries = await repo.list_pending(limit=50)

            for entry in entries:
                try:
                    if entry.event_type == "job.queued":
                        from app.repositories.publication import PublicationJobRepository

                        job_repo = PublicationJobRepository(db)
                        job = await job_repo.get_by_id(entry.aggregate_id)
                        if job and job.status == JobStatus.queued:
                            svc = PublicationService(db)
                            await svc.execute_job(job)

                    await repo.mark_processed(entry)
                    processed += 1
                except Exception as exc:
                    logger.error("outbox_processing_failed", entry_id=str(entry.id), error=str(exc))
                    await repo.mark_failed(entry)
                    failed += 1

    try:
        asyncio.run(_process())
    except Exception as exc:
        logger.error("outbox_processor_error", error=str(exc))
        raise self.retry(exc=exc)

    if lock_owner:
        try:
            asyncio.run(release_lock(outbox_lock_key(), lock_owner))
        except Exception:
            pass

    return {"processed": processed, "failed": failed}


@app.task(name="app.worker.tasks.execute_job", bind=True, max_retries=3, default_retry_delay=60)
def execute_job(self, job_id: str) -> dict:
    """Execute a single publication job by ID."""
    lock_owner = None
    try:
        lock_key = job_lock_key(job_id)
        lock_owner = asyncio.run(acquire_lock(lock_key, ttl_seconds=600))
        if not lock_owner:
            logger.warning("job_lock_contended", job_id=job_id, message="Job already being executed by another worker")
            raise self.retry(exc=Exception(f"Job {job_id} locked by another worker"), countdown=30)
    except Exception as exc:
        if isinstance(exc, self.retry.__class__):
            raise
        logger.warning("job_lock_error", job_id=job_id, error=str(exc))

    async def _execute():
        session_factory = _get_session_factory()
        async with session_factory() as db:
            from app.repositories.publication import PublicationJobRepository

            job_repo = PublicationJobRepository(db)
            job = await job_repo.get_by_id(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            svc = PublicationService(db)
            result = await svc.execute_job(job)
            return {
                "job_id": str(result.id),
                "status": result.status.value,
                "error_code": result.error_code,
                "error_message": result.error_message,
            }

    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error("job_execution_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)
    finally:
        if lock_owner:
            try:
                asyncio.run(release_lock(job_lock_key(job_id), lock_owner))
            except Exception:
                pass


@app.task(name="app.worker.tasks.process_scheduled")
def process_scheduled() -> dict:
    """Beat task: queue approved+scheduled jobs that are due."""
    lock_owner = None
    try:
        lock_owner = asyncio.run(acquire_lock(scheduled_lock_key(), ttl_seconds=120))
        if not lock_owner:
            logger.info("scheduled_lock_contended")
            return {"processed": 0, "skipped": True}
    except Exception:
        pass

    processed = 0

    async def _process():
        nonlocal processed
        session_factory = _get_session_factory()
        async with session_factory() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(PublicationJob).where(
                    PublicationJob.status == JobStatus.approved,
                    PublicationJob.scheduled_at.isnot(None),
                    PublicationJob.scheduled_at <= now,
                )
            )
            jobs = list(result.scalars().all())

            for job in jobs:
                svc = PublicationService(db)
                from app.repositories.publication import PublicationJobRepository
                job_repo = PublicationJobRepository(db)
                current = await job_repo.get_by_id(job.id)
                if current and current.status == JobStatus.approved:
                    await svc._enqueue_job(current)
                    processed += 1

    try:
        asyncio.run(_process())
    except Exception as exc:
        logger.error("scheduled_processing_error", error=str(exc))

    if lock_owner:
        try:
            asyncio.run(release_lock(scheduled_lock_key(), lock_owner))
        except Exception:
            pass

    return {"processed": processed}


# Register beat schedule
from celery.schedules import crontab

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

