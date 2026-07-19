"""Repository for Listing entity operations."""

import secrets
import uuid

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Listing, ListingStatus


class ListingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def slug_exists(self, org_id: uuid.UUID, slug: str) -> bool:
        result = await self.db.execute(
            select(func.count(Listing.id)).where(
                Listing.organization_id == org_id,
                Listing.slug == slug,
            )
        )
        return result.scalar_one() > 0

    async def _generate_unique_slug(self, org_id: uuid.UUID, title: str) -> str:
        base_slug = slugify(title, max_length=200) or "listing"
        slug = base_slug
        if await self.slug_exists(org_id, slug):
            suffix = secrets.token_hex(3)
            slug = f"{base_slug}-{suffix}"
            if await self.slug_exists(org_id, slug):
                suffix = secrets.token_hex(6)
                slug = f"{base_slug}-{suffix}"
        return slug

    async def get_by_id(self, org_id: uuid.UUID, listing_id: uuid.UUID) -> Listing | None:
        result = await self.db.execute(
            select(Listing).where(
                Listing.organization_id == org_id,
                Listing.id == listing_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, org_id: uuid.UUID, slug: str) -> Listing | None:
        result = await self.db.execute(
            select(Listing).where(
                Listing.organization_id == org_id,
                Listing.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        status: ListingStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Listing]:
        stmt = select(Listing).where(
            Listing.organization_id == org_id,
        )
        if status is not None:
            stmt = stmt.where(Listing.listing_status == status)
        stmt = stmt.order_by(Listing.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, org_id: uuid.UUID, **fields) -> Listing:
        title = fields.pop("title")
        slug = await self._generate_unique_slug(org_id, title)
        listing = Listing(
            organization_id=org_id,
            title=title,
            slug=slug,
            **fields,
        )
        self.db.add(listing)
        await self.db.flush()
        await self.db.refresh(listing)
        return listing

    async def update(self, listing: Listing, **fields) -> Listing:
        for key, value in fields.items():
            setattr(listing, key, value)
        listing.version = (listing.version or 1) + 1
        await self.db.flush()
        await self.db.refresh(listing)
        return listing

    async def delete(self, listing: Listing) -> None:
        await self.db.delete(listing)
        await self.db.flush()
