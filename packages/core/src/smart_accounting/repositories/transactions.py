# fx_transactions repository — queries only, no transaction management.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, or_, select

from smart_accounting.common.uow import UoW
from smart_accounting.models import FxTransaction
from smart_accounting.models.fx_transaction import TransactionDirection, TransactionKind


class TransactionsRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def insert(
        self,
        *,
        book_id: int,
        created_by_user_id: int,
        kind: TransactionKind,
        direction: TransactionDirection,
        base_currency_code: str,
        quote_currency_code: str,
        amount_quote: Decimal,
        rate: Decimal,
        amount_base: Decimal,
        fee: Decimal,
        fee_currency_code: str | None,
        occurred_at: datetime,
        note: str | None,
        base_account_id: int | None,
        quote_account_id: int | None,
        category_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> FxTransaction:
        tx = FxTransaction(
            book_id=book_id,
            created_by_user_id=created_by_user_id,
            kind=kind,
            direction=direction,
            base_currency_code=base_currency_code,
            quote_currency_code=quote_currency_code,
            amount_quote=amount_quote,
            rate=rate,
            amount_base=amount_base,
            fee=fee,
            fee_currency_code=fee_currency_code,
            occurred_at=occurred_at,
            note=note,
            base_account_id=base_account_id,
            quote_account_id=quote_account_id,
            category_id=category_id,
            idempotency_key=idempotency_key,
        )
        self._session.add(tx)
        await self._session.flush()
        # Re-read so the NUMERIC(20,8) amounts carry column scale in the create response.
        await self._session.refresh(tx)
        return tx

    async def get(self, tx_id: int) -> FxTransaction | None:
        return await self._session.get(FxTransaction, tx_id)

    async def get_by_idempotency(self, book_id: int, key: str) -> FxTransaction | None:
        result = await self._session.execute(
            select(FxTransaction).where(
                FxTransaction.book_id == book_id,
                FxTransaction.idempotency_key == key,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_book(
        self,
        book_id: int,
        *,
        direction: TransactionDirection | None = None,
        quote_currency_code: str | None = None,
        account_id: int | None = None,
        occurred_after: datetime | None = None,
        occurred_before: datetime | None = None,
        archived: bool | None = False,
        after: tuple[datetime, int] | None = None,
        limit: int = 50,
    ) -> list[FxTransaction]:
        stmt = select(FxTransaction).where(FxTransaction.book_id == book_id)
        if archived is not None:
            stmt = stmt.where(FxTransaction.archived.is_(archived))
        if direction is not None:
            stmt = stmt.where(FxTransaction.direction == direction)
        if quote_currency_code is not None:
            stmt = stmt.where(FxTransaction.quote_currency_code == quote_currency_code)
        if account_id is not None:
            stmt = stmt.where(
                or_(
                    FxTransaction.base_account_id == account_id,
                    FxTransaction.quote_account_id == account_id,
                )
            )
        if occurred_after is not None:
            stmt = stmt.where(FxTransaction.occurred_at >= occurred_after)
        if occurred_before is not None:
            stmt = stmt.where(FxTransaction.occurred_at < occurred_before)
        if after is not None:
            after_at, after_id = after
            # keyset over (occurred_at DESC, id DESC) — the next page is strictly "older".
            stmt = stmt.where(
                or_(
                    FxTransaction.occurred_at < after_at,
                    and_(
                        FxTransaction.occurred_at == after_at,
                        FxTransaction.id < after_id,
                    ),
                )
            )
        stmt = stmt.order_by(FxTransaction.occurred_at.desc(), FxTransaction.id.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        tx_id: int,
        *,
        amount_quote: Decimal | None = None,
        rate: Decimal | None = None,
        amount_base: Decimal | None = None,
        note: str | None = None,
        occurred_at: datetime | None = None,
        archived: bool | None = None,
    ) -> FxTransaction | None:
        tx = await self._session.get(FxTransaction, tx_id)
        if tx is None:
            return None
        if amount_quote is not None:
            tx.amount_quote = amount_quote
        if rate is not None:
            tx.rate = rate
        if amount_base is not None:
            tx.amount_base = amount_base
        if note is not None:
            tx.note = note
        if occurred_at is not None:
            tx.occurred_at = occurred_at
        if archived is not None:
            tx.archived = archived
        await self._session.flush()
        await self._session.refresh(tx)
        return tx
