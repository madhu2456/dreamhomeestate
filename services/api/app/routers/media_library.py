"""Org media library — upload posters/images/videos for quick posts."""

from __future__ import annotations

import os
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, get_organization, require_role
from app.models import MediaLibraryItem, MembershipRole, Organization
from app.services import media_service

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["media-library"])

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
VIDEO_MAX_BYTES = 100 * 1024 * 1024  # 100 MB


class MediaLibraryItemOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    kind: str
    public_url: str
    mime_type: str | None = None
    original_file_name: str | None = None
    width: int | None = None
    height: int | None = None
    size_bytes: int | None = None
    duration_seconds: int | None = None
    created_at: object

    model_config = {"from_attributes": True}


@router.get("", response_model=list[MediaLibraryItemOut])
async def list_media_library(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(
            MembershipRole.owner,
            MembershipRole.administrator,
            MembershipRole.editor,
            MembershipRole.viewer,
        )
    ),
) -> list[MediaLibraryItemOut]:
    result = await db.execute(
        select(MediaLibraryItem)
        .where(MediaLibraryItem.organization_id == org.id)
        .order_by(MediaLibraryItem.created_at.desc())
        .limit(100)
    )
    return [MediaLibraryItemOut.model_validate(r) for r in result.scalars().all()]


@router.post("/upload", response_model=MediaLibraryItemOut, status_code=status.HTTP_201_CREATED)
async def upload_media_library_item(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    file: UploadFile = File(...),
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> MediaLibraryItemOut:
    """Upload an image (poster) or video for multi-account posts."""
    filename = file.filename or "upload.bin"
    ext = os.path.splitext(filename)[1].lower()
    content_type = (file.content_type or "").lower()

    is_image_ext = ext in media_service.ALLOWED_EXTENSIONS or ext == ".jpeg"
    is_image_ct = content_type.startswith("image/")
    is_video = ext in VIDEO_EXTENSIONS or content_type.startswith("video/")

    # Prefer image path when browser reports image/* even if extension is odd
    if is_image_ext or (is_image_ct and not is_video):
        try:
            file_bytes, width, height, mime_type, ext = await media_service.validate_image(file)
            item_id = uuid.uuid4()
            object_key, public_url, size_bytes = await media_service.upload_library_image(
                file_bytes=file_bytes,
                org_id=org.id,
                media_id=item_id,
                ext=ext,
                mime_type=mime_type,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("media_library_image_upload_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image upload failed: {exc!s}"[:300],
            ) from exc
        item = MediaLibraryItem(
            id=item_id,
            organization_id=org.id,
            kind="image",
            object_key=object_key,
            public_url=public_url,
            mime_type=mime_type,
            original_file_name=filename,
            width=width,
            height=height,
            size_bytes=size_bytes,
            created_by=current_user.id,
        )
    elif is_video:
        file_bytes = await file.read()
        if len(file_bytes) > VIDEO_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video too large (max 100 MB)",
            )
        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
        item_id = uuid.uuid4()
        mime = file.content_type or f"video/{ext.lstrip('.')}"
        object_key, public_url, size_bytes = await media_service.upload_library_bytes(
            file_bytes=file_bytes,
            org_id=org.id,
            media_id=item_id,
            ext=ext,
            mime_type=mime,
            subfolder="video",
        )
        item = MediaLibraryItem(
            id=item_id,
            organization_id=org.id,
            kind="video",
            object_key=object_key,
            public_url=public_url,
            mime_type=mime,
            original_file_name=filename,
            size_bytes=size_bytes,
            created_by=current_user.id,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported type {ext}. Use images (jpg/png/webp) or video (mp4/mov/webm).",
        )

    db.add(item)
    await db.flush()
    await db.refresh(item)
    logger.info(
        "media_library_upload",
        org_id=str(org.id),
        item_id=str(item.id),
        kind=item.kind,
    )
    return MediaLibraryItemOut.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_media_library_item(
    item_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> Response:
    result = await db.execute(
        select(MediaLibraryItem).where(
            MediaLibraryItem.id == item_id,
            MediaLibraryItem.organization_id == org.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    await db.delete(item)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
