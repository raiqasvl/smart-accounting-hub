# book_invites — single-use magic-link invitations. token = secrets.token_urlsafe(24).
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk


class BookInvite(Base):
    __tablename__ = "book_invites"

    id: Mapped[bigserial_pk]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    invited_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    role: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
