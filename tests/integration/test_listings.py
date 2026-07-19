"""Integration tests for listings CRUD API."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ListingStatus, MembershipRole
from app.repositories.listing import ListingRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository
from app.security import hash_password


@pytest_asyncio.fixture
async def editor_user(db: AsyncSession, test_org) -> "User":
    """Create a user with editor role in test_org."""
    from app.models import User
    repo = UserRepository(db)
    user = await repo.create(
        email=f"editor-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Editor User",
        password="editorpass123",
    )
    org_repo = OrganizationRepository(db)
    await org_repo.add_member(test_org, user, MembershipRole.editor)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db: AsyncSession, test_org) -> "User":
    """Create a user with viewer role in test_org."""
    from app.models import User
    repo = UserRepository(db)
    user = await repo.create(
        email=f"viewer-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Viewer User",
        password="viewerpass123",
    )
    org_repo = OrganizationRepository(db)
    await org_repo.add_member(test_org, user, MembershipRole.viewer)
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
    from datetime import datetime, timedelta, timezone

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
async def viewer_client(
    client: AsyncClient, db: AsyncSession, viewer_user, test_org
) -> AsyncClient:
    """Return a client authenticated as viewer_user."""
    from app.repositories.session_repo import SessionRepository
    from app.security import sign_session_id
    from datetime import datetime, timedelta, timezone

    session_repo = SessionRepository(db)
    session_id = uuid.uuid4()
    session_token = sign_session_id(session_id)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    await session_repo.create(
        user_id=viewer_user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    await db.flush()

    client.cookies.set("res_session", session_token)
    return client


class TestCreateListing:
    async def test_create_as_editor(
        self, editor_client: AsyncClient, test_org
    ):
        response = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "Beautiful Apartment",
                "transaction_type": "sale",
                "property_type": "apartment",
                "city": "Mumbai",
                "country": "India",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Beautiful Apartment"
        assert data["slug"].startswith("beautiful-apartment")
        assert data["listing_status"] == "draft"

    async def test_slug_uniqueness(
        self, editor_client: AsyncClient, test_org
    ):
        # First listing with same title
        resp1 = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "Unique Condo",
                "transaction_type": "sale",
                "property_type": "apartment",
                "city": "Delhi",
                "country": "India",
            },
        )
        assert resp1.status_code == 201
        slug1 = resp1.json()["slug"]

        # Second listing with same title should get a different slug
        resp2 = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "Unique Condo",
                "transaction_type": "sale",
                "property_type": "apartment",
                "city": "Delhi",
                "country": "India",
            },
        )
        assert resp2.status_code == 201
        slug2 = resp2.json()["slug"]
        assert slug1 != slug2
        assert slug2.startswith("unique-condo-")

    async def test_create_as_viewer_forbidden(
        self, viewer_client: AsyncClient, test_org
    ):
        response = await viewer_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "Viewer Attempt",
                "transaction_type": "sale",
                "property_type": "apartment",
                "city": "Pune",
                "country": "India",
            },
        )
        assert response.status_code == 403

    async def test_create_requires_auth(self, client: AsyncClient, test_org):
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "No Auth",
                "transaction_type": "sale",
                "property_type": "apartment",
                "city": "Pune",
                "country": "India",
            },
        )
        assert response.status_code == 401


class TestUpdateListing:
    async def test_update_status_to_published(
        self, editor_client: AsyncClient, test_org
    ):
        # Create listing first
        resp = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "Test Published",
                "transaction_type": "sale",
                "property_type": "house",
                "city": "Bangalore",
                "country": "India",
            },
        )
        listing_id = resp.json()["id"]

        # Update to published
        response = await editor_client.patch(
            f"/api/v1/organizations/{test_org.id}/listings/{listing_id}",
            json={"listing_status": "published"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["listing_status"] == "published"
        assert data["published_at"] is not None

    async def test_update_price(
        self, editor_client: AsyncClient, test_org
    ):
        resp = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "Price Update Test",
                "transaction_type": "sale",
                "property_type": "house",
                "city": "Mumbai",
                "country": "India",
            },
        )
        listing_id = resp.json()["id"]

        response = await editor_client.patch(
            f"/api/v1/organizations/{test_org.id}/listings/{listing_id}",
            json={"price": 5000000},
        )
        assert response.status_code == 200
        assert response.json()["price"] == 5000000


class TestListListings:
    async def test_list_org_listings(
        self, editor_client: AsyncClient, test_org
    ):
        # Create a few listings
        for i in range(3):
            await editor_client.post(
                f"/api/v1/organizations/{test_org.id}/listings",
                json={
                    "title": f"Listing {i}",
                    "transaction_type": "sale",
                    "property_type": "apartment",
                    "city": "Mumbai",
                    "country": "India",
                },
            )

        response = await editor_client.get(
            f"/api/v1/organizations/{test_org.id}/listings"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    async def test_list_viewer_can_read(
        self, viewer_client: AsyncClient, test_org, editor_client: AsyncClient
    ):
        # Create via editor
        resp = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "Viewer Readable",
                "transaction_type": "sale",
                "property_type": "apartment",
                "city": "Mumbai",
                "country": "India",
            },
        )
        listing_id = resp.json()["id"]

        # Viewer can read
        get_resp = await viewer_client.get(
            f"/api/v1/organizations/{test_org.id}/listings/{listing_id}"
        )
        assert get_resp.status_code == 200


class TestDeleteListing:
    async def test_delete_listing(
        self, editor_client: AsyncClient, test_org
    ):
        resp = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/listings",
            json={
                "title": "To Be Deleted",
                "transaction_type": "sale",
                "property_type": "apartment",
                "city": "Mumbai",
                "country": "India",
            },
        )
        listing_id = resp.json()["id"]

        response = await editor_client.delete(
            f"/api/v1/organizations/{test_org.id}/listings/{listing_id}"
        )
        assert response.status_code == 204

        # Verify gone
        get_resp = await editor_client.get(
            f"/api/v1/organizations/{test_org.id}/listings/{listing_id}"
        )
        assert get_resp.status_code == 404
