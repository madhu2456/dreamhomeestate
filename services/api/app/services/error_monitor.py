"""Error monitoring integration point — pluggable backends (Sentry / Datadog / no-op).

When no provider is configured all methods are safe no-ops that only log.
"""

import uuid
from functools import lru_cache
from typing import TYPE_CHECKING

import structlog

from app.config import get_settings

if TYPE_CHECKING:
    from starlette.requests import Request

logger = structlog.get_logger(__name__)


class ErrorMonitor:
    """Centralized error capture with pluggable backends.

    The monitor is always safe to call — when no DSN or provider is configured
    it degrades gracefully to structured logging only.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._sentry_initialized: bool = False
        self._sentry_sdk: object | None = None

    def _ensure_sentry(self) -> None:
        """Lazy-init the Sentry SDK when a DSN is configured.

        Import errors are caught so the application runs without ``sentry_sdk``
        installed.
        """
        if self._sentry_initialized:
            return
        self._sentry_initialized = True

        dsn = self._settings.sentry_dsn
        if not dsn:
            return

        try:
            import sentry_sdk  # type: ignore[import-untyped]

            sentry_sdk.init(
                dsn=str(dsn),
                environment=self._settings.env,
                traces_sample_rate=0.1,
            )
            self._sentry_sdk = sentry_sdk
            logger.info("sentry_initialized")
        except ImportError:
            logger.warning("sentry_sdk_not_installed")
        except Exception:
            logger.exception("sentry_init_failed")

    def capture_exception(
        self,
        exc: Exception,
        context: dict | None = None,
        request: "Request | None" = None,
    ) -> str:
        """Log an exception with full context and optionally ship to Sentry/Datadog.

        Returns an error event ID (uuid hex) that can be returned to the caller
        for tracing.
        """
        event_id = uuid.uuid4().hex

        log_kwargs: dict = {
            "error_event_id": event_id,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "exc_info": True,
        }
        if context:
            log_kwargs["error_context"] = context

        if request is not None:
            try:
                log_kwargs["path"] = request.url.path
                log_kwargs["method"] = request.method
            except Exception:
                pass

        logger.error("error_captured", **log_kwargs)

        # Sentry
        if self._settings.sentry_dsn:
            self._ensure_sentry()
            if self._sentry_sdk is not None:
                try:
                    self._sentry_sdk.capture_exception(exc)  # type: ignore[union-attr]
                except Exception:
                    logger.exception("sentry_capture_failed")

        # Datadog stub — logs intent; replace with real SDK in the future
        if self._settings.error_monitor_provider == "datadog":
            logger.info(
                "datadog_integration_stub",
                error_event_id=event_id,
                error=repr(exc),
            )

        return event_id

    def set_user_context(self, user_id: str, org_id: str | None = None) -> None:
        """Attach user identity to subsequent error reports.

        Call this after authentication so every captured error includes the
        responsible user / org for debugging.
        """
        structlog.contextvars.bind_contextvars(
            error_user_id=user_id,
            error_org_id=org_id or "",
        )

        if self._settings.sentry_dsn:
            self._ensure_sentry()
            if self._sentry_sdk is not None:
                try:
                    self._sentry_sdk.set_user({"id": user_id})  # type: ignore[union-attr]
                except Exception:
                    pass


@lru_cache
def get_error_monitor() -> ErrorMonitor:
    """Singleton factory for the error monitor."""
    return ErrorMonitor()
