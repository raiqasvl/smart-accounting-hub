# books — top-level multi-tenancy boundary (D2). Every domain row is book_id-scoped.
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk, currency_code


class Book(Base):
    __tablename__ = "books"

    id: Mapped[bigserial_pk]
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 0=personal 1=family 2=business
    base_currency_code: Mapped[currency_code]
    default_language: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
