# tg_chats — one row per Telegram chat (private or group). D15. active_book_id NULL => onboarding.
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, SmallInteger, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TgChat(Base):
    __tablename__ = "tg_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    active_book_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("books.id"))
    last_message_id: Mapped[int | None] = mapped_column(BigInteger)
    ui_mode: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    gpt_mode: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    hide_amounts: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
