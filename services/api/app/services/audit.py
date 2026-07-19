"""Audit service — structured logging for security/compliance."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit import AuditLogRepository

logger = structlog.get_logger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = AuditLogRepository(db)

    async def log_action(
        self,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        action: str = "",
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Convenience wrapper that creates an audit log entry.  Never raises."""
        try:
            await self._repo.create(
                organization_id=organization_id,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            logger.exception("audit_log_write_failed", action=action)

    async def log_listing_change(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        listing_id: uuid.UUID,
        action: str,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Structured logging for listing CRUD operations."""
        await self.log_action(
            organization_id=org_id,
            user_id=user_id,
            action=action,
            entity_type="listing",
            entity_id=listing_id,
            details=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_campaign_action(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        campaign_id: uuid.UUID,
        action: str,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Structured logging for campaign operations."""
        await self.log_action(
            organization_id=org_id,
            user_id=user_id,
            action=action,
            entity_type="campaign",
            entity_id=campaign_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
