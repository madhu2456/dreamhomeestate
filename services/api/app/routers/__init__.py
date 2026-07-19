"""Routers package."""

from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.content import router as content_router
from app.routers.feature_flags import router as feature_flags_router
from app.routers.health import router as health_router
from app.routers.listing_media import router as listing_media_router
from app.routers.listings import router as listings_router
from app.routers.media_library import router as media_library_router
from app.routers.organizations import router as organizations_router
from app.routers.public import router as public_router
from app.routers.publications import router as publications_router
from app.routers.social_accounts import router as social_accounts_router
from app.routers.users import router as users_router
from app.routers.webhooks import router as webhook_router

__all__ = [
    "audit_router",
    "feature_flags_router",
    "health_router",
    "auth_router",
    "users_router",
    "organizations_router",
    "listings_router",
    "public_router",
    "listing_media_router",
    "media_library_router",
    "social_accounts_router",
    "content_router",
    "publications_router",
    "webhook_router",
]
