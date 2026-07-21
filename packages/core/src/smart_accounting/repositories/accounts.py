# accounts repository — queries only, no transaction management.
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, func, or_, select

from smart_accounting.common.uow import UoW
from smart_accounting.models import Account, FxTransaction


class AccountsRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def insert(
        self, *, book_id: int, currency_code: str, name: str, kind: int, opening_balance: Decimal
    ) -> Account:
        account = Account(
            book_id=book_id,
            currency_code=currency_code,
            name=name,
            kind=kind,
            opening_balance=opening_balance,
        )
        self._session.add(account)
        await self._session.flush()
        # Re-read so opening_balance carries the column's NUMERIC(20,8) scale (e.g. 500.00000000),
        # keeping the create response byte-identical to what later GETs serialize.
        await self._session.refresh(account)
        return account

    async def get(self, account_id: int) -> Account | None:
        return await self._session.get(Account, account_id)

    async def list_for_book(self, book_id: int, archived: bool | None = None) -> list[Account]:
        stmt = select(Account).where(Account.book_id == book_id)
        if archived is not None:
            stmt = stmt.where(Account.archived.is_(archived))
        result = await self._session.execute(stmt.order_by(Account.id))
        return list(result.scalars().all())

    async def update(
        self, account_id: int, *, name: str | None = None, archived: bool | None = None
    ) -> Account | None:
        account = await self._session.get(Account, account_id)
        if account is None:
            return None
        if name is not None:
            account.name = name
        if archived is not None:
            account.archived = archived
        await self._session.flush()
        return account

    async def delete(self, account_id: int) -> None:
        await self._session.execute(delete(Account).where(Account.id == account_id))

    async def has_transactions(self, account_id: int) -> bool:
        """True if any fx_transaction references this account (either leg) — blocks hard delete."""
        result = await self._session.execute(
            select(func.count())
            .select_from(FxTransaction)
            .where(
                or_(
                    FxTransaction.base_account_id == account_id,
                    FxTransaction.quote_account_id == account_id,
                )
            )
        )
        return (result.scalar_one() or 0) > 0
