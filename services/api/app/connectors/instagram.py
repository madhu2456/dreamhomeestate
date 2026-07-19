"""Instagram Graph API connector — live content publishing only.

Uses Instagram API with Instagram Login (Business/Creator accounts).
Publishing flow: create media container → poll until FINISHED → media_publish.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.connectors.base import SocialConnector
from app.models import EncryptedOAuthCredentials, SocialAccount
from app.services.encryption import decrypt_text

settings = get_settings()
logger = structlog.get_logger(__name__)

IG_GRAPH = "https://graph.instagram.com"
IG_GRAPH_VERSION = "v21.0"
IG_API_OAUTH = "https://api.instagram.com"


class ProviderPublishError(Exception):
    """Raised when a live provider call fails in a structured way."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str = "provider_error"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class InstagramConnector(SocialConnector):
    def _require_configured(self) -> None:
        if not settings.instagram_app_id or not settings.instagram_app_secret:
            raise ProviderPublishError(
                "Instagram OAuth is not configured (INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET required)",
                code="not_configured",
            )

    def _decrypt_access_token(self, credentials: EncryptedOAuthCredentials) -> str:
        try:
            return decrypt_text(credentials.encrypted_access_token)
        except Exception as exc:
            raise ProviderPublishError(
                "Failed to decrypt Instagram access token",
                code="decryption_failed",
            ) from exc

    def _ig_user_id(self, account: SocialAccount) -> str:
        ig_id = account.provider_account_id
        if not ig_id or ig_id == "pending" or ig_id.startswith("mock-"):
            raise ProviderPublishError(
                "Instagram account is missing a valid provider_account_id (IG user id)",
                code="missing_ig_user_id",
            )
        return str(ig_id)

    async def validate(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials | None,
    ) -> dict[str, Any]:
        self._require_configured()
        if credentials is None:
            return {"valid": False, "error": "missing_credentials", "can_publish": False}

        access_token = self._decrypt_access_token(credentials)

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    f"{IG_GRAPH}/me",
                    params={
                        "fields": "user_id,username,account_type,name",
                        "access_token": access_token,
                    },
                )
                if resp.status_code == 401:
                    return {"valid": False, "error": "unauthorized", "can_publish": False}
                resp.raise_for_status()
                data = resp.json()
                # Instagram Login returns user_id; some responses use id
                user_id = data.get("user_id") or data.get("id")
                return {
                    "valid": True,
                    "can_publish": True,
                    "max_images": 10,
                    "max_video_seconds": 60,
                    "supports_carousel": True,
                    "provider_account_id": str(user_id) if user_id else None,
                    "username": data.get("username"),
                    "account_type": data.get("account_type"),
                    "display_name": data.get("name"),
                }
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "instagram_validate_http_error",
                    status=exc.response.status_code,
                    body=exc.response.text[:500],
                )
                return {
                    "valid": False,
                    "error": f"HTTP {exc.response.status_code}",
                    "can_publish": False,
                }
            except httpx.RequestError as exc:
                logger.warning("instagram_validate_request_error", error=str(exc))
                return {"valid": False, "error": str(exc), "can_publish": False}

    async def publish(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_configured()
        if credentials is None:
            raise ProviderPublishError(
                "Missing OAuth credentials for Instagram account",
                code="missing_credentials",
            )

        access_token = self._decrypt_access_token(credentials)
        ig_user_id = self._ig_user_id(account)
        caption = (content.get("body") or content.get("title") or "").strip()
        media_urls = [u for u in (content.get("media_urls") or []) if u]
        media_kinds = content.get("media_kinds")  # optional parallel list: image|video

        if not media_urls:
            raise ProviderPublishError(
                "Instagram posts require at least one public image or video URL",
                code="media_required",
            )
        if len(caption) > 2200:
            raise ProviderPublishError(
                f"Instagram caption exceeds 2200 characters ({len(caption)})",
                code="text_too_long",
            )

        items = [
            {
                "url": url,
                "kind": self._infer_media_kind(
                    url,
                    media_kinds[i] if isinstance(media_kinds, list) and i < len(media_kinds) else None,
                ),
            }
            for i, url in enumerate(media_urls[:10])
        ]

        async with httpx.AsyncClient(timeout=180) as client:
            if len(items) == 1 and items[0]["kind"] == "video":
                container_id = await self._create_video_container(
                    client,
                    ig_user_id,
                    access_token,
                    video_url=items[0]["url"],
                    caption=caption,
                    is_carousel_item=False,
                )
            elif len(items) == 1:
                container_id = await self._create_image_container(
                    client,
                    ig_user_id,
                    access_token,
                    image_url=items[0]["url"],
                    caption=caption,
                    is_carousel_item=False,
                )
            else:
                child_ids: list[str] = []
                for item in items:
                    if item["kind"] == "video":
                        child_id = await self._create_video_container(
                            client,
                            ig_user_id,
                            access_token,
                            video_url=item["url"],
                            caption="",
                            is_carousel_item=True,
                        )
                    else:
                        child_id = await self._create_image_container(
                            client,
                            ig_user_id,
                            access_token,
                            image_url=item["url"],
                            caption="",
                            is_carousel_item=True,
                        )
                    await self._wait_for_container(client, child_id, access_token)
                    child_ids.append(child_id)

                container_id = await self._create_carousel_container(
                    client,
                    ig_user_id,
                    access_token,
                    children=child_ids,
                    caption=caption,
                )

            await self._wait_for_container(client, container_id, access_token)
            publish_result = await self._publish_container(
                client, ig_user_id, access_token, container_id
            )
            media_id = publish_result.get("id")
            permalink = await self._fetch_permalink(client, media_id, access_token)

            logger.info(
                "instagram_publish_success",
                account_id=str(account.id),
                media_id=media_id,
            )
            return {
                "id": media_id,
                "url": permalink,
                "provider": "instagram",
                "container_id": container_id,
            }

    @staticmethod
    def _infer_media_kind(url: str, hint: str | None = None) -> str:
        if hint in ("image", "video"):
            return hint
        lower = (url or "").lower().split("?", 1)[0]
        if lower.endswith((".mp4", ".mov", ".m4v", ".webm")):
            return "video"
        return "image"

    async def _create_image_container(
        self,
        client: httpx.AsyncClient,
        ig_user_id: str,
        access_token: str,
        *,
        image_url: str,
        caption: str,
        is_carousel_item: bool,
    ) -> str:
        params: dict[str, Any] = {
            "image_url": image_url,
            "access_token": access_token,
        }
        if is_carousel_item:
            params["is_carousel_item"] = "true"
        elif caption:
            params["caption"] = caption

        resp = await client.post(
            f"{IG_GRAPH}/{IG_GRAPH_VERSION}/{ig_user_id}/media",
            data=params,
        )
        if resp.status_code >= 400:
            logger.warning(
                "instagram_create_container_failed",
                status=resp.status_code,
                body=resp.text[:800],
            )
            raise ProviderPublishError(
                self._extract_error_message(resp),
                status_code=resp.status_code,
                code="ig_container_failed",
            )
        container_id = resp.json().get("id")
        if not container_id:
            raise ProviderPublishError("Instagram returned no container id", code="ig_container_failed")
        return str(container_id)

    async def _create_video_container(
        self,
        client: httpx.AsyncClient,
        ig_user_id: str,
        access_token: str,
        *,
        video_url: str,
        caption: str,
        is_carousel_item: bool,
    ) -> str:
        """Create a REELS/VIDEO container from a public video_url."""
        params: dict[str, Any] = {
            "media_type": "REELS" if not is_carousel_item else "VIDEO",
            "video_url": video_url,
            "access_token": access_token,
        }
        if is_carousel_item:
            params["is_carousel_item"] = "true"
            params["media_type"] = "VIDEO"
        elif caption:
            params["caption"] = caption

        resp = await client.post(
            f"{IG_GRAPH}/{IG_GRAPH_VERSION}/{ig_user_id}/media",
            data=params,
        )
        if resp.status_code >= 400:
            logger.warning(
                "instagram_create_video_container_failed",
                status=resp.status_code,
                body=resp.text[:800],
            )
            raise ProviderPublishError(
                self._extract_error_message(resp),
                status_code=resp.status_code,
                code="ig_video_container_failed",
            )
        container_id = resp.json().get("id")
        if not container_id:
            raise ProviderPublishError(
                "Instagram returned no video container id", code="ig_video_container_failed"
            )
        return str(container_id)

    async def _create_carousel_container(
        self,
        client: httpx.AsyncClient,
        ig_user_id: str,
        access_token: str,
        *,
        children: list[str],
        caption: str,
    ) -> str:
        params: dict[str, Any] = {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "access_token": access_token,
        }
        if caption:
            params["caption"] = caption

        resp = await client.post(
            f"{IG_GRAPH}/{IG_GRAPH_VERSION}/{ig_user_id}/media",
            data=params,
        )
        if resp.status_code >= 400:
            raise ProviderPublishError(
                self._extract_error_message(resp),
                status_code=resp.status_code,
                code="ig_carousel_failed",
            )
        container_id = resp.json().get("id")
        if not container_id:
            raise ProviderPublishError("Instagram returned no carousel container id", code="ig_carousel_failed")
        return str(container_id)

    async def _wait_for_container(
        self,
        client: httpx.AsyncClient,
        container_id: str,
        access_token: str,
        *,
        max_attempts: int = 20,
        delay_seconds: float = 2.0,
    ) -> None:
        """Poll container status until FINISHED (or raise on ERROR/timeout)."""
        for attempt in range(max_attempts):
            resp = await client.get(
                f"{IG_GRAPH}/{IG_GRAPH_VERSION}/{container_id}",
                params={
                    "fields": "status_code,status",
                    "access_token": access_token,
                },
            )
            if resp.status_code >= 400:
                # Some image containers are ready without a status endpoint payload
                if attempt == 0:
                    return
                raise ProviderPublishError(
                    self._extract_error_message(resp),
                    status_code=resp.status_code,
                    code="ig_container_status_failed",
                )

            data = resp.json()
            status_code = (data.get("status_code") or data.get("status") or "").upper()
            if status_code in ("", "FINISHED", "PUBLISHED"):
                return
            if status_code in ("ERROR", "EXPIRED"):
                raise ProviderPublishError(
                    f"Instagram media container failed: {data}",
                    code="ig_container_error",
                )
            await asyncio.sleep(delay_seconds)

        raise ProviderPublishError(
            f"Timed out waiting for Instagram media container {container_id}",
            code="ig_container_timeout",
        )

    async def _publish_container(
        self,
        client: httpx.AsyncClient,
        ig_user_id: str,
        access_token: str,
        container_id: str,
    ) -> dict[str, Any]:
        resp = await client.post(
            f"{IG_GRAPH}/{IG_GRAPH_VERSION}/{ig_user_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": access_token,
            },
        )
        if resp.status_code >= 400:
            logger.warning(
                "instagram_media_publish_failed",
                status=resp.status_code,
                body=resp.text[:800],
            )
            raise ProviderPublishError(
                self._extract_error_message(resp),
                status_code=resp.status_code,
                code="ig_publish_failed",
            )
        return resp.json()

    async def _fetch_permalink(
        self,
        client: httpx.AsyncClient,
        media_id: str | None,
        access_token: str,
    ) -> str | None:
        if not media_id:
            return None
        try:
            resp = await client.get(
                f"{IG_GRAPH}/{IG_GRAPH_VERSION}/{media_id}",
                params={"fields": "permalink", "access_token": access_token},
            )
            if resp.status_code < 400:
                return resp.json().get("permalink")
        except httpx.HTTPError:
            pass
        return None

    async def revoke(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any]:
        return {"revoked": True}

    async def refresh_token(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any] | None:
        """Refresh a long-lived Instagram User access token (valid ~60 days)."""
        self._require_configured()
        try:
            access_token = decrypt_text(credentials.encrypted_access_token)
        except Exception:
            logger.warning("instagram_refresh_decrypt_failed", account_id=str(account.id))
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    f"{IG_GRAPH}/refresh_access_token",
                    params={
                        "grant_type": "ig_refresh_token",
                        "access_token": access_token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                expires_in = int(data.get("expires_in", 5184000))
                return {
                    "access_token": data["access_token"],
                    "expires_at": (
                        datetime.now(UTC) + timedelta(seconds=expires_in)
                    ).isoformat(),
                }
            except Exception:
                logger.exception("instagram_refresh_failed", account_id=str(account.id))
                return None

    @staticmethod
    def _extract_error_message(resp: httpx.Response) -> str:
        try:
            payload = resp.json()
            err = payload.get("error") or {}
            if isinstance(err, dict):
                message = err.get("message") or err.get("error_user_msg")
                if message:
                    return str(message)
            if "message" in payload:
                return str(payload["message"])
        except Exception:
            pass
        return f"HTTP {resp.status_code}: {resp.text[:300]}"
