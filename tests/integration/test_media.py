"""Integration tests for listing media endpoints."""

import io
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ListingStatus, MembershipRole
from app.repositories.listing import ListingRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository
from datetime import datetime, timezone


def _make_in_memory_jpeg() -> tuple[bytes, str]:
    """Create a tiny in-memory JPEG image."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read(), "test_image.jpg"


def _make_in_memory_png() -> tuple[bytes, str]:
    """Create a tiny in-memory PNG image."""
    img = Image.new("RGBA", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read(), "test_image.png"


@pytest_asyncio.fixture
async def editor_user(db: AsyncSession, test_org):
    """Create a user with editor role in test_org."""
    from app.models import User
    repo = UserRepository(db)
    user = await repo.create(
        email=f"media-editor-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Media Editor",
        password="editorpass123",
    )
    org_repo = OrganizationRepository(db)
    await org_repo.add_member(test_org, user, MembershipRole.editor)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def editor_client(
    client: AsyncClient, db: AsyncSession, editor_user, test_org
) -> AsyncClient:
    """Return a client authenticated as editor_user."""
    from app.repositories.session_repo import SessionRepository
    from app.security import sign_session_id
    from datetime import timedelta

    session_repo = SessionRepository(db)
    session_id = uuid.uuid4()
    session_token = sign_session_id(session_id)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    await session_repo.create(
        user_id=editor_user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    await db.flush()

    client.cookies.set("res_session", session_token)
    return client


@pytest_asyncio.fixture
async def listing_with_org(
    db: AsyncSession, test_org, editor_client: AsyncClient
):
    """Create a listing for media tests. Bypass HTTP since we need the raw ID."""
    repo = ListingRepository(db)
    listing = await repo.create(
        org_id=test_org.id,
        title="Media Test Listing",
        transaction_type="sale",
        property_type="apartment",
        city="Mumbai",
        country="India",
        listing_status=ListingStatus.published,
        published_at=datetime.now(timezone.utc),
    )
    await db.flush()
    return listing


class TestUploadMedia:
    async def test_upload_image(
        self, editor_client: AsyncClient, test_org, db: AsyncSession
    ):
        """Upload a valid image file."""
        # Create a listing first
        from app.repositories.listing import ListingRepository
        repo = ListingRepository(db)
        listing = await repo.create(
            org_id=test_org.id,
            title="Image Upload Test",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
        )
        await db.flush()

        jpeg_bytes, filename = _make_in_memory_jpeg()

        response = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings/{listing.id}/media",
            files={"file": (filename, jpeg_bytes, "image/jpeg")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["kind"] == "image"
        assert data["original_file_name"] == filename
        assert data["processing_status"] == "ready"
        assert data["width"] == 100
        assert data["height"] == 100

    async def test_set_cover(
        self, editor_client: AsyncClient, test_org, db: AsyncSession
    ):
        """Set a media item as cover."""
        from app.repositories.listing import ListingRepository
        repo = ListingRepository(db)
        listing = await repo.create(
            org_id=test_org.id,
            title="Cover Test",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
        )
        await db.flush()

        jpeg_bytes, filename = _make_in_memory_jpeg()
        resp = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings/{listing.id}/media",
            files={"file": (filename, jpeg_bytes, "image/jpeg")},
        )
        media_id = resp.json()["id"]

        # Set as cover
        response = await editor_client.patch(
            f"/api/v1/organizations/{test_org.id}/listings/{listing.id}/media/{media_id}/cover",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Cover image updated"
        assert data["media_id"] == media_id

    async def test_delete_media(
        self, editor_client: AsyncClient, test_org, db: AsyncSession
    ):
        """Delete a media item."""
        from app.repositories.listing import ListingRepository
        repo = ListingRepository(db)
        listing = await repo.create(
            org_id=test_org.id,
            title="Delete Media Test",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
        )
        await db.flush()

        jpeg_bytes, filename = _make_in_memory_jpeg()
        resp = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings/{listing.id}/media",
            files={"file": (filename, jpeg_bytes, "image/jpeg")},
        )
        media_id = resp.json()["id"]

        response = await editor_client.delete(
            f"/api/v1/organizations/{test_org.id}/listings/{listing.id}/media/{media_id}",
        )
        assert response.status_code == 204

    async def test_invalid_file_type_rejected(
        self, editor_client: AsyncClient, test_org, db: AsyncSession
    ):
        """Non-image file should be rejected."""
        from app.repositories.listing import ListingRepository
        repo = ListingRepository(db)
        listing = await repo.create(
            org_id=test_org.id,
            title="Invalid File Test",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
        )
        await db.flush()

        txt_content = b"This is not an image"
        response = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings/{listing.id}/media",
            files={"file": ("document.txt", txt_content, "text/plain")},
        )
        assert response.status_code == 400
