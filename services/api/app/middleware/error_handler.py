"""ASGI middleware that catches unhandled exceptions and reports them via ErrorMonitor.

Returns a generic 500 response — no internal details are leaked to the client.
"""

import structlog
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.error_monitor import get_error_monitor

logger = structlog.get_logger(__name__)


class ErrorHandlerMiddleware:
    """Outermost ASGI middleware — catches unhandled exceptions from the entire stack.

    After capturing the exception it returns a safe, generic 500 response.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            error_monitor = get_error_monitor()

            # Build minimal request context from ASGI scope (avoid consuming receive)
            request = Request(scope)

            context: dict = {
                "path": scope.get("path", ""),
                "method": scope.get("method", ""),
                "query_string": scope.get("query_string", b"").decode("latin-1", errors="replace"),
            }

            error_monitor.capture_exception(exc, context=context, request=request)

            # Return a safe, generic 500 — do NOT leak internal error details
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
            await response(scope, receive, send)
