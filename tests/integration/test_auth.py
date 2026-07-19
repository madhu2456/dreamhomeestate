"""Integration tests for authentication flow: login, logout, me, password reset."""

import re

import pytest
from httpx import AsyncClient

from app.repositories import UserRepository
from app.repositories.organization import OrganizationRepository
from app.models import MembershipRole


def _set_cookie_headers(response) -> list[str]:
    """All Set-Cookie header values (httpx may only expose non-HttpOnly in .cookies)."""
    # httpx 0.27+: multi-value headers
    if hasattr(response.headers, "get_list"):
        values = response.headers.get_list("set-cookie")
        if values:
            return values
    raw = response.headers.get("set-cookie")
    return [raw] if raw else []


def _cookie_names_from_set_cookie(response) -> set[str]:
    names: set[str] = set()
    for header in _set_cookie_headers(response):
        match = re.match(r"([^=]+)=", header.strip())
        if match:
            names.add(match.group(1))
    return names


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user, test_org, db):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == str(test_user.id)
        assert len(data["memberships"]) >= 1

        # Session (HttpOnly) + CSRF (readable). Prefer Set-Cookie headers —
        # httpx response.cookies can omit HttpOnly cookies.
        cookie_names = _cookie_names_from_set_cookie(response)
        assert "res_session" in cookie_names, (
            f"session cookie missing from Set-Cookie; got {cookie_names!r}. "
            "If only csrf is present, a middleware may be collapsing multi Set-Cookie headers."
        )
        assert "res_csrf" in cookie_names

        # Functional check: session cookie authenticates /me
        session_header = next(
            h for h in _set_cookie_headers(response) if h.startswith("res_session=")
        )
        session_value = session_header.split(";", 1)[0].split("=", 1)[1]
        client.cookies.set("res_session", session_value)
        me = await client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == test_user.email

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever"},
        )
        assert response.status_code == 401

    async def test_login_inactive_user(self, client: AsyncClient, db, test_org):
        repo = UserRepository(db)
        user = await repo.create(
            email="inactive@example.com",
            full_name="Inactive User",
            password="testpass123",
            is_active=False,
        )
        org_repo = OrganizationRepository(db)
        await org_repo.add_member(test_org, user, MembershipRole.viewer)
        await db.flush()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "testpass123"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Account is inactive"


class TestMe:
    async def test_me_authenticated(self, authenticated_client: AsyncClient, test_user):
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == str(test_user.id)

    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestLogout:
    async def test_logout_clears_session(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["detail"] == "Logged out"

        # After logout, /me should return 401
        response2 = await authenticated_client.get("/api/v1/auth/me")
        assert response2.status_code == 401


class TestPasswordReset:
    async def test_password_reset_request_always_succeeds(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": test_user.email},
        )
        assert response.status_code == 200
        # Should always return the same message (no user enumeration)
        assert "sent" in response.json()["detail"].lower()

    async def test_password_reset_request_unknown_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "no-such-user@example.com"},
        )
        assert response.status_code == 200
        assert "sent" in response.json()["detail"].lower()

    async def test_password_reset_with_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"token": "invalid-token", "new_password": "newpass12345"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
