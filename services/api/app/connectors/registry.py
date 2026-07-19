"""Connector registry mapping provider strings to SocialConnector instances."""

from app.connectors.base import SocialConnector
from app.connectors.instagram import InstagramConnector
from app.connectors.x import XConnector

_registry: dict[str, SocialConnector] = {
    "instagram": InstagramConnector(),
    "x": XConnector(),
}


def get_connector(provider: str) -> SocialConnector:
    """Resolve a provider string to its SocialConnector instance.

    Raises KeyError for unknown providers (including legacy ``mock``).
    """
    try:
        return _registry[provider]
    except KeyError as exc:
        raise KeyError(
            f"Unknown or disabled social provider '{provider}'. "
            "Supported live providers: instagram, x."
        ) from exc


def supported_providers() -> list[str]:
    return list(_registry.keys())
