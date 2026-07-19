"""Pydantic settings shared across services."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Path | None:
    """Search for .env file in current dir and parent directories."""
    start = Path.cwd()
    for directory in [start] + list(start.parents):
        env_file = directory / ".env"
        if env_file.exists():
            return env_file
    # Fallback: check relative to this config file
    config_dir = Path(__file__).resolve().parents[3]  # packages/config/realestate_config -> project root
    env_file = config_dir / ".env"
    if env_file.exists():
        return env_file
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file() or ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = Field(default="development", alias="ENV")
    project_name: str = Field(default="RealEstateSocial", alias="PROJECT_NAME")
    live_domain: str = Field(default="http://localhost:3000", alias="LIVE_DOMAIN")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    # Security
    secret_key: str = Field(alias="SECRET_KEY")
    session_cookie_name: str = Field(default="res_session", alias="SESSION_COOKIE_NAME")
    session_max_age_seconds: int = Field(default=86400, alias="SESSION_MAX_AGE_SECONDS")

    # API / CORS
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_allowed_origins: str | list[str] = Field(default="", alias="CORS_ALLOWED_ORIGINS")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    # Content Security Policy
    csp_default_src: str = Field(default="'self'", alias="CSP_DEFAULT_SRC")
    csp_script_src: str = Field(default="'self'", alias="CSP_SCRIPT_SRC")
    csp_style_src: str = Field(default="'self' 'unsafe-inline'", alias="CSP_STYLE_SRC")
    csp_img_src: str = Field(default="'self' data: https:", alias="CSP_IMG_SRC")
    csp_font_src: str = Field(default="'self'", alias="CSP_FONT_SRC")
    csp_connect_src: str = Field(default="'self'", alias="CSP_CONNECT_SRC")
    csp_frame_ancestors: str = Field(default="'none'", alias="CSP_FRAME_ANCESTORS")
    csp_form_action: str = Field(default="'self'", alias="CSP_FORM_ACTION")
    csp_base_uri: str = Field(default="'self'", alias="CSP_BASE_URI")

    # Database
    database_url: str = Field(alias="DATABASE_URL")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")

    # Redis
    redis_url: str = Field(alias="REDIS_URL")

    # Object storage
    s3_endpoint: str = Field(alias="S3_ENDPOINT")
    s3_access_key: str = Field(alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME")
    s3_public_url: str = Field(alias="S3_PUBLIC_URL")
    s3_use_ssl: bool = Field(default=True, alias="S3_USE_SSL")
    s3_signature_version: str = Field(default="s3v4", alias="S3_SIGNATURE_VERSION")

    # Encryption
    oauth_encryption_key: str = Field(alias="OAUTH_ENCRYPTION_KEY")

    # OAuth credentials
    instagram_app_id: str | None = Field(default=None, alias="INSTAGRAM_APP_ID")
    instagram_app_secret: str | None = Field(default=None, alias="INSTAGRAM_APP_SECRET")
    instagram_redirect_uri: str | None = Field(default=None, alias="INSTAGRAM_REDIRECT_URI")

    x_client_id: str | None = Field(default=None, alias="X_CLIENT_ID")
    x_client_secret: str | None = Field(default=None, alias="X_CLIENT_SECRET")
    x_redirect_uri: str | None = Field(default=None, alias="X_REDIRECT_URI")

    # Webhook secrets
    instagram_webhook_verify_token: str = Field(default="", alias="INSTAGRAM_WEBHOOK_VERIFY_TOKEN")
    instagram_webhook_secret: str = Field(default="", alias="INSTAGRAM_WEBHOOK_SECRET")
    x_webhook_secret: str = Field(default="", alias="X_WEBHOOK_SECRET")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_webhook: int = Field(default=100, alias="RATE_LIMIT_WEBHOOK")
    rate_limit_webhook_window: int = Field(default=60, alias="RATE_LIMIT_WEBHOOK_WINDOW")
    rate_limit_auth: int = Field(default=5, alias="RATE_LIMIT_AUTH")
    rate_limit_auth_window: int = Field(default=60, alias="RATE_LIMIT_AUTH_WINDOW")
    rate_limit_api: int = Field(default=60, alias="RATE_LIMIT_API")
    rate_limit_api_window: int = Field(default=60, alias="RATE_LIMIT_API_WINDOW")
    rate_limit_public: int = Field(default=30, alias="RATE_LIMIT_PUBLIC")
    rate_limit_public_window: int = Field(default=60, alias="RATE_LIMIT_PUBLIC_WINDOW")

    # Feature flags — publishing is live-only (no mock publish path)
    live_instagram_publishing: bool = Field(default=True, alias="LIVE_INSTAGRAM_PUBLISHING")
    live_x_publishing: bool = Field(default=True, alias="LIVE_X_PUBLISHING")
    ai_content_assistance: bool = Field(default=False, alias="AI_CONTENT_ASSISTANCE")
    video_publishing: bool = Field(default=False, alias="VIDEO_PUBLISHING")
    scheduling: bool = Field(default=False, alias="SCHEDULING")
    scheduled_publishing_enabled: bool = Field(default=True, alias="SCHEDULED_PUBLISHING_ENABLED")
    analytics_collection: bool = Field(default=False, alias="ANALYTICS_COLLECTION")
    webhooks: bool = Field(default=False, alias="WEBHOOKS")
    auto_publish_without_review: bool = Field(default=False, alias="AUTO_PUBLISH_WITHOUT_REVIEW")
    watermarking: bool = Field(default=False, alias="WATERMARKING")

    # SMTP
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str | None = Field(default=None, alias="SMTP_FROM")

    # Monitoring
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    error_monitor_provider: str = Field(default="", alias="ERROR_MONITOR_PROVIDER")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_cors(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Parse CORS_ORIGINS env var as a JSON list (e.g. '["http://a.com","http://b.com"]')."""
        if value is None:
            return ["http://localhost:3000"]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                # Fall back to comma-separated if JSON parsing fails
                return [o.strip() for o in value.split(",") if o.strip()]
        if isinstance(value, list):
            return value
        return ["http://localhost:3000"]

    @model_validator(mode="after")
    def _merge_cors_origins(self) -> "Settings":
        """If CORS_ALLOWED_ORIGINS is set but CORS_ORIGINS is at default,
        prefer the legacy value for backward compatibility."""
        # Check if cors_origins is still the factory default
        if self.cors_origins == ["http://localhost:3000"] and self.cors_allowed_origins:
            object.__setattr__(self, "cors_origins", self.cors_allowed_origins)
        return self

    @property
    def is_development(self) -> bool:
        return self.env.lower() in ("development", "testing", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
