"""Repository for ListingMedia entity operations."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ListingMedia


class ListingMediaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, media_id: uuid.UUID) -> ListingMedia | None:
        result = await self.db.execute(
            select(ListingMedia).where(ListingMedia.id == media_id)
        )
        return result.scalar_one_or_none()

    async def list_for_listing(self, listing_id: uuid.UUID) -> list[ListingMedia]:
        result = await self.db.execute(
            select(ListingMedia)
            .where(ListingMedia.listing_id == listing_id)
            .order_by(ListingMedia.order_index, ListingMedia.created_at)
        )
        return list(result.scalars().all())

    async def create(self, listing_id: uuid.UUID, org_id: uuid.UUID, **kwargs) -> ListingMedia:
        media = ListingMedia(
            listing_id=listing_id,
            organization_id=org_id,
            **kwargs,
        )
        self.db.add(media)
        await self.db.flush()
        await self.db.refresh(media)
        return media

    async def set_cover(self, media: ListingMedia) -> ListingMedia:
        # Unset other covers for the same listing
        await self.db.execute(
            update(ListingMedia)
            .where(
                ListingMedia.listing_id == media.listing_id,
                ListingMedia.id != media.id,
                ListingMedia.is_cover == True,  # noqa: E712
            )
            .values(is_cover=False)
        )
        media.is_cover = True
        await self.db.flush()
        await self.db.refresh(media)
        return media

    async def delete(self, media: ListingMedia) -> None:
        await self.db.delete(media)
        await self.db.flush()
