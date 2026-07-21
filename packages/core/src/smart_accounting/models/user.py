# users — Telegram-identified humans. telegram_user_id is the canonical identity (D-baseline).
from __future__ import annotations

from sqlalchemy import Boolean, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk, tg_user_id


class User(Base):
    __tablename__ = "users"

    id: Mapped[bigserial_pk]
    telegram_user_id: Mapped[tg_user_id]
    telegram_username: Mapped[str | None] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
