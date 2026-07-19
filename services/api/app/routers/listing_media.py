"""Listing media router: upload, reorder, set cover, delete media."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_organization, require_role
from app.models import (
    MediaKind,
    MediaProcessingStatus,
    MembershipRole,
    Organization,
)
from app.repositories.listing import ListingRepository
from app.repositories.listing_media import ListingMediaRepository
from app.schemas.listing import MediaOut
from app.schemas.listing_media import CoverUpdateOut
from app.services.media_service import (
    delete_objects,
    process_and_upload_image,
    validate_image,
)

router = APIRouter(tags=["listing_media"])
logger = structlog.get_logger(__name__)


@router.post(
    "/{listing_id}/media",
    response_model=MediaOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    listing_id: uuid.UUID,
    file: UploadFile,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> MediaOut:
    """Upload an image for a listing. Owner/Admin/Editor only."""
    listing_repo = ListingRepository(db)
    listing = await listing_repo.get_by_id(org.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    # Validate the image
    file_bytes, width, height, mime_type, ext = await validate_image(file)

    # Get the next order index
    media_repo = ListingMediaRepository(db)
    existing_media = await media_repo.list_for_listing(listing_id)
    next_order = len(existing_media)

    # Create media record (pending)
    media = await media_repo.create(
        listing_id=listing_id,
        org_id=org.id,
        kind=MediaKind.image,
        original_object_key="",
        original_file_name=file.filename,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        width=width,
        height=height,
        order_index=next_order,
        processing_status=MediaProcessingStatus.pending,
    )

    try:
        # Process and upload
        result = await process_and_upload_image(
            file_bytes=file_bytes,
            listing_id=listing_id,
            media_id=media.id,
            original_name=file.filename or "image.jpg",
        )

        media.original_object_key = result["original_object_key"]
        media.size_bytes = result["size_bytes"]
        media.mime_type = result["mime_type"]
        media.width = result["width"]
        media.height = result["height"]
        media.variants = result["variants"]
        media.processing_status = MediaProcessingStatus.ready
        await db.flush()
        await db.refresh(media)
    except Exception:
        media.processing_status = MediaProcessingStatus.failed
        await db.flush()
        raise

    return MediaOut.model_validate(media)


@router.patch(
    "/{listing_id}/media/{media_id}/cover",
    response_model=CoverUpdateOut,
)
async def set_cover(
    listing_id: uuid.UUID,
    media_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> CoverUpdateOut:
    """Set a media item as the cover for a listing. Owner/Admin/Editor only."""
    listing_repo = ListingRepository(db)
    listing = await listing_repo.get_by_id(org.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    media_repo = ListingMediaRepository(db)
    media = await media_repo.get_by_id(media_id)
    if media is None or media.listing_id != listing_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    await media_repo.set_cover(media)

    return CoverUpdateOut(message="Cover image updated", media_id=media.id)


@router.delete(
    "/{listing_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_media(
    listing_id: uuid.UUID,
    media_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
):
    """Delete a media item from DB and S3. Owner/Admin/Editor only."""
    listing_repo = ListingRepository(db)
    listing = await listing_repo.get_by_id(org.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    media_repo = ListingMediaRepository(db)
    media = await media_repo.get_by_id(media_id)
    if media is None or media.listing_id != listing_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    # Collect object keys to delete
    keys_to_delete = [media.original_object_key]
    if media.variants:
        keys_to_delete.extend(v for v in media.variants.values() if v)

    await media_repo.delete(media)

    # Delete from S3 (best-effort, do not fail if S3 delete fails)
    await delete_objects([k for k in keys_to_delete if k])
