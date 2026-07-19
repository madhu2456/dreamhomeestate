"""Worker package."""

from app.worker.celery_app import app

__all__ = ["app"]
