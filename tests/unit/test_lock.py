"""Unit tests for Redis-based distributed lock service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.lock import (
    acquire_lock,
    job_lock_key,
    outbox_lock_key,
    release_lock,
    renew_lock,
    scheduled_lock_key,
)


@pytest.fixture
def mock_redis():
    """Return an AsyncMock standing in for a redis.asyncio.Redis client."""
    return AsyncMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.redis_url = "redis://localhost:6379/0"
    return settings


class TestAcquireLock:
    async def test_acquire_lock_success(self, mock_redis, mock_settings):
        """Verify SET NX is called with correct key, owner, and TTL."""
        mock_redis.set.return_value = True

        with patch(
            "app.services.lock.get_settings", return_value=mock_settings
        ), patch("app.services.lock.aioredis.from_url", return_value=mock_redis):
            result = await acquire_lock("test_lock", ttl_seconds=120, owner_id="owner-42")

        assert result == "owner-42"
        mock_redis.set.assert_called_once_with("test_lock", "owner-42", nx=True, ex=120)
        mock_redis.aclose.assert_called_once()

    async def test_acquire_lock_contended(self, mock_redis, mock_settings):
        """When Redis returns False for SET NX, acquire_lock returns None."""
        mock_redis.set.return_value = False

        with patch(
            "app.services.lock.get_settings", return_value=mock_settings
        ), patch("app.services.lock.aioredis.from_url", return_value=mock_redis):
            result = await acquire_lock("locked_resource", owner_id="owner-1")

        assert result is None
        mock_redis.set.assert_called_once()
        mock_redis.aclose.assert_called_once()

    async def test_acquire_lock_generates_uuid_owner(self, mock_redis, mock_settings):
        """When no owner_id is provided, a UUID string is generated."""
        mock_redis.set.return_value = True

        with patch(
            "app.services.lock.get_settings", return_value=mock_settings
        ), patch("app.services.lock.aioredis.from_url", return_value=mock_redis):
            result = await acquire_lock("job_123")

        # result should be a 36-character UUID string
        assert result is not None
        assert len(result) == 36
        assert result.count("-") == 4
        mock_redis.set.assert_called_once()


class TestReleaseLock:
    async def test_release_lock_calls_eval_with_lua_script(self, mock_redis, mock_settings):
        """Verify EVAL is called with the correct Lua release script and args."""
        mock_redis.eval.return_value = 1

        with patch(
            "app.services.lock.get_settings", return_value=mock_settings
        ), patch("app.services.lock.aioredis.from_url", return_value=mock_redis):
            result = await release_lock("test_lock", "owner-99")

        assert result is True
        # EVAL called with (script, num_keys, key, owner_id)
        mock_redis.eval.assert_called_once()
        args = mock_redis.eval.call_args[0]
        assert len(args) == 4
        assert "redis.call" in args[0]  # LUA script
        assert args[1] == 1  # num_keys
        assert args[2] == "test_lock"  # key
        assert args[3] == "owner-99"  # owner_id
        mock_redis.aclose.assert_called_once()

    async def test_release_lock_returns_false_when_not_owner(self, mock_redis, mock_settings):
        """When the Lua script returns 0, release_lock returns False."""
        mock_redis.eval.return_value = 0

        with patch(
            "app.services.lock.get_settings", return_value=mock_settings
        ), patch("app.services.lock.aioredis.from_url", return_value=mock_redis):
            result = await release_lock("stolen_lock", "wrong-owner")

        assert result is False


class TestRenewLock:
    async def test_renew_lock_calls_expire(self, mock_redis, mock_settings):
        """Verify EXPIRE is called on the lock key with the given TTL."""
        mock_redis.expire.return_value = 1

        with patch(
            "app.services.lock.get_settings", return_value=mock_settings
        ), patch("app.services.lock.aioredis.from_url", return_value=mock_redis):
            result = await renew_lock("test_lock", "owner-1", ttl_seconds=600)

        assert result is True
        mock_redis.expire.assert_called_once_with("test_lock", 600)
        mock_redis.aclose.assert_called_once()

    async def test_renew_lock_returns_false_when_expired(self, mock_redis, mock_settings):
        """When EXPIRE returns 0 (key doesn't exist), renew_lock returns False."""
        mock_redis.expire.return_value = 0

        with patch(
            "app.services.lock.get_settings", return_value=mock_settings
        ), patch("app.services.lock.aioredis.from_url", return_value=mock_redis):
            result = await renew_lock("expired_lock", "owner-1")

        assert result is False


class TestLockKeyFormats:
    def test_job_lock_key_format(self):
        """Verify job lock key uses the correct prefix."""
        assert job_lock_key("abc-123") == "job_lease:abc-123"
        assert job_lock_key("") == "job_lease:"

    def test_outbox_lock_key_format(self):
        """Verify outbox lock key is a fixed string."""
        assert outbox_lock_key() == "outbox:lease"

    def test_scheduled_lock_key_format(self):
        """Verify scheduled lock key is a fixed string."""
        assert scheduled_lock_key() == "scheduled:lease"
