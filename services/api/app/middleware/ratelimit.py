"""Rate limiting ASGI middleware backed by Redis (fixed-window counter).

Route groups and their default limits:
  - Webhook routes  (/api/v1/webhooks/)  → 100 req / 60 s per IP
  - Auth routes     (/api/v1/auth/login)  →   5 req / 60 s per IP
  - API routes      (/api/v1/)            →  60 req / 60 s per user/IP
  - Public routes   (everything else)     →  30 req / 60 s per IP

In development/testing mode (or when RATE_LIMIT_ENABLED=false) the
middleware never blocks requests.
"""

from __future__ import annotations

import json

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)

# ────────────────────────── route-group detection ──────────────────────────

# Match order matters — check "most specific" first.
ROUTE_GROUPS: list[tuple[str, str, str]] = [
    # (path-prefix, group-name, match-type)
    # match-type: "exact" or "prefix"
    ("/api/v1/webhooks/", "webhook", "prefix"),
    ("/api/v1/auth/login", "auth", "exact"),
    ("/api/v1/", "api", "prefix"),
]


def _classify_path(path: str) -> tuple[str, int, int]:
    """Return (group_name, limit, window_seconds) for a request path."""
    for prefix, group, match_type in ROUTE_GROUPS:  # noqa: B007
        if match_type == "exact":
            if path == prefix:
                break
        else:
            if path.startswith(prefix):
                break
    else:
        group = "public"

    match group:
        case "webhook":
            return group, settings.rate_limit_webhook, settings.rate_limit_webhook_window
        case "auth":
            return group, settings.rate_limit_auth, settings.rate_limit_auth_window
        case "api":
            return group, settings.rate_limit_api, settings.rate_limit_api_window
        case _:
            return "public", settings.rate_limit_public, settings.rate_limit_public_window


# ────────────────────────── helpers ────────────────────────────────────────


def _get_client_ip(scope: dict) -> str:
    """Extract the client IP from ASGI scope headers.

    Checks X-Forwarded-For (first entry when behind a proxy) then falls
    back to the direct client address.
    """
    headers = dict(scope.get("headers", []))
    forwarded = headers.get(b"x-forwarded-for")
    if forwarded:
        # Take the leftmost IP (the original client) when behind proxies.
        return forwarded.decode("latin-1").split(",")[0].strip()

    real_ip = headers.get(b"x-real-ip")
    if real_ip:
        return real_ip.decode("latin-1").strip()

    client = scope.get("client")
    if client:
        return client[0]

    return "unknown"


def _rate_limit_key(window: int, group: str, identifier: str) -> str:
    """Build a Redis key for the rate-limit counter.

    Example:  ratelimit:60:auth:192.168.1.1
    """
    return f"ratelimit:{window}:{group}:{identifier}"


# ────────────────────────── middleware ─────────────────────────────────────


class RateLimitMiddleware:
    """ASGI middleware that enforces per-route-group rate limits via Redis.

    Fixed-window algorithm: each key is increment-expired atomically.  When
    ``INCR`` returns 1 the key is brand-new so we set its TTL to the window
    size.  A count above the limit triggers a 429 response with a
    ``Retry-After`` header equal to the remaining window seconds.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Only enforce if the feature flag is on (disabled in tests / local).
        # Re-read settings each request so env overrides apply after import.
        current = get_settings()
        if not current.rate_limit_enabled or current.is_development:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        client_ip = _get_client_ip(scope)
        group, limit, window = _classify_path(path)
        key = _rate_limit_key(window, group, client_ip)

        dev_mode = current.is_development

        try:
            r = aioredis.from_url(current.redis_url, decode_responses=True)
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, window)

            blocked = count > limit
            if blocked:
                retry_after = await r.ttl(key)
            await r.aclose()

        except Exception:
            # Redis is unavailable — fail open so the site stays online.
            logger.error(
                "rate_limit_redis_error",
                path=path,
                ip=client_ip,
                group=group,
                exc_info=True,
            )
            await self.app(scope, receive, send)
            return

        if blocked:
            retry_after_int = max(int(retry_after), 1)
            logger.warning(
                "rate_limit_exceeded",
                path=path,
                ip=client_ip,
                group=group,
                limit=limit,
                window=window,
                count=count,
                retry_after=retry_after_int,
            )

            if dev_mode:
                # Log and let through.
                logger.info("rate_limit_dev_mode_pass", path=path, ip=client_ip)
                await self.app(scope, receive, send)
                return

            # --- 429 Too Many Requests ---
            body = json.dumps({
                "detail": "Too many requests",
                "retry_after_seconds": retry_after_int,
            }).encode("utf-8")

            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", str(retry_after_int).encode("latin-1")),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            })
            return

        # Under the limit — normal flow.
        await self.app(scope, receive, send)
