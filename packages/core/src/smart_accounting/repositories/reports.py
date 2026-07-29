# reports repository — read-only aggregate queries over fx_transactions.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select

from smart_accounting.common.uow import UoW
from smart_accounting.models import FxTransaction
from smart_accounting.models.fx_transaction import TransactionDirection, TransactionKind


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
        SUM(amount_base)/SUM(amount_quote) (D16); None when no rows match (NULLIF guards /0).

        Internal transfers are excluded: they carry a synthetic rate of 1 (no FX happened), so
        counting them would drag the headline average toward 1."""
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
            FxTransaction.kind != TransactionKind.internal_transfer,
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

    async def legs_for_account(
        self,
        book_id: int,
        account_id: int,
        occurred_after: datetime | None = None,
        occurred_before: datetime | None = None,
    ) -> list[FxTransaction]:
        """Every non-archived row touching this account, oldest first — the input to a running
        balance."""
        stmt = select(FxTransaction).where(
            FxTransaction.book_id == book_id,
            FxTransaction.archived.is_(False),
            or_(
                FxTransaction.base_account_id == account_id,
                FxTransaction.quote_account_id == account_id,
            ),
        )
        if occurred_after is not None:
            stmt = stmt.where(FxTransaction.occurred_at >= occurred_after)
        if occurred_before is not None:
            stmt = stmt.where(FxTransaction.occurred_at < occurred_before)
        stmt = stmt.order_by(FxTransaction.occurred_at, FxTransaction.id)
        return list((await self._session.execute(stmt)).scalars().all())
