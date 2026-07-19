"""X (Twitter) API v2 connector — live publishing only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.connectors.base import SocialConnector
from app.models import EncryptedOAuthCredentials, SocialAccount
from app.services.encryption import decrypt_text

settings = get_settings()
logger = structlog.get_logger(__name__)

X_API = "https://api.x.com/2"
X_UPLOAD = "https://upload.twitter.com/1.1/media/upload.json"
X_OAUTH_TOKEN = "https://api.x.com/2/oauth2/token"
X_ME = "https://api.x.com/2/users/me"


class ProviderPublishError(Exception):
    """Raised when a live provider call fails in a structured way."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str = "provider_error"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class XConnector(SocialConnector):
    def _require_configured(self) -> None:
        if not settings.x_client_id or not settings.x_client_secret:
            raise ProviderPublishError(
                "X OAuth is not configured (X_CLIENT_ID / X_CLIENT_SECRET required)",
                code="not_configured",
            )

    def _decrypt_access_token(self, credentials: EncryptedOAuthCredentials) -> str:
        try:
            return decrypt_text(credentials.encrypted_access_token)
        except Exception as exc:
            raise ProviderPublishError("Failed to decrypt X access token", code="decryption_failed") from exc

    async def validate(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials | None,
    ) -> dict[str, Any]:
        self._require_configured()
        if credentials is None:
            return {"valid": False, "error": "missing_credentials"}

        access_token = self._decrypt_access_token(credentials)

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    X_ME,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"user.fields": "id,username,name,profile_image_url"},
                )
                if resp.status_code == 401:
                    return {"valid": False, "error": "unauthorized", "can_publish": False}
                resp.raise_for_status()
                data = resp.json().get("data", {})
                return {
                    "valid": True,
                    "can_publish": True,
                    "max_images": 4,
                    "max_video_seconds": 140,
                    "supports_carousel": False,
                    "supports_threads": True,
                    "provider_account_id": data.get("id"),
                    "username": data.get("username"),
                    "display_name": data.get("name"),
                    "profile_image_url": data.get("profile_image_url"),
                }
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "x_validate_http_error",
                    status=exc.response.status_code,
                    body=exc.response.text[:500],
                )
                return {
                    "valid": False,
                    "error": f"HTTP {exc.response.status_code}",
                    "can_publish": False,
                }
            except httpx.RequestError as exc:
                logger.warning("x_validate_request_error", error=str(exc))
                return {"valid": False, "error": str(exc), "can_publish": False}

    async def publish(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_configured()
        if credentials is None:
            raise ProviderPublishError("Missing OAuth credentials for X account", code="missing_credentials")

        access_token = self._decrypt_access_token(credentials)
        body = (content.get("body") or content.get("title") or "").strip()
        media_urls = list(content.get("media_urls") or [])
        in_reply_to = content.get("in_reply_to_tweet_id") or content.get("reply_to_id")

        if not body and not media_urls:
            raise ProviderPublishError("X post requires text and/or media", code="empty_content")

        # X free/basic text limit is 280; allow longer for premium but warn via truncate policy
        if len(body) > 280:
            # Prefer hard fail so templates are fixed rather than silently truncating
            raise ProviderPublishError(
                f"X post exceeds 280 characters ({len(body)})",
                code="text_too_long",
            )

        async with httpx.AsyncClient(timeout=60) as client:
            media_ids: list[str] = []
            for url in media_urls[:4]:
                media_id = await self._upload_media(client, access_token, url)
                media_ids.append(media_id)

            payload: dict[str, Any] = {}
            if body:
                payload["text"] = body
            if media_ids:
                payload["media"] = {"media_ids": media_ids}
            if in_reply_to:
                payload["reply"] = {"in_reply_to_tweet_id": str(in_reply_to)}

            resp = await client.post(
                f"{X_API}/tweets",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "x_publish_failed",
                    status=resp.status_code,
                    body=resp.text[:800],
                    account_id=str(account.id),
                )
                raise ProviderPublishError(
                    self._extract_error_message(resp),
                    status_code=resp.status_code,
                    code="x_publish_failed",
                )

            data = resp.json().get("data", {})
            tweet_id = data.get("id")
            username = account.username or "i"
            url = f"https://x.com/{username}/status/{tweet_id}" if tweet_id else None
            logger.info(
                "x_publish_success",
                account_id=str(account.id),
                tweet_id=tweet_id,
            )
            return {
                "id": tweet_id,
                "url": url,
                "provider": "x",
                "media_ids": media_ids,
            }

    async def _upload_media(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        media_url: str,
    ) -> str:
        """Download a public image URL and upload it to X media endpoint."""
        try:
            media_resp = await client.get(media_url, follow_redirects=True)
            media_resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderPublishError(
                f"Failed to download media for X upload: {media_url}",
                code="media_download_failed",
            ) from exc

        content_type = media_resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if not content_type.startswith("image/"):
            raise ProviderPublishError(
                f"X media upload currently supports images only (got {content_type})",
                code="unsupported_media",
            )

        # Simple (non-chunked) upload for images under ~5MB
        upload = await client.post(
            X_UPLOAD,
            headers={"Authorization": f"Bearer {access_token}"},
            files={"media": ("media", media_resp.content, content_type)},
        )
        if upload.status_code >= 400:
            logger.warning(
                "x_media_upload_failed",
                status=upload.status_code,
                body=upload.text[:500],
            )
            raise ProviderPublishError(
                f"X media upload failed: {upload.text[:300]}",
                status_code=upload.status_code,
                code="media_upload_failed",
            )

        data = upload.json()
        media_id = data.get("media_id_string") or str(data.get("media_id", ""))
        if not media_id:
            raise ProviderPublishError("X media upload returned no media_id", code="media_upload_failed")
        return media_id

    async def revoke(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any]:
        # X does not expose a simple user-token revoke for all app types; local revoke is enough.
        return {"revoked": True}

    async def refresh_token(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any] | None:
        self._require_configured()
        if not credentials.encrypted_refresh_token:
            return None

        try:
            refresh_token = decrypt_text(credentials.encrypted_refresh_token)
        except Exception:
            logger.warning("x_refresh_decrypt_failed", account_id=str(account.id))
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    X_OAUTH_TOKEN,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": settings.x_client_id,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    auth=(settings.x_client_id or "", settings.x_client_secret or ""),
                )
                resp.raise_for_status()
                data = resp.json()
                expires_in = int(data.get("expires_in", 7200))
                result: dict[str, Any] = {
                    "access_token": data["access_token"],
                    "expires_at": (
                        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    ).isoformat(),
                }
                if "refresh_token" in data:
                    result["refresh_token"] = data["refresh_token"]
                return result
            except Exception:
                logger.exception("x_refresh_failed", account_id=str(account.id))
                return None

    @staticmethod
    def _extract_error_message(resp: httpx.Response) -> str:
        try:
            payload = resp.json()
            if "detail" in payload:
                return str(payload["detail"])
            errors = payload.get("errors") or []
            if errors:
                return str(errors[0].get("message") or errors[0])
            title = payload.get("title")
            if title:
                return f"{title}: {payload.get('detail', resp.text[:200])}"
        except Exception:
            pass
        return f"HTTP {resp.status_code}: {resp.text[:300]}"
