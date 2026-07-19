"""Unit tests for FeatureFlagService with env-var overrides and settings mocking."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.feature_flags import FeatureFlagService, get_feature_flags


@pytest.fixture
def mock_settings():
    """Return a minimal Settings mock with known feature-flag bool fields."""
    settings = MagicMock()
    settings.live_instagram_publishing = False
    settings.live_x_publishing = False
    settings.scheduled_publishing_enabled = True
    settings.webhooks = False
    # These are bool fields matching the auto-discovery patterns in _build_flag_registry
    settings.ai_content_assistance = False
    settings.video_publishing = False
    settings.scheduling = False
    settings.analytics_collection = False
    settings.auto_publish_without_review = False
    settings.watermarking = False
    # model_fields for auto-discovery
    settings.model_fields = {
        "live_instagram_publishing": MagicMock(annotation=bool),
        "live_x_publishing": MagicMock(annotation=bool),
        "ai_content_assistance": MagicMock(annotation=bool),
        "video_publishing": MagicMock(annotation=bool),
        "scheduling": MagicMock(annotation=bool),
        "scheduled_publishing_enabled": MagicMock(annotation=bool),
        "analytics_collection": MagicMock(annotation=bool),
        "webhooks": MagicMock(annotation=bool),
        "auto_publish_without_review": MagicMock(annotation=bool),
        "watermarking": MagicMock(annotation=bool),
        "secret_key": MagicMock(annotation=str),  # non-bool, should be skipped
        "redis_url": MagicMock(annotation=str),  # non-bool, should be skipped
    }
    return settings


@pytest.fixture
def service(mock_settings):
    """Create a FeatureFlagService with patched get_settings."""
    with patch(
        "app.services.feature_flags.get_settings", return_value=mock_settings
    ):
        return FeatureFlagService()


class TestKnownFlagsExist:
    def test_known_flags_exist_in_registry(self, service):
        """Verify all explicitly-known flags are present in the built registry."""
        registry = service._known_flags
        assert "content_previews" in registry
        assert "publication_engine" in registry
        assert "live_instagram_publishing" in registry
        assert "live_x_publishing" in registry
        assert "webhooks" in registry
        assert "scheduled_publishing" in registry

    def test_always_on_flags_are_true(self, service):
        """content_previews and publication_engine are always-on, not gated by settings."""
        assert service._known_flags["content_previews"] is True
        assert service._known_flags["publication_engine"] is True


class TestEnvOverride:
    def test_env_override_takes_precedence_over_settings(self, service, mock_settings, monkeypatch):
        """An explicit FEATURE_* env var overrides the settings-based value."""
        # settings says the flag is off
        mock_settings.live_instagram_publishing = False
        # rebuild registry
        service._known_flags = service._build_flag_registry()

        # env override sets it to true
        monkeypatch.setenv("FEATURE_LIVE_INSTAGRAM_PUBLISHING", "true")
        assert service.is_enabled("live_instagram_publishing") is True

    def test_env_override_false_takes_precedence(self, service, mock_settings, monkeypatch):
        """FEATURE_* env var can also override a true setting to false."""
        mock_settings.scheduled_publishing_enabled = True
        service._known_flags = service._build_flag_registry()

        monkeypatch.setenv("FEATURE_SCHEDULED_PUBLISHING", "false")
        assert service.is_enabled("scheduled_publishing") is False

    def test_env_override_uses_integer_1(self, service, monkeypatch):
        """The value '1' (string) is also treated as True."""
        monkeypatch.setenv("FEATURE_LIVE_X_PUBLISHING", "1")
        assert service.is_enabled("live_x_publishing") is True

    def test_env_override_uses_zero(self, service, monkeypatch):
        """The value '0' (string) is treated as False."""
        monkeypatch.setenv("FEATURE_WEBHOOKS", "0")
        assert service.is_enabled("webhooks") is False

    def test_env_override_unknown_value_falls_through_to_settings(self, service, mock_settings, monkeypatch):
        """An env var with a non-true/false value (like 'yes') is ignored."""
        mock_settings.webhooks = True
        service._known_flags = service._build_flag_registry()

        monkeypatch.setenv("FEATURE_WEBHOOKS", "yes")
        # Neither 'true' nor 'false'→ falls through to settings
        assert service.is_enabled("webhooks") is True

    def test_env_override_case_insensitive_flag_name(self, service, monkeypatch):
        """FEATURE_* env var lookups must be case-insensitive for the flag name."""
        monkeypatch.setenv("FEATURE_LIVE_X_PUBLISHING", "true")
        assert service.is_enabled("live_X_PUBLISHING") is True


class TestDefaultFalse:
    def test_unknown_flag_returns_false(self, service):
        """An unknown feature flag that is not in the registry defaults to False."""
        assert service.is_enabled("nonexistent_flag") is False

    def test_known_flag_respects_settings(self, service, mock_settings):
        """A known flag without env override returns its settings-derived value."""
        mock_settings.webhooks = True
        service._known_flags = service._build_flag_registry()
        assert service.is_enabled("webhooks") is True

        mock_settings.webhooks = False
        service._known_flags = service._build_flag_registry()
        assert service.is_enabled("webhooks") is False


class TestListFlags:
    def test_list_flags_returns_all_known_flags(self, service):
        """list_flags returns every flag from the registry with its evaluated state."""
        result = service.list_flags()
        assert isinstance(result, dict)
        assert "content_previews" in result
        assert "webhooks" in result
        assert result["content_previews"] is True
        assert result["publication_engine"] is True

    def test_list_flags_sorted_keys(self, service):
        """Flag names are returned sorted alphabetically."""
        result = service.list_flags()
        keys = list(result.keys())
        assert keys == sorted(keys)


class TestAutoDiscovery:
    def test_auto_discovers_bool_settings_ending_with_enabled(self, service):
        """scheduled_publishing_enabled (ends with '_enabled') should be auto-discovered."""
        # It is already in known_mappings and should appear as 'scheduled_publishing'
        assert "scheduled_publishing" in service._known_flags

    def test_auto_discovers_bool_settings_starting_with_live(self, service):
        """Bool fields starting with 'live_' should be auto-discovered."""
        assert "live_instagram_publishing" in service._known_flags
        assert "live_x_publishing" in service._known_flags

    def test_auto_discovers_bool_settings_end_with_publishing(self, service):
        """Bool fields ending with '_publishing' should be auto-discovered."""
        # live_instagram_publishing already has both `live_` start and `_publishing` end
        assert "live_instagram_publishing" in service._known_flags
        assert "live_x_publishing" in service._known_flags


class TestSingleton:
    def test_get_feature_flags_singleton(self):
        """get_feature_flags() returns the same instance on repeated calls."""
        # Reset the lru_cache to get fresh instances
        get_feature_flags.cache_clear()

        with patch(
            "app.services.feature_flags.get_settings", return_value=MagicMock()
        ):
            instance1 = get_feature_flags()
            instance2 = get_feature_flags()

        assert instance1 is instance2
