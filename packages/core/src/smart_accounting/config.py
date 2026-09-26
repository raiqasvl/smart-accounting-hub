# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Pydantic-settings shape — single source of truth for runtime config.
# Read once via @lru_cache get_config(); both api and bot processes consume it.
# Env var list mirrors `.env.example`. Fields not read by Python (RESTIC/B2) are ignored via
# `extra="ignore"`. Production refuses to boot without its secrets (see the validator below).
from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secrets production cannot run without. Each defaults to "" so local dev boots from an empty .env.
_PRODUCTION_REQUIRED = ("BOT_TOKEN", "JWT_SECRET", "DOMAIN")
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- core ---
    DOMAIN: str = ""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- telegram ---
    BOT_TOKEN: str = ""
    BOT_USERNAME: str = ""

    # --- jwt (Mini-App auth, D12) ---
    JWT_SECRET: str = ""
    JWT_LIFETIME_SECONDS: int = 1800

    # --- postgres / redis ---
    POSTGRES_DSN: str = (
        "postgresql+asyncpg://smart_accounting:CHANGEME@localhost:5432/smart_accounting"
    )
    REDIS_DSN: str = "redis://localhost:6379/0"

    # --- observability (D17) ---
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None

    # --- fx providers (M3; present in .env.example) ---
    FRANKFURTER_BASE_URL: str = "https://api.frankfurter.dev/v1"
    FX_REFRESH_INTERVAL_SECONDS: int = 3600
    FX_REFRESH_ENABLED: bool = True  # disable in tests / offline; gates the API lifespan task

    @model_validator(mode="after")
    def _require_production_secrets(self) -> Settings:
        # A .env that never reached the server would otherwise boot silently, and an empty
        # JWT_SECRET signs tokens anyone can forge. A container that refuses to start is the
        # better failure.
        if self.ENVIRONMENT != "production":
            return self
        missing = [name for name in _PRODUCTION_REQUIRED if not getattr(self, name)]
        if missing:
            raise ValueError(f"production requires {', '.join(missing)}")
        if len(self.JWT_SECRET) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"production requires JWT_SECRET of at least {_MIN_JWT_SECRET_LENGTH} characters"
            )
        return self


@lru_cache
def get_config() -> Settings:
    return Settings()
