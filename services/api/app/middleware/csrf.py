"""CSRF protection using the double-submit cookie pattern.

Mutating browser requests must send:
  X-CSRF-Token: <value matching the non-HttpOnly CSRF cookie>

The session cookie stays HttpOnly. A separate CSRF cookie (readable by JS)
is set on login and via GET /api/v1/auth/csrf.

API clients that authenticate with Bearer tokens are exempt.
In development/testing the check is lenient (warn only).
"""

from __future__ import annotations

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
    "/api/v1/auth/csrf",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF token on mutating browser-originated requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not _should_check_csrf(request):
            return await call_next(request)

        csrf_header: str | None = request.headers.get("X-CSRF-Token")
        csrf_cookie: str | None = request.cookies.get(settings.csrf_cookie_name)

        if not csrf_header:
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

        if not csrf_cookie or csrf_header != csrf_cookie:
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
    auth_header: str | None = request.headers.get("Authorization", "")
    if auth_header and auth_header.lower().startswith("bearer "):
        return False

    return True


validate_csrf = CSRFMiddleware
