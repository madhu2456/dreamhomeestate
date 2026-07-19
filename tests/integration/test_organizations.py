"""Integration tests for organizations API."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import UserRepository
from app.repositories.organization import OrganizationRepository


class TestListOrganizations:
    async def test_list_orgs_for_user(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.get("/api/v1/organizations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(o["slug"] == test_org.slug for o in data)

    async def test_list_orgs_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/organizations")
        assert response.status_code == 401


class TestCreateOrganization:
    async def test_create_org(self, authenticated_client: AsyncClient):
        slug = f"new-org-{uuid.uuid4().hex[:8]}"
        response = await authenticated_client.post(
            "/api/v1/organizations",
            json={
                "name": "New Organization",
                "slug": slug,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == slug

    async def test_create_org_duplicate_slug(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.post(
            "/api/v1/organizations",
            json={
                "name": "Duplicate",
                "slug": test_org.slug,
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_create_org_invalid_slug(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post(
            "/api/v1/organizations",
            json={
                "name": "Bad Slug",
                "slug": "INVALID UPPERCASE",
            },
        )
        assert response.status_code == 422


class TestGetOrganization:
    async def test_get_org_as_member(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_org.id}"
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(test_org.id)

    async def test_get_org_not_member(
        self, authenticated_client: AsyncClient, db
    ):
        org_repo = OrganizationRepository(db)
        other_org = await org_repo.create(name="Other", slug="other-org")
        await db.flush()

        response = await authenticated_client.get(
            f"/api/v1/organizations/{other_org.id}"
        )
        assert response.status_code == 403

    async def test_get_org_nonexistent(self, authenticated_client: AsyncClient):
        fake_id = uuid.uuid4()
        response = await authenticated_client.get(f"/api/v1/organizations/{fake_id}")
        assert response.status_code == 404


class TestListMembers:
    async def test_list_members_as_owner(
        self, authenticated_client: AsyncClient, test_org, test_user
    ):
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_org.id}/members"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(m["email"] == test_user.email for m in data)

    async def test_add_member_to_org(
        self, authenticated_client: AsyncClient, test_org, test_user
    ):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/members",
            json={
                "email": "member@example.com",
                "full_name": "New Member",
                "role": "editor",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "member@example.com"
        assert data["role"] == "editor"

    async def test_add_duplicate_member(
        self, authenticated_client: AsyncClient, test_org, test_user
    ):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/members",
            json={
                "email": test_user.email,
                "full_name": test_user.full_name,
                "role": "viewer",
            },
        )
        assert response.status_code == 409
