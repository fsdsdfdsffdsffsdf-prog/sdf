"""Application configuration using Pydantic Settings v2.

Loads settings from environment variables and .env file with type validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings class."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Basic Configuration
    APP_NAME: str = "AntiGraffiti AI"
    APP_ENV: str = "production"
    APP_DEBUG: bool = False
    SECRET_KEY: str = Field(
        default="replace_with_a_64_character_cryptographically_secure_key_32bytes",
        description="Secret key for JWT tokens and cryptographic signatures",
    )
    ALLOWED_HOSTS: str = "*"

    # Database Configuration (PostgreSQL 16+)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://antigraffiti_user:antigraffiti_password@localhost:5432/antigraffiti_db",
        description="Async PostgreSQL connection URL",
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # Redis Cache & Broker Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = Field(
        ...,
        description="Bot authentication token obtained from @BotFather",
    )
    TELEGRAM_BOT_USERNAME: str = Field(
        default="antigraffiti_ai_bot",
        description="Telegram bot username without @",
    )

    # Webhook Settings (Production HTTPS Only)
    WEBHOOK_URL: str = Field(
        default="https://example.com",
        description="Public HTTPS URL pointing to the Nginx reverse proxy",
    )
    WEBHOOK_PATH: str = "/webhook/telegram"
    WEBHOOK_SECRET: str = Field(
        ...,
        description="Secret token verified in X-Telegram-Bot-Api-Secret-Token header",
    )

    # AI Vision Settings (OpenAI)
    OPENAI_API_KEY: str = Field(
        ...,
        description="OpenAI API key with access to Vision models",
    )
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TIMEOUT_SECONDS: int = 45
    OPENAI_MAX_RETRIES: int = 3

    # Initial Super Administrator (Provisioned automatically on startup if absent)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = Field(
        default="SuperStrongAdminPassword2026!",
        description="Default super admin password (will be hashed with Argon2id)",
    )
    ADMIN_EMAIL: str = "admin@antigraffiti.local"

    # Media Storage Settings
    STORAGE_PATH: str = "/app/storage"
    MAX_PHOTO_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Geocoding Service Settings
    GEOCODING_USER_AGENT: str = "AntiGraffitiAI/1.0 (urban_monitoring_initiative)"

    @property
    def full_webhook_url(self) -> str:
        """Returns the full public URL for Telegram Webhook."""
        base = self.WEBHOOK_URL.rstrip("/")
        path = self.WEBHOOK_PATH if self.WEBHOOK_PATH.startswith("/") else f"/{self.WEBHOOK_PATH}"
        return f"{base}{path}"

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Parses comma-separated ALLOWED_HOSTS into a list."""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @property
    def storage_dir(self) -> Path:
        """Returns verified Path to storage directory."""
        path = Path(self.STORAGE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        (path / "photos").mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    """Returns singleton cached instance of application settings."""
    return Settings()
