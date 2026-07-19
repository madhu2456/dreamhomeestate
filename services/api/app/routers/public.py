"""Public router: unauthenticated endpoints for published listings."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Listing, ListingStatus
from app.schemas.listing import PublicListingOut

router = APIRouter(prefix="/public", tags=["public"])


def _build_listing_query(
    limit: int = 50,
    offset: int = 0,
    city: str | None = None,
    transaction_type: str | None = None,
    property_type: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    q: str | None = None,
):
    now = datetime.now(timezone.utc)  # noqa: UP017

    stmt = select(Listing).where(
        Listing.listing_status == ListingStatus.published,
        Listing.published_at <= now,
        or_(
            Listing.expires_at.is_(None),
            Listing.expires_at > now,
        ),
    )

    if city:
        stmt = stmt.where(Listing.city.ilike(f"%{city}%"))
    if transaction_type:
        stmt = stmt.where(Listing.transaction_type == transaction_type)
    if property_type:
        stmt = stmt.where(Listing.property_type == property_type)
    if min_price is not None:
        stmt = stmt.where(Listing.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.price <= max_price)
    if q:
        search_term = f"%{q}%"
        stmt = stmt.where(
            or_(
                Listing.title.ilike(search_term),
                Listing.summary.ilike(search_term),
                Listing.city.ilike(search_term),
            )
        )

    stmt = stmt.order_by(Listing.published_at.desc()).offset(offset).limit(limit)
    return stmt


@router.get("/listings", response_model=list[PublicListingOut])
async def list_public_listings(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    city: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    property_type: str | None = Query(default=None),
    min_price: int | None = Query(default=None),
    max_price: int | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[PublicListingOut]:
    """List published listings with optional filters. No auth required."""
    stmt = _build_listing_query(
        limit=limit,
        offset=offset,
        city=city,
        transaction_type=transaction_type,
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        q=q,
    )
    result = await db.execute(stmt)
    listings = list(result.scalars().all())
    return [PublicListingOut.model_validate(listing) for listing in listings]


@router.get("/listings/{listing_id}", response_model=PublicListingOut)
async def get_public_listing(
    listing_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicListingOut:
    """Get a single published listing detail. No auth required."""
    now = datetime.now(timezone.utc)  # noqa: UP017

    result = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.listing_status == ListingStatus.published,
            Listing.published_at <= now,
            or_(
                Listing.expires_at.is_(None),
                Listing.expires_at > now,
            ),
        )
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return PublicListingOut.model_validate(listing)
