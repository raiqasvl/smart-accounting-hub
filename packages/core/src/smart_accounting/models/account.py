# accounts — places money sits (cash/bank/card/brokerage). One currency each; fx happens between them.
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk, currency_code


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[bigserial_pk]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    currency_code: Mapped[currency_code]  # not a FK — per-book overrides; service-layer validates
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 0=cash 1=bank 2=card 3=brokerage 4=other
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, server_default=text("0")
    )
