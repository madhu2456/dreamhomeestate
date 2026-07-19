"""FastAPI application factory for RealEstateSocial."""

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import CorrelationIdMiddleware, setup_logging
from app.middleware import (
    ErrorHandlerMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    validate_csrf,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown events."""
    setup_logging()
    # Startup: nothing special needed for Phase 1
    yield
    # Shutdown: nothing special needed for Phase 1


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # --- Middleware stack ---
    # Order: ErrorHandler -> CORS -> SecurityHeaders -> CSRF -> RateLimit -> Correlation ID

    # Error handler — outermost, catches unhandled exceptions from the entire stack
    app.add_middleware(ErrorHandlerMiddleware)

    # CORS (handles preflight before anything else except error handling)
    origins = settings.cors_origins
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Security headers on every response
    app.add_middleware(SecurityHeadersMiddleware)

    # CSRF protection for mutating browser requests
    app.add_middleware(validate_csrf)

    # Rate limiting per route group (inner — close to route handlers)
    app.add_middleware(RateLimitMiddleware)

    # Correlation ID (innermost — runs after security checks, before route handlers)
    app.add_middleware(CorrelationIdMiddleware)

    # --- Exception handlers ---

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        from app.logging_config import get_correlation_id
        import structlog

        logger = structlog.get_logger(__name__)
        logger.error("unhandled_exception", error=str(exc), exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": get_correlation_id(),
            },
        )

    @app.exception_handler(status.HTTP_422_UNPROCESSABLE_ENTITY)
    async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
        from app.logging_config import get_correlation_id
        from fastapi.exceptions import RequestValidationError

        if isinstance(exc, RequestValidationError):
            errors = []
            for error in exc.errors():
                errors.append(
                    {
                        "loc": error.get("loc", []),
                        "msg": error.get("msg", ""),
                        "type": error.get("type", ""),
                    }
                )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": "Validation error",
                    "errors": errors,
                    "request_id": get_correlation_id(),
                },
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc), "request_id": get_correlation_id()},
        )

    # --- Routers ---

    from app.routers import (
        audit_router,
        auth_router,
        content_router,
        feature_flags_router,
        health_router,
        listing_media_router,
        listings_router,
        organizations_router,
        public_router,
        publications_router,
        social_accounts_router,
        users_router,
        webhook_router,
    )

    api_prefix = "/api/v1"
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(organizations_router, prefix=api_prefix)
    app.include_router(listings_router, prefix=f"{api_prefix}/organizations/{{org_id}}/listings")
    app.include_router(public_router, prefix=api_prefix)
    app.include_router(listing_media_router, prefix=f"{api_prefix}/organizations/{{org_id}}/listings")
    app.include_router(social_accounts_router)
    app.include_router(content_router, prefix=f"{api_prefix}/organizations/{{org_id}}/content")
    app.include_router(publications_router, prefix=f"{api_prefix}/organizations/{{org_id}}/publications")
    app.include_router(audit_router, prefix=f"{api_prefix}/organizations/{{org_id}}/audit-log")

    # Webhook endpoints — global platform callbacks (no org prefix, no auth)
    app.include_router(webhook_router)

    # Feature flags — org-scoped (with auth) and global (no auth)
    app.include_router(feature_flags_router, prefix=api_prefix)

    return app


app = create_app()
