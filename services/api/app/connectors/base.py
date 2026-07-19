"""Abstract base for social-media platform connectors."""

from abc import ABC, abstractmethod
from typing import Any

from app.models import EncryptedOAuthCredentials, SocialAccount


class SocialConnector(ABC):
    """Interface every platform connector must implement."""

    @abstractmethod
    async def validate(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials | None,
    ) -> dict[str, Any]:
        """Validate the connection and return capabilities/status dict."""
        ...

    @abstractmethod
    async def publish(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        """Post content to the live platform. Must not use mocks."""
        ...

    @abstractmethod
    async def revoke(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any]:
        """Revoke the token on the platform side if supported."""
        ...

    async def refresh_token(
        self,
        account: SocialAccount,
        credentials: EncryptedOAuthCredentials,
    ) -> dict[str, Any] | None:
        """Refresh the access token if supported.

        Returns a dict with ``access_token`` (and optionally ``refresh_token``,
        ``expires_at``) on success, or ``None`` if the connector does not
        support token refresh (the default).
        """
        return None
