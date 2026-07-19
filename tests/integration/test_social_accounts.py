"""Integration tests for live social account connections."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccountConnectionStatus, MembershipRole, ProviderEnum
from app.repositories.encrypted_credentials import EncryptedCredentialsRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.social_account import SocialAccountRepository
from app.repositories.user import UserRepository
from app.security import sign_session_id
from app.services.encryption import encrypt_text


class TestListSocialAccounts:
    async def test_list_empty(self, authenticated_client: AsyncClient, test_org):
        response = await authenticated_client.get(
            f"/api/v1/organizations/{test_org.id}/social-accounts"
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_unauthenticated(self, client: AsyncClient, test_org):
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/social-accounts"
        )
        assert response.status_code == 401


class TestLiveConnectRequiresConfig:
    async def test_connect_instagram_without_config_returns_503(
        self, authenticated_client, test_org
    ):
        with patch("app.routers.social_accounts._instagram_configured", return_value=False):
            response = await authenticated_client.post(
                f"/api/v1/organizations/{test_org.id}/social-accounts/instagram/connect",
                json={"redirect_after": "/admin/social-accounts"},
            )
        assert response.status_code == 503
        assert "INSTAGRAM_APP_ID" in response.json()["detail"]

    async def test_connect_x_without_config_returns_503(
        self, authenticated_client, test_org
    ):
        with patch("app.routers.social_accounts._x_configured", return_value=False):
            response = await authenticated_client.post(
                f"/api/v1/organizations/{test_org.id}/social-accounts/x/connect",
                json={"redirect_after": "/admin/social-accounts"},
            )
        assert response.status_code == 503
        assert "X_CLIENT_ID" in response.json()["detail"]

    async def test_connect_unsupported_provider(self, authenticated_client, test_org):
        response = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/social-accounts/facebook/connect",
            json={"redirect_after": "/admin/social-accounts"},
        )
        assert response.status_code == 400

    async def test_connect_instagram_returns_oauth_url(
        self, authenticated_client, test_org
    ):
        with patch("app.routers.social_accounts._instagram_configured", return_value=True), patch(
            "app.routers.social_accounts.settings"
        ) as mock_settings:
            mock_settings.instagram_app_id = "app-id"
            mock_settings.instagram_app_secret = "secret"
            mock_settings.instagram_redirect_uri = (
                "http://localhost:8000/api/v1/social-accounts/instagram/callback"
            )
            response = await authenticated_client.post(
                f"/api/v1/organizations/{test_org.id}/social-accounts/instagram/connect",
                json={"redirect_after": "/admin/social-accounts"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mock"] is False
        assert "authorization_url" in data
        assert "instagram.com/oauth/authorize" in data["authorization_url"]
        assert "instagram_business_content_publish" in data["authorization_url"]

    async def test_connect_x_returns_oauth_url(self, authenticated_client, test_org):
        with patch("app.routers.social_accounts._x_configured", return_value=True), patch(
            "app.routers.social_accounts.settings"
        ) as mock_settings:
            mock_settings.x_client_id = "x-client"
            mock_settings.x_client_secret = "x-secret"
            mock_settings.x_redirect_uri = (
                "http://localhost:8000/api/v1/social-accounts/x/callback"
            )
            response = await authenticated_client.post(
                f"/api/v1/organizations/{test_org.id}/social-accounts/x/connect",
                json={"redirect_after": "/admin/social-accounts"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mock"] is False
        assert "twitter.com/i/oauth2/authorize" in data["authorization_url"]
        assert "media.write" in data["authorization_url"] or "media%2Ewrite" in data[
            "authorization_url"
        ] or "media.write" in data["authorization_url"].replace("+", " ")


async def _seed_live_account(db: AsyncSession, org_id, user_id=None, provider="instagram"):
    repo = SocialAccountRepository(db)
    account = await repo.create(
        org_id=org_id,
        provider=provider,
        provider_account_id=f"live-{provider}-{uuid.uuid4().hex[:8]}",
        username=f"live_{provider}",
        display_name=f"Live {provider}",
        connection_status="active",
        created_by=user_id,
        capabilities_snapshot={"valid": True, "can_publish": True},
    )
    creds_repo = EncryptedCredentialsRepository(db)
    await creds_repo.create_or_update(
        social_account_id=account.id,
        access_token="live-access-token",
    )
    await db.flush()
    return account


class TestRevoke:
    async def test_revoke_sets_status(self, authenticated_client, test_org, db):
        account = await _seed_live_account(db, test_org.id)

        revoke_resp = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/social-accounts/{account.id}/revoke"
        )
        assert revoke_resp.status_code == 200
        data = revoke_resp.json()
        assert data["connection_status"] == "revoked"
        assert data["revoked_at"] is not None

    async def test_revoke_not_found(self, authenticated_client, test_org):
        fake_id = uuid.uuid4()
        resp = await authenticated_client.post(
            f"/api/v1/organizations/{test_org.id}/social-accounts/{fake_id}/revoke"
        )
        assert resp.status_code == 404


class TestValidate:
    async def test_validate_updates_capabilities(self, authenticated_client, test_org, db):
        account = await _seed_live_account(db, test_org.id, provider="x")

        with patch("app.routers.social_accounts.get_connector") as mock_get:
            connector = AsyncMock()
            connector.validate.return_value = {
                "valid": True,
                "can_publish": True,
                "username": "live_x",
                "provider_account_id": account.provider_account_id,
            }
            mock_get.return_value = connector

            validate_resp = await authenticated_client.post(
                f"/api/v1/organizations/{test_org.id}/social-accounts/{account.id}/validate"
            )

        assert validate_resp.status_code == 200
        data = validate_resp.json()
        assert data["capabilities_snapshot"] is not None
        assert data["capabilities_snapshot"]["valid"] is True
        assert data["connection_status"] == "active"

    async def test_test_endpoint_works(self, authenticated_client, test_org, db):
        account = await _seed_live_account(db, test_org.id, provider="instagram")

        with patch("app.routers.social_accounts.get_connector") as mock_get:
            connector = AsyncMock()
            connector.validate.return_value = {
                "valid": True,
                "can_publish": True,
                "username": "live_instagram",
            }
            mock_get.return_value = connector

            test_resp = await authenticated_client.post(
                f"/api/v1/organizations/{test_org.id}/social-accounts/{account.id}/test"
            )
        assert test_resp.status_code == 200
        data = test_resp.json()
        assert data["capabilities_snapshot"] is not None
