# Production must refuse to boot with an unset secret. Every Settings field has a default so local
# dev runs from an empty .env; in production that same default is a silent hole.
from __future__ import annotations

import pytest
from pydantic import ValidationError

from smart_accounting.config import Settings

PRODUCTION = {
    "ENVIRONMENT": "production",
    "BOT_TOKEN": "123456:prod-bot-token",
    "JWT_SECRET": "x" * 32,
    "DOMAIN": "accounting.example.com",
}


def settings(**overrides: object) -> Settings:
    # _env_file=None: a developer's local .env must not leak into these cases.
    return Settings(_env_file=None, **{**PRODUCTION, **overrides})  # type: ignore[arg-type]


def test_development_boots_with_empty_secrets() -> None:
    s = Settings(_env_file=None, ENVIRONMENT="development", BOT_TOKEN="", JWT_SECRET="", DOMAIN="")
    assert s.JWT_SECRET == ""


def test_production_boots_when_complete() -> None:
    assert settings().ENVIRONMENT == "production"


@pytest.mark.parametrize("field", ["BOT_TOKEN", "JWT_SECRET", "DOMAIN"])
def test_production_rejects_missing_secret(field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        settings(**{field: ""})


def test_production_names_every_missing_field_at_once() -> None:
    with pytest.raises(ValidationError) as excinfo:
        settings(BOT_TOKEN="", DOMAIN="")
    assert "BOT_TOKEN" in str(excinfo.value)
    assert "DOMAIN" in str(excinfo.value)


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        settings(JWT_SECRET="x" * 31)
