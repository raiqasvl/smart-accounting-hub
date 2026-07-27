# TransactionService — records and reads FX trades. One transaction per method (UoW). M3 handles
# single-leg plain_cash trades; two-leg transfers/conversions land in M4. D16: the user-supplied
# rate is authoritative and amount_base = amount_quote * rate is computed here.
from __future__ import annotations

from datetime import UTC, datetime

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.errors import (
    AccountCurrencyMismatch,
    AccountNotInBook,
    CurrencyUnknown,
    InvalidAmount,
    TransactionNotFound,
)
from smart_accounting.models.fx_transaction import TransactionDirection, TransactionKind
from smart_accounting.repositories.accounts import AccountsRepo
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.currencies import CurrenciesRepo
from smart_accounting.repositories.transactions import TransactionsRepo
from smart_accounting.schemas import TransactionCreateIn, TransactionOut, TransactionPatchIn
from smart_accounting.services.authz import resolve_role


class TransactionService:
    def __init__(
        self,
        uow: UoW,
        transactions: TransactionsRepo,
        accounts: AccountsRepo,
        currencies: CurrenciesRepo,
        members: BookMembersRepo,
    ) -> None:
        self._uow = uow
        self._transactions = transactions
        self._accounts = accounts
        self._currencies = currencies
        self._members = members

    async def record(
        self, book_id: int, user_id: int, dto: TransactionCreateIn
    ) -> tuple[TransactionOut, bool]:
        """Returns (transaction, replayed). `replayed` is True when an existing row was returned
        for a repeated idempotency_key (D28) — the caller surfaces it as `Idempotent-Replayed`."""
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.write")

            if dto.idempotency_key is not None:
                existing = await self._transactions.get_by_idempotency(book_id, dto.idempotency_key)
                if existing is not None:
                    return TransactionOut.model_validate(existing), True

            if dto.amount_quote <= 0 or dto.rate <= 0:
                raise InvalidAmount({"field": "amount_quote_or_rate"})
            if dto.fee < 0:
                raise InvalidAmount({"field": "fee"})
            for code in (dto.base_currency_code, dto.quote_currency_code):
                if not await self._currencies.code_visible(book_id, code):
                    raise CurrencyUnknown({"code": code})
            await self._check_account(book_id, dto.base_account_id, dto.base_currency_code)
            await self._check_account(book_id, dto.quote_account_id, dto.quote_currency_code)

            tx = await self._transactions.insert(
                book_id=book_id,
                created_by_user_id=user_id,
                kind=TransactionKind.plain_cash,
                direction=TransactionDirection(dto.direction),
                base_currency_code=dto.base_currency_code,
                quote_currency_code=dto.quote_currency_code,
                amount_quote=dto.amount_quote,
                rate=dto.rate,
                amount_base=dto.amount_quote * dto.rate,
                fee=dto.fee,
                fee_currency_code=dto.fee_currency_code,
                occurred_at=dto.occurred_at or datetime.now(UTC),
                note=dto.note,
                base_account_id=dto.base_account_id,
                quote_account_id=dto.quote_account_id,
                idempotency_key=dto.idempotency_key,
            )
            return TransactionOut.model_validate(tx), False

    async def list_for_book(
        self,
        book_id: int,
        user_id: int,
        *,
        direction: str | None = None,
        quote_currency_code: str | None = None,
        account_id: int | None = None,
        occurred_after: datetime | None = None,
        occurred_before: datetime | None = None,
        archived: bool | None = False,
        after: tuple[datetime, int] | None = None,
        limit: int = 50,
    ) -> list[TransactionOut]:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.read")
            rows = await self._transactions.list_for_book(
                book_id,
                direction=TransactionDirection(direction) if direction is not None else None,
                quote_currency_code=quote_currency_code,
                account_id=account_id,
                occurred_after=occurred_after,
                occurred_before=occurred_before,
                archived=archived,
                after=after,
                limit=limit,
            )
            return [TransactionOut.model_validate(row) for row in rows]

    async def get(self, tx_id: int, user_id: int) -> TransactionOut:
        async with self._uow:
            tx = await self._transactions.get(tx_id)
            if tx is None:
                raise TransactionNotFound({"transaction_id": tx_id})
            role = await resolve_role(self._members, tx.book_id, user_id)
            require_permission(role, "tx.read")
            return TransactionOut.model_validate(tx)

    async def patch(self, tx_id: int, user_id: int, dto: TransactionPatchIn) -> TransactionOut:
        async with self._uow:
            tx = await self._transactions.get(tx_id)
            if tx is None:
                raise TransactionNotFound({"transaction_id": tx_id})
            role = await resolve_role(self._members, tx.book_id, user_id)
            require_permission(role, "tx.write")

            new_amount = dto.amount_quote if dto.amount_quote is not None else tx.amount_quote
            new_rate = dto.rate if dto.rate is not None else tx.rate
            if new_amount <= 0 or new_rate <= 0:
                raise InvalidAmount({"field": "amount_quote_or_rate"})
            recompute = dto.amount_quote is not None or dto.rate is not None
            updated = await self._transactions.update(
                tx_id,
                amount_quote=dto.amount_quote,
                rate=dto.rate,
                amount_base=new_amount * new_rate if recompute else None,
                note=dto.note,
                occurred_at=dto.occurred_at,
                archived=dto.archived,
            )
            assert updated is not None  # loaded above, same transaction
            return TransactionOut.model_validate(updated)

    async def archive(self, tx_id: int, user_id: int) -> None:
        async with self._uow:
            tx = await self._transactions.get(tx_id)
            if tx is None:
                raise TransactionNotFound({"transaction_id": tx_id})
            role = await resolve_role(self._members, tx.book_id, user_id)
            require_permission(role, "tx.write")
            await self._transactions.update(tx_id, archived=True)

    async def _check_account(
        self, book_id: int, account_id: int | None, currency_code: str
    ) -> None:
        if account_id is None:
            return
        account = await self._accounts.get(account_id)
        if account is None or account.book_id != book_id:
            raise AccountNotInBook({"account_id": account_id, "book_id": book_id})
        if account.currency_code != currency_code:
            raise AccountCurrencyMismatch(
                {"account_id": account_id, "expected": currency_code}
            )
