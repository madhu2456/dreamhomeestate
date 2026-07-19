"""Feature flag service with env-var overrides and auto-discovery from settings."""

import os
from functools import lru_cache

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class FeatureFlagService:
    """Centralized feature flag evaluation.

    Priority: env var FEATURE_{FLAG} > settings-based flag > per-org override > default (False).
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._known_flags: dict[str, bool] = self._build_flag_registry()

    def _build_flag_registry(self) -> dict[str, bool]:
        """Auto-discover feature flags from settings and define hard-coded always-on ones."""
        flags: dict[str, bool] = {}

        # Always-on flags (not gated by settings)
        flags["content_previews"] = True
        flags["publication_engine"] = True

        # Known mappings: flag_name → settings attribute name
        known_mappings: dict[str, str] = {
            "live_instagram_publishing": "live_instagram_publishing",
            "live_x_publishing": "live_x_publishing",
            "webhooks": "webhooks",
            "scheduled_publishing": "scheduled_publishing_enabled",
        }

        for flag_name, attr_name in known_mappings.items():
            flags[flag_name] = bool(getattr(self._settings, attr_name, False))

        # Auto-discover additional bool fields from settings that look like feature flags
        for name, field_info in self._settings.model_fields.items():
            if field_info.annotation is bool:
                if (
                    name.startswith("live_")
                    or name.endswith("_enabled")
                    or "_flag" in name
                    or name.endswith("_publishing")
                ):
                    if name not in known_mappings.values():
                        flags[name] = bool(getattr(self._settings, name, False))

        return flags

    def is_enabled(self, flag_name: str, org_id: str | None = None) -> bool:
        """Check whether a feature flag is enabled.

        Resolution order:
        1. Environment variable ``FEATURE_{FLAG_NAME}`` (uppercased).
        2. Settings-based boolean flag value.
        3. Future: per-org override from ``organization.feature_flags`` JSONB column.
        4. Default: ``False``.
        """
        del org_id  # reserved for per-org override (future)

        # 1. Highest priority: explicit FEATURE_* env var override
        env_key = f"FEATURE_{flag_name.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            if env_val.lower() in ("true", "1"):
                return True
            if env_val.lower() in ("false", "0"):
                return False

        # 2. Settings-based flag
        if flag_name in self._known_flags:
            return self._known_flags[flag_name]

        # 3. TODO: per-org override from Organization.feature_flags JSONB
        #    when that column is added to the Organization model.

        # 4. Default deny
        return False

    def list_flags(self, org_id: str | None = None) -> dict[str, bool]:
        """Return all known feature flags and their current evaluated state."""
        return {name: self.is_enabled(name, org_id) for name in sorted(self._known_flags)}


@lru_cache
def get_feature_flags() -> FeatureFlagService:
    """Singleton factory for the feature flag service."""
    return FeatureFlagService()
