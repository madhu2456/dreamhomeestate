"""Redis-based distributed lock for job leases."""

import uuid

import redis.asyncio as aioredis

from app.config import get_settings

LUA_RELEASE = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


async def acquire_lock(
    lock_name: str,
    ttl_seconds: int = 300,
    owner_id: str | None = None,
) -> str | None:
    """Try to acquire a Redis lock.

    Returns the owner_id string on success, None if already held.
    """
    settings = get_settings()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    owner = owner_id or str(uuid.uuid4())
    acquired = await r.set(lock_name, owner, nx=True, ex=ttl_seconds)
    await r.aclose()
    return owner if acquired else None


async def release_lock(lock_name: str, owner_id: str) -> bool:
    """Release the lock only if we still own it (safe, atomic Lua script)."""
    settings = get_settings()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    released = await r.eval(LUA_RELEASE, 1, lock_name, owner_id)
    await r.aclose()
    return bool(released)


async def renew_lock(lock_name: str, owner_id: str, ttl_seconds: int = 300) -> bool:
    """Extend the TTL of a lock we own.

    Returns True if renewed, False if we no longer own it.
    """
    settings = get_settings()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    result = await r.expire(lock_name, ttl_seconds)
    await r.aclose()
    return bool(result)


def job_lock_key(job_id: str) -> str:
    return f"job_lease:{job_id}"


def outbox_lock_key() -> str:
    return "outbox:lease"


def scheduled_lock_key() -> str:
    return "scheduled:lease"
