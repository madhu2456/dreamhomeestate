"""Listings router: CRUD for real estate listings within an organization."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, get_organization, require_role
from app.models import ListingStatus, MembershipRole, Organization
from app.repositories.listing import ListingRepository
from app.schemas.listing import ListingCreate, ListingOut, ListingUpdate
from app.services.audit import AuditService

router = APIRouter(tags=["listings"])
logger = structlog.get_logger(__name__)


@router.get("", response_model=list[ListingOut])
async def list_listings(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: ListingStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ListingOut]:
    """List all listings for the organization. Any member can view."""
    repo = ListingRepository(db)
    listings = await repo.list_for_org(
        org_id=org.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [ListingOut.model_validate(listing) for listing in listings]


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    body: ListingCreate,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> ListingOut:
    """Create a new listing. Owner/Admin/Editor only."""
    repo = ListingRepository(db)
    fields = body.model_dump()
    listing = await repo.create(org_id=org.id, **fields)

    logger.info(
        "listing_created",
        listing_id=str(listing.id),
        slug=listing.slug,
        org_id=str(org.id),
    )

    # Audit: listing.created
    audit_svc = AuditService(db)
    await audit_svc.log_listing_change(
        org_id=org.id,
        user_id=current_user.id,
        listing_id=listing.id,
        action="listing.created",
        changes=fields,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return ListingOut.model_validate(listing)


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ListingOut:
    """Get a single listing by ID. Any member can view."""
    repo = ListingRepository(db)
    listing = await repo.get_by_id(org.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return ListingOut.model_validate(listing)


@router.patch("/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: uuid.UUID,
    body: ListingUpdate,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> ListingOut:
    """Update a listing. Owner/Admin/Editor only."""
    repo = ListingRepository(db)
    listing = await repo.get_by_id(org.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    fields = body.model_dump(exclude_unset=True)

    # If status is being set to published, set published_at if not already set
    if fields.get("listing_status") == ListingStatus.published and not listing.published_at:
        listing.published_at = datetime.now(timezone.utc)  # noqa: UP017
        await repo.update(listing, published_at=listing.published_at)

    listing = await repo.update(listing, **fields)

    # Audit: listing.updated
    audit_svc = AuditService(db)
    await audit_svc.log_listing_change(
        org_id=org.id,
        user_id=current_user.id,
        listing_id=listing.id,
        action="listing.updated",
        changes=fields,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return ListingOut.model_validate(listing)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(
    listing_id: uuid.UUID,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
):
    """Delete a listing. Owner/Admin/Editor only."""
    repo = ListingRepository(db)
    listing = await repo.get_by_id(org.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    await repo.delete(listing)

    # Audit: listing.deleted
    audit_svc = AuditService(db)
    await audit_svc.log_listing_change(
        org_id=org.id,
        user_id=current_user.id,
        listing_id=listing_id,
        action="listing.deleted",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(
        "listing_deleted",
        listing_id=str(listing_id),
        org_id=str(org.id),
    )
