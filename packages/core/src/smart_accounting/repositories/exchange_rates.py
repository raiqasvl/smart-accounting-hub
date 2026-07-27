# exchange_rates repository — queries only. D16: these rows are informational (rate hints), never the
# source of truth for the weighted-average (that reads fx_transactions).
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from smart_accounting.common.uow import UoW
from smart_accounting.models import ExchangeRate


class ExchangeRatesRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def insert_many(
        self, *, base: str, source: str, fetched_at: datetime, rates: dict[str, Decimal]
    ) -> int:
        objs = [
            ExchangeRate(
                base_currency_code=base,
                quote_currency_code=quote,
                rate=rate,
                source=source,
                fetched_at=fetched_at,
            )
            for quote, rate in rates.items()
        ]
        self._session.add_all(objs)
        await self._session.flush()
        return len(objs)

    async def latest(self, base: str, quote: str) -> ExchangeRate | None:
        stmt = (
            select(ExchangeRate)
            .where(
                ExchangeRate.base_currency_code == base,
                ExchangeRate.quote_currency_code == quote,
            )
            .order_by(ExchangeRate.fetched_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def latest_cross(self, base: str, quote: str) -> Decimal | None:
        """Base per one quote, computed via the USD pivot the fetcher stores (USD→X = X per USD):
        base_per_quote = (USD→base) / (USD→quote). Returns None if either leg is missing."""
        if base == quote:
            return Decimal(1)
        usd_base = Decimal(1) if base == "USD" else await self._usd_rate(base)
        usd_quote = Decimal(1) if quote == "USD" else await self._usd_rate(quote)
        if usd_base is None or usd_quote is None or usd_quote == 0:
            return None
        return usd_base / usd_quote

    async def _usd_rate(self, code: str) -> Decimal | None:
        row = await self.latest("USD", code)
        return row.rate if row is not None else None
