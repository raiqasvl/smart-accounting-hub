# fx_transactions — the headline table. One fx trade or one leg of a multi-leg movement.
# D16 invariant: (amount_quote, rate, amount_base) is the source of truth; weighted-avg =
# SUM(amount_base) / SUM(amount_quote).
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk, currency_code, money_amount


class TransactionKind(enum.StrEnum):
    plain_cash = "plain_cash"
    internal_transfer = "internal_transfer"
    fx_conversion = "fx_conversion"


class TransactionDirection(enum.StrEnum):
    buy = "buy"
    sell = "sell"


# Native PG enums; the types are created by the 0001 migration (create_type=False here).
_kind_enum = PgEnum(
    TransactionKind,
    name="transaction_kind",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)
_direction_enum = PgEnum(
    TransactionDirection,
    name="transaction_direction",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class FxTransaction(Base):
    __tablename__ = "fx_transactions"
    __table_args__ = (
        Index(
            "ix_fx_transactions_book_quote_direction_occurred",
            "book_id",
            "quote_currency_code",
            "direction",
            text("occurred_at DESC"),
        ),
        Index("ix_fx_transactions_book_occurred", "book_id", text("occurred_at DESC")),
        Index(
            "ix_fx_transactions_linked",
            "linked_transaction_id",
            postgresql_where=text("linked_transaction_id IS NOT NULL"),
        ),
        # D28: idempotent trade recording (added in 0003). Partial unique so NULL keys are free.
        Index(
            "uq_fx_transactions_book_idempotency",
            "book_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[bigserial_pk]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[TransactionKind] = mapped_column(
        _kind_enum, nullable=False, server_default=text("'plain_cash'")
    )
    direction: Mapped[TransactionDirection] = mapped_column(_direction_enum, nullable=False)
    base_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    quote_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    base_currency_code: Mapped[currency_code]
    quote_currency_code: Mapped[currency_code]
    amount_quote: Mapped[money_amount]
    rate: Mapped[money_amount]
    amount_base: Mapped[money_amount]
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, server_default=text("0"))
    fee_currency_code: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    linked_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("fx_transactions.id"))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    idempotency_key: Mapped[str | None] = mapped_column(Text)
