# book_members — junction table user x book x role. PK (book_id, user_id). role enum in auth/rbac.py.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BookMember(Base):
    __tablename__ = "book_members"

    book_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("books.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    role: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 0=owner 1=admin 2=editor 3=viewer
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
