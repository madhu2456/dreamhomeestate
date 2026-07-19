"""Integration tests for users API."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MembershipRole
from app.repositories import UserRepository
from app.repositories.organization import OrganizationRepository


class TestListUsers:
    async def test_list_users_as_owner(
        self, authenticated_client: AsyncClient, test_org, test_user
    ):
        response = await authenticated_client.get(
            f"/api/v1/users?org_id={test_org.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(u["email"] == test_user.email for u in data)

    async def test_list_users_unauthenticated(self, client: AsyncClient, test_org):
        response = await client.get(f"/api/v1/users?org_id={test_org.id}")
        assert response.status_code == 401

    async def test_list_users_wrong_org(self, authenticated_client: AsyncClient, db, test_user):
        # Create another org where test_user is NOT a member
        org_repo = OrganizationRepository(db)
        other_org = await org_repo.create(name="Other", slug="other-org")
        await db.flush()

        # test_user is not a member of other_org
        response = await authenticated_client.get(f"/api/v1/users?org_id={other_org.id}")
        assert response.status_code == 403


class TestCreateUser:
    async def test_create_user_as_owner(
        self, authenticated_client: AsyncClient, test_org, db
    ):
        response = await authenticated_client.post(
            f"/api/v1/users?org_id={test_org.id}",
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "newuserpass",
                "role": "editor",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"

    async def test_create_user_duplicate_in_org(
        self, authenticated_client: AsyncClient, test_org, test_user
    ):
        response = await authenticated_client.post(
            f"/api/v1/users?org_id={test_org.id}",
            json={
                "email": test_user.email,
                "full_name": test_user.full_name,
                "role": "viewer",
            },
        )
        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

    async def test_create_user_invalid_role(
        self, authenticated_client: AsyncClient, test_org
    ):
        response = await authenticated_client.post(
            f"/api/v1/users?org_id={test_org.id}",
            json={
                "email": "roleuser@example.com",
                "full_name": "Role User",
                "role": "superuser",
            },
        )
        assert response.status_code == 422


class TestGetUser:
    async def test_get_user_in_org(
        self, authenticated_client: AsyncClient, test_org, test_user
    ):
        response = await authenticated_client.get(
            f"/api/v1/users/{test_user.id}?org_id={test_org.id}"
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(test_user.id)

    async def test_get_user_not_in_org(
        self, authenticated_client: AsyncClient, test_org, db
    ):
        repo = UserRepository(db)
        other_user = await repo.create(
            email="other@example.com", full_name="Other", password="testpass123"
        )
        await db.flush()

        response = await authenticated_client.get(
            f"/api/v1/users/{other_user.id}?org_id={test_org.id}"
        )
        assert response.status_code == 404
