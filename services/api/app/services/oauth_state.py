"""OAuth state and PKCE helpers backed by Redis."""

import base64
import hashlib
import json
import os
import secrets

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()


def _redis() -> aioredis.Redis:
    """Return a decode_responses=True Redis connection."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def store_oauth_state(state: str, data: dict, ttl: int = 600) -> None:
    """Persist state-tied data in Redis with the given TTL (seconds)."""
    r = _redis()
    key = f"oauth_state:{state}"
    await r.set(key, json.dumps(data), ex=ttl)


async def pop_oauth_state(state: str) -> dict | None:
    """Retrieve and delete the oauth_state key. Returns None if missing."""
    r = _redis()
    key = f"oauth_state:{state}"
    val = await r.get(key)
    if val is None:
        return None
    await r.delete(key)
    return json.loads(val)


def generate_state() -> str:
    """Generate a cryptographically random 32-hex-char OAuth state string."""
    return secrets.token_hex(16)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and its S256 challenge."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge
