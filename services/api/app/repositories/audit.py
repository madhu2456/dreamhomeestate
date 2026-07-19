"""Repository for AuditLogEntry persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLogEntry


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        action: str = "",
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        *,
        action: str | None = None,
        before: str | None = None,
        after: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        stmt = select(AuditLogEntry).where(AuditLogEntry.organization_id == org_id)
        if action is not None:
            stmt = stmt.where(AuditLogEntry.action == action)
        if before is not None:
            stmt = stmt.where(AuditLogEntry.created_at <= before)
        if after is not None:
            stmt = stmt.where(AuditLogEntry.created_at >= after)
        stmt = stmt.order_by(AuditLogEntry.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        stmt = (
            select(AuditLogEntry)
            .where(AuditLogEntry.user_id == user_id)
            .order_by(AuditLogEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
