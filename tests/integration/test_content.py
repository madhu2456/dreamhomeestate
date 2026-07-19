"""Integration tests for content template CRUD and preview API."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MembershipRole
from app.repositories.content import ContentTemplateRepository
from app.repositories.listing import ListingRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository


@pytest_asyncio.fixture
async def editor_user(db: AsyncSession, test_org):
    from app.models import User
    repo = UserRepository(db)
    user = await repo.create(
        email=f"editor-content-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Editor User",
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
async def test_template(db: AsyncSession, test_org):
    repo = ContentTemplateRepository(db)
    template = await repo.create(
        org_id=test_org.id,
        name="Test Template",
        platform="mock",
        body_template="{{ title }} - {{ price_formatted }}",
        variables=["title", "price_formatted"],
    )
    return template


class TestListTemplates:
    async def test_list_templates_empty(self, authenticated_client: AsyncClient, test_org):
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_org.id}/content/templates"
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_templates_with_data(
        self, authenticated_client: AsyncClient, test_org, test_template
    ):
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_org.id}/content/templates"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test Template"


class TestCreateTemplate:
    async def test_create_as_editor(self, editor_client: AsyncClient, test_org):
        response = await editor_client.post(
            f"/api/v1/organizations/{test_org.id}/content/templates",
            json={
                "name": "New Template",
                "platform": "x",
                "body_template": "Check out {{ title }}!",
                "variables": ["title"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Template"
        assert data["platform"] == "x"
        assert data["version"] == 1

    async def test_create_as_viewer_fails(
        self, db: AsyncSession, client: AsyncClient, test_org
    ):
        from app.repositories.session_repo import SessionRepository
        from app.security import sign_session_id
        from datetime import datetime, timedelta, timezone
        from app.models import User

        repo = UserRepository(db)
        viewer = await repo.create(
            email=f"viewer-{uuid.uuid4().hex[:8]}@example.com",
            full_name="Viewer",
            password="pass123",
        )
        org_repo = OrganizationRepository(db)
        await org_repo.add_member(test_org, viewer, MembershipRole.viewer)
        await db.flush()

        session_repo = SessionRepository(db)
        session_id = uuid.uuid4()
        session_token = sign_session_id(session_id)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        await session_repo.create(
            user_id=viewer.id,
            session_token=session_token,
            expires_at=expires_at,
        )
        await db.flush()

        client.cookies.set("res_session", session_token)
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/content/templates",
            json={
                "name": "Viewer Template",
                "platform": "mock",
                "body_template": "test",
                "variables": [],
            },
        )
        assert response.status_code == 403


class TestGetTemplate:
    async def test_get_template_by_id(
        self, authenticated_client: AsyncClient, test_org, test_template
    ):
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_org.id}/content/templates/{test_template.id}"
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(test_template.id)

    async def test_get_template_not_found(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_org.id}/content/templates/{uuid.uuid4()}"
        )
        assert response.status_code == 404


class TestUpdateTemplate:
    async def test_update_template(
        self, authenticated_client: AsyncClient, test_org, test_template
    ):
        response = await authenticated_client.patch(
            f"/api/v1/organizations/{test_org.id}/content/templates/{test_template.id}",
            json={"name": "Updated Template"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Template"

    async def test_update_template_creates_new_version(
        self, authenticated_client: AsyncClient, test_org, test_template
    ):
        response = await authenticated_client.patch(
            f"/api/v1/organizations/{test_org.id}/content/templates/{test_template.id}",
            json={"body_template": "New body template content"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2
        assert data["body_template"] == "New body template content"


class TestDeleteTemplate:
    async def test_delete_template(
        self, authenticated_client: AsyncClient, test_org, test_template
    ):
        response = await authenticated_client.delete(
            f"/api/v1/organizations/{test_org.id}/content/templates/{test_template.id}"
        )
        assert response.status_code == 204

    async def test_delete_nonexistent_template_fails(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.delete(
            f"/api/v1/organizations/{test_org.id}/content/templates/{uuid.uuid4()}"
        )
        assert response.status_code == 404


class TestPreview:
    @pytest_asyncio.fixture
    async def test_listing(self, db: AsyncSession, test_org):
        repo = ListingRepository(db)
        listing = await repo.create(
            org_id=test_org.id,
            title="Beautiful Villa",
            transaction_type="sale",
            property_type="house",
            city="Miami",
            country="USA",
            price=750000,
            currency="USD",
            bedrooms=4,
            bathrooms=3,
            area=2500,
            area_unit="sqft",
        )
        return listing

    async def test_preview_with_template(
        self,
        authenticated_client: AsyncClient,
        test_org,
        test_template,
        test_listing,
    ):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/content/preview",
            json={
                "listing_id": str(test_listing.id),
                "template_id": str(test_template.id),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Beautiful Villa" in data["body"]
        assert "USD 750,000" in data["body"]
        assert data["platform"] == "mock"
        assert not data["errors"]

    async def test_preview_with_missing_listing(
        self, authenticated_client: AsyncClient, test_org, test_template
    ):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/content/preview",
            json={
                "listing_id": str(uuid.uuid4()),
                "template_id": str(test_template.id),
            },
        )
        assert response.status_code == 404

    async def test_preview_with_missing_template(
        self, authenticated_client: AsyncClient, test_org, test_listing
    ):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/content/preview",
            json={
                "listing_id": str(test_listing.id),
                "template_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 404


class TestPreviewDryRun:
    async def test_dry_run_renders_template(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/content/preview/dry-run",
            json={
                "body_template": "Hello {{ name }}!",
                "title_template": "Title: {{ name }}",
                "platform": "mock",
                "variables": {"name": "World"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["body"] == "Hello World!"
        assert data["title"] == "Title: World"
        assert not data["errors"]

    async def test_dry_run_warns_about_missing_vars(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/content/preview/dry-run",
            json={
                "body_template": "{{ unknown }}",
                "platform": "mock",
                "variables": {},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) > 0
