"""ASGI middleware that adds security-related HTTP response headers."""

from app.config import get_settings

settings = get_settings()


def _build_csp() -> str:
    """Build Content-Security-Policy header value from settings."""
    directives = []
    mapping = {
        "default-src": settings.csp_default_src,
        "script-src": settings.csp_script_src,
        "style-src": settings.csp_style_src,
        "img-src": settings.csp_img_src,
        "font-src": settings.csp_font_src,
        "connect-src": settings.csp_connect_src,
        "frame-ancestors": settings.csp_frame_ancestors,
        "form-action": settings.csp_form_action,
        "base-uri": settings.csp_base_uri,
    }
    for directive, value in mapping.items():
        if value:
            directives.append(f"{directive} {value}")
    return "; ".join(directives)


class SecurityHeadersMiddleware:
    """ASGI middleware that injects security headers on every response.

    Headers added:
      - Content-Security-Policy (configurable via settings)
      - X-Content-Type-Options: nosniff
      - X-Frame-Options: DENY
      - X-XSS-Protection: 0
      - Referrer-Policy: strict-origin-when-cross-origin
      - Permissions-Policy: camera=(), microphone=(), geolocation=()

    Important: never collapse multi-value headers (especially multiple
    ``Set-Cookie``) via ``dict(headers)`` — that drops all but the last cookie.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Keep as a list of pairs so repeated Set-Cookie headers survive
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                existing_lower = {k.decode("latin-1").lower() for k, _ in headers}

                security_headers: list[tuple[bytes, bytes]] = [
                    (b"content-security-policy", _build_csp().encode("latin-1")),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"0"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (
                        b"permissions-policy",
                        b"camera=(), microphone=(), geolocation=()",
                    ),
                ]

                for key, value in security_headers:
                    if key.decode("latin-1") not in existing_lower:
                        headers.append((key, value))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)
