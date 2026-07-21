# currencies repository — queries only. System rows (book_id NULL) + per-book overrides.
from __future__ import annotations

from sqlalchemy import or_, select

from smart_accounting.common.uow import UoW
from smart_accounting.models import Currency


class CurrenciesRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def list_visible(self, book_id: int) -> list[Currency]:
        """System catalogue + this book's overrides (FinWave's `book_id IS NULL OR = $1`)."""
        result = await self._session.execute(
            select(Currency)
            .where(or_(Currency.book_id.is_(None), Currency.book_id == book_id))
            .order_by(Currency.kind, Currency.code)
        )
        return list(result.scalars().all())

    async def code_visible(self, book_id: int, code: str) -> bool:
        result = await self._session.execute(
            select(Currency.id)
            .where(
                or_(Currency.book_id.is_(None), Currency.book_id == book_id),
                Currency.code == code,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_book_override(self, book_id: int, code: str) -> Currency | None:
        result = await self._session.execute(
            select(Currency).where(Currency.book_id == book_id, Currency.code == code)
        )
        return result.scalar_one_or_none()

    async def insert(
        self, *, book_id: int | None, code: str, symbol: str, decimals: int, kind: int
    ) -> Currency:
        currency = Currency(book_id=book_id, code=code, symbol=symbol, decimals=decimals, kind=kind)
        self._session.add(currency)
        await self._session.flush()
        return currency
