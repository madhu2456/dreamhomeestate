"""Unit tests for live X and Instagram connectors (httpx mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.connectors.instagram import InstagramConnector, ProviderPublishError as IGError
from app.connectors.x import ProviderPublishError as XError
from app.connectors.x import XConnector


def _account(provider_account_id="12345", username="tester"):
    account = MagicMock()
    account.id = "acc-1"
    account.provider_account_id = provider_account_id
    account.username = username
    return account


def _creds(token="access-token"):
    creds = MagicMock()
    creds.encrypted_access_token = "enc"
    creds.encrypted_refresh_token = None
    return creds


class TestXConnector:
    @pytest.mark.asyncio
    async def test_publish_text_tweet(self):
        connector = XConnector()
        account = _account()
        creds = _creds()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"id": "tweet-99"}}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response

        with patch("app.connectors.x.settings") as settings, patch(
            "app.connectors.x.decrypt_text", return_value="token"
        ), patch("app.connectors.x.httpx.AsyncClient", return_value=mock_client):
            settings.x_client_id = "cid"
            settings.x_client_secret = "secret"
            result = await connector.publish(
                account, creds, {"body": "Hello from RealEstate", "media_urls": []}
            )

        assert result["id"] == "tweet-99"
        assert "status/tweet-99" in result["url"]
        mock_client.post.assert_called()

    @pytest.mark.asyncio
    async def test_publish_rejects_too_long(self):
        connector = XConnector()
        with patch("app.connectors.x.settings") as settings, patch(
            "app.connectors.x.decrypt_text", return_value="token"
        ):
            settings.x_client_id = "cid"
            settings.x_client_secret = "secret"
            with pytest.raises(XError) as exc:
                await connector.publish(
                    _account(), _creds(), {"body": "x" * 281, "media_urls": []}
                )
        assert exc.value.code == "text_too_long"

    @pytest.mark.asyncio
    async def test_publish_requires_config(self):
        connector = XConnector()
        with patch("app.connectors.x.settings") as settings:
            settings.x_client_id = None
            settings.x_client_secret = None
            with pytest.raises(XError) as exc:
                await connector.publish(_account(), _creds(), {"body": "hi"})
        assert exc.value.code == "not_configured"


class TestInstagramConnector:
    @pytest.mark.asyncio
    async def test_publish_single_image(self):
        connector = InstagramConnector()
        account = _account(provider_account_id="ig-user-1")
        creds = _creds()

        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {"id": "container-1"}

        status_resp = MagicMock()
        status_resp.status_code = 200
        status_resp.json.return_value = {"status_code": "FINISHED"}

        publish_resp = MagicMock()
        publish_resp.status_code = 200
        publish_resp.json.return_value = {"id": "media-9"}

        permalink_resp = MagicMock()
        permalink_resp.status_code = 200
        permalink_resp.json.return_value = {"permalink": "https://instagram.com/p/abc"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = [create_resp, publish_resp]
        mock_client.get.side_effect = [status_resp, permalink_resp]

        with patch("app.connectors.instagram.settings") as settings, patch(
            "app.connectors.instagram.decrypt_text", return_value="token"
        ), patch(
            "app.connectors.instagram.httpx.AsyncClient", return_value=mock_client
        ):
            settings.instagram_app_id = "app"
            settings.instagram_app_secret = "secret"
            result = await connector.publish(
                account,
                creds,
                {
                    "body": "New listing!",
                    "media_urls": ["https://cdn.example.com/img.jpg"],
                },
            )

        assert result["id"] == "media-9"
        assert result["url"] == "https://instagram.com/p/abc"

    @pytest.mark.asyncio
    async def test_publish_requires_media(self):
        connector = InstagramConnector()
        with patch("app.connectors.instagram.settings") as settings, patch(
            "app.connectors.instagram.decrypt_text", return_value="token"
        ):
            settings.instagram_app_id = "app"
            settings.instagram_app_secret = "secret"
            with pytest.raises(IGError) as exc:
                await connector.publish(
                    _account(provider_account_id="ig-1"),
                    _creds(),
                    {"body": "caption only", "media_urls": []},
                )
        assert exc.value.code == "media_required"
