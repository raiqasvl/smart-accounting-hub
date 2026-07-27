# reports repository — read-only aggregate queries over fx_transactions.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from smart_accounting.common.uow import UoW
from smart_accounting.models import FxTransaction
from smart_accounting.models.fx_transaction import TransactionDirection


class ReportsRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def weighted_avg_rate(
        self,
        book_id: int,
        quote_currency_code: str,
        direction: TransactionDirection,
        occurred_after: datetime | None = None,
        occurred_before: datetime | None = None,
    ) -> tuple[Decimal | None, int, Decimal]:
        """Returns (weighted_avg_rate, sample_count, sum_amount_quote). The average is
        SUM(amount_base)/SUM(amount_quote) (D16); None when no rows match (NULLIF guards /0)."""
        sum_base = func.sum(FxTransaction.amount_base)
        sum_quote = func.sum(FxTransaction.amount_quote)
        stmt = select(
            sum_base / func.nullif(sum_quote, 0),
            func.count(),
            func.coalesce(sum_quote, 0),
        ).where(
            FxTransaction.book_id == book_id,
            FxTransaction.quote_currency_code == quote_currency_code,
            FxTransaction.direction == direction,
            FxTransaction.archived.is_(False),
        )
        if occurred_after is not None:
            stmt = stmt.where(FxTransaction.occurred_at >= occurred_after)
        if occurred_before is not None:
            stmt = stmt.where(FxTransaction.occurred_at < occurred_before)
        row = (await self._session.execute(stmt)).one()
        avg: Decimal | None = row[0]
        count = int(row[1])
        total: Decimal = row[2] if row[2] is not None else Decimal(0)
        return avg, count, total
