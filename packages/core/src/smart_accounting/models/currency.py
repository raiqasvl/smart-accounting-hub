# currencies — fiat + crypto + metals catalogue with per-book overrides. book_id NULL => system row.
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk, currency_code


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (UniqueConstraint("book_id", "code", name="uq_currencies_book_id_code"),)

    id: Mapped[bigserial_pk]
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"))
    code: Mapped[currency_code]
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    decimals: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    kind: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )  # 0=fiat 1=crypto 2=metal
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
