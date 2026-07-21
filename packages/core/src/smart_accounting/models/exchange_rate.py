# exchange_rates — historical FX rates from external providers. D16: informational only (weighted-avg
# reads fx_transactions, not this). Feeds the bot's "current rate hint".
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk, currency_code


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "base_currency_code",
            "quote_currency_code",
            "source",
            "fetched_at",
            name="uq_exchange_rates_base_quote_source_fetched",
        ),
        Index(
            "ix_exchange_rates_base_quote_fetched",
            "base_currency_code",
            "quote_currency_code",
            text("fetched_at DESC"),
        ),
    )

    id: Mapped[bigserial_pk]
    base_currency_code: Mapped[currency_code]
    quote_currency_code: Mapped[currency_code]
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
