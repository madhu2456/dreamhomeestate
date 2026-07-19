"""Repository for Organization and membership operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    User,
)


class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, name: str, slug: str, **kwargs) -> Organization:
        org = Organization(name=name, slug=slug, **kwargs)
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def add_member(
        self,
        organization: Organization,
        user: User,
        role: MembershipRole = MembershipRole.viewer,
    ) -> OrganizationMembership:
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            role=role,
        )
        self.db.add(membership)
        await self.db.flush()
        await self.db.refresh(membership)
        return membership

    async def get_membership(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMembership | None:
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self, organization_id: uuid.UUID
    ) -> list[OrganizationMembership]:
        result = await self.db.execute(
            select(OrganizationMembership)
            .options(joinedload(OrganizationMembership.user))
            .where(OrganizationMembership.organization_id == organization_id)
        )
        return list(result.scalars().all())

    async def list_for_user(self, user_id: uuid.UUID) -> list[OrganizationMembership]:
        result = await self.db.execute(
            select(OrganizationMembership)
            .options(
                joinedload(OrganizationMembership.organization),
                joinedload(OrganizationMembership.user),
            )
            .where(OrganizationMembership.user_id == user_id)
        )
        return list(result.scalars().all())
