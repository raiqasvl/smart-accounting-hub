# UserOut — the user DTO that crosses the service boundary (never the ORM entity).
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    telegram_user_id: int
    first_name: str | None = None
    last_name: str | None = None
    # ORM attribute is `telegram_username`; wire field is `username`.
    username: str | None = Field(default=None, validation_alias="telegram_username")
    language: str
    timezone: str
