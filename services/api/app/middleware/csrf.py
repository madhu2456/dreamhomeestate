"""CSRF protection middleware using the double-submit cookie pattern.

For browser-based requests to mutating endpoints (POST/PUT/PATCH/DELETE),
the request must include an X-CSRF-Token header whose value matches the
session cookie value.  API clients that authenticate with Bearer tokens
are exempt.

In development mode the check is lenient — it warns but does not block.
"""

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_ROUTE_PREFIXES = (
    "/api/v1/webhooks/",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/password-reset-request",
    "/api/v1/auth/password-reset",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF token on mutating browser-originated requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not _should_check_csrf(request):
            return await call_next(request)

        csrf_token: str | None = request.headers.get("X-CSRF-Token")
        session_token: str | None = request.cookies.get(settings.session_cookie_name)

        if not csrf_token:
            logger.warning(
                "csrf_token_missing",
                method=request.method,
                path=request.url.path,
                sec_fetch_site=request.headers.get("sec-fetch-site", "missing"),
            )
            if settings.is_development:
                request.state.csrf_validated = False
                return await call_next(request)
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )

        if csrf_token != session_token:
            logger.warning(
                "csrf_token_mismatch",
                method=request.method,
                path=request.url.path,
            )
            if settings.is_development:
                request.state.csrf_validated = False
                return await call_next(request)
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch"},
            )

        request.state.csrf_validated = True
        return await call_next(request)


def _should_check_csrf(request: Request) -> bool:
    """Return True if this request requires CSRF validation."""
    if request.method not in MUTATING_METHODS:
        return False

    path = request.url.path
    for prefix in SKIP_ROUTE_PREFIXES:
        if path.startswith(prefix):
            return False

    # API clients that authenticate with Bearer tokens skip CSRF.
    # CSRF is a browser-originated attack; Bearer clients manage tokens themselves.
    auth_header: str | None = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return False

    return True


validate_csrf = CSRFMiddleware
