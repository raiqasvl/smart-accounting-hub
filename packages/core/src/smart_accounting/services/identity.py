# TgIdentity — the Telegram identity a service needs to onboard a user. A plain data holder so
# both the API (from verified initData) and the bot (from an aiogram Message) can build it
# without the core depending on aiogram.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TgIdentity:
    telegram_user_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    language_code: str | None

    @classmethod
    def from_init_data(cls, parsed: dict[str, Any]) -> TgIdentity:
        user: dict[str, Any] = parsed.get("user") or {}
        return cls(
            telegram_user_id=int(user["id"]),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            username=user.get("username"),
            language_code=user.get("language_code"),
        )
