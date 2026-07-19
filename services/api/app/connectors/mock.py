"""Deprecated mock connector — live publishing only.

Kept only so historical `provider=mock` rows fail with a clear error
instead of crashing import paths. New connections and publishes must use
real Instagram / X connectors.
"""

from typing import Any

from app.connectors.base import SocialConnector
from app.models import EncryptedOAuthCredentials, SocialAccount


class MockConnector(SocialConnector):
    """Live-only mode: all mock operations are rejected."""

    async def validate(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials | None,
    ) -> dict[str, Any]:
        return {
            "valid": False,
            "can_publish": False,
            "error": "mock_disabled",
            "message": "Mock connectors are disabled. Connect a live Instagram or X account.",
        }

    async def publish(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        raise RuntimeError(
            "Mock publishing is disabled. Configure LIVE Instagram/X credentials and reconnect accounts."
        )

    async def revoke(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any]:
        return {"revoked": True, "mock": False}

    async def refresh_token(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any] | None:
        return None
