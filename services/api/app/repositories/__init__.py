"""Data-access layer for organization-scoped queries."""

from app.repositories.audit import AuditLogRepository
from app.repositories.content import ContentTemplateRepository
from app.repositories.encrypted_credentials import EncryptedCredentialsRepository
from app.repositories.listing import ListingRepository
from app.repositories.listing_media import ListingMediaRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.publication import (
    PublicationAttemptRepository,
    PublicationCampaignRepository,
    PublicationJobRepository,
    PublicationOutboxRepository,
)
from app.repositories.session_repo import SessionRepository
from app.repositories.social_account import SocialAccountRepository
from app.repositories.user import UserRepository

__all__ = [
    "AuditLogRepository",
    "UserRepository",
    "OrganizationRepository",
    "SessionRepository",
    "ListingRepository",
    "ListingMediaRepository",
    "SocialAccountRepository",
    "EncryptedCredentialsRepository",
    "ContentTemplateRepository",
    "PublicationCampaignRepository",
    "PublicationJobRepository",
    "PublicationAttemptRepository",
    "PublicationOutboxRepository",
]
