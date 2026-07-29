# TransactionService — records and reads FX trades. One transaction per method (UoW).
#
# D16: the user-supplied rate is authoritative and amount_base = amount_quote * rate.
#
# Account-to-account movements (M4) are ONE row that touches both accounts via
# quote_account_id (money out) and base_account_id (money in) — the schema carries both FKs.
# A second "mirror" leg would double-count in the weighted-average (the buy leg of a USD->EUR
# conversion would read as "bought USD"), so a movement stays a single economic event.
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.errors import (
    AccountCurrencyMismatch,
    AccountNotInBook,
    CategoryNotFound,
    CurrencyUnknown,
    InvalidAmount,
    InvalidTransfer,
    TransactionNotFound,
)
from smart_accounting.models import Account
from smart_accounting.models.fx_transaction import TransactionDirection, TransactionKind
from smart_accounting.repositories.accounts import AccountsRepo
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.categories import CategoriesRepo
from smart_accounting.repositories.currencies import CurrenciesRepo
from smart_accounting.repositories.transactions import TransactionsRepo
from smart_accounting.schemas import (
    FxConversionCreateIn,
    TransactionCreateIn,
    TransactionExportRow,
    TransactionOut,
    TransactionPatchIn,
    TransferCreateIn,
)
from smart_accounting.services.authz import resolve_role

# Upper bound on one export so a huge book can't exhaust memory; surfaced in the CSV route.
EXPORT_LIMIT = 10_000


class TransactionService:
    def __init__(
        self,
        uow: UoW,
        transactions: TransactionsRepo,
        accounts: AccountsRepo,
        currencies: CurrenciesRepo,
        categories: CategoriesRepo,
        members: BookMembersRepo,
    ) -> None:
        self._uow = uow
        self._transactions = transactions
        self._accounts = accounts
        self._currencies = currencies
        self._categories = categories
        self._members = members

    async def record(
        self, book_id: int, user_id: int, dto: TransactionCreateIn
    ) -> tuple[TransactionOut, bool]:
        """Returns (transaction, replayed). `replayed` is True when an existing row was returned
        for a repeated idempotency_key (D28) — the caller surfaces it as `Idempotent-Replayed`."""
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.write")

            replay = await self._replay(book_id, dto.idempotency_key)
            if replay is not None:
                return replay, True

            if dto.amount_quote <= 0 or dto.rate <= 0:
                raise InvalidAmount({"field": "amount_quote_or_rate"})
            if dto.fee < 0:
                raise InvalidAmount({"field": "fee"})
            for code in (dto.base_currency_code, dto.quote_currency_code):
                if not await self._currencies.code_visible(book_id, code):
                    raise CurrencyUnknown({"code": code})
            await self._check_account(book_id, dto.base_account_id, dto.base_currency_code)
            await self._check_account(book_id, dto.quote_account_id, dto.quote_currency_code)
            await self._check_category(book_id, dto.category_id)

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
                category_id=dto.category_id,
                idempotency_key=dto.idempotency_key,
            )
            return TransactionOut.model_validate(tx), False

    async def record_transfer(
        self, book_id: int, user_id: int, dto: TransferCreateIn
    ) -> tuple[TransactionOut, bool]:
        """Same-currency movement between two of the book's accounts. Rate is 1 and the row is
        kind=internal_transfer, which the weighted-average report excludes (no FX happened)."""
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.write")
            replay = await self._replay(book_id, dto.idempotency_key)
            if replay is not None:
                return replay, True
            if dto.amount <= 0:
                raise InvalidAmount({"field": "amount"})
            source, target = await self._movement_accounts(
                book_id, dto.from_account_id, dto.to_account_id
            )
            if source.currency_code != target.currency_code:
                raise AccountCurrencyMismatch(
                    {"from": source.currency_code, "to": target.currency_code}
                )
            await self._check_category(book_id, dto.category_id)
            tx = await self._transactions.insert(
                book_id=book_id,
                created_by_user_id=user_id,
                kind=TransactionKind.internal_transfer,
                direction=TransactionDirection.sell,
                base_currency_code=target.currency_code,
                quote_currency_code=source.currency_code,
                amount_quote=dto.amount,
                rate=Decimal(1),
                amount_base=dto.amount,
                fee=Decimal(0),
                fee_currency_code=None,
                occurred_at=dto.occurred_at or datetime.now(UTC),
                note=dto.note,
                base_account_id=target.id,
                quote_account_id=source.id,
                category_id=dto.category_id,
                idempotency_key=dto.idempotency_key,
            )
            return TransactionOut.model_validate(tx), False

    async def record_fx_conversion(
        self, book_id: int, user_id: int, dto: FxConversionCreateIn
    ) -> tuple[TransactionOut, bool]:
        """Cross-currency movement: `amount` leaves the from-account and amount*rate lands in the
        to-account. This IS a real trade, so it counts toward the weighted average."""
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.write")
            replay = await self._replay(book_id, dto.idempotency_key)
            if replay is not None:
                return replay, True
            if dto.amount <= 0 or dto.rate <= 0:
                raise InvalidAmount({"field": "amount_or_rate"})
            source, target = await self._movement_accounts(
                book_id, dto.from_account_id, dto.to_account_id
            )
            if source.currency_code == target.currency_code:
                raise InvalidTransfer({"reason": "same_currency"})
            await self._check_category(book_id, dto.category_id)
            tx = await self._transactions.insert(
                book_id=book_id,
                created_by_user_id=user_id,
                kind=TransactionKind.fx_conversion,
                direction=TransactionDirection.sell,
                base_currency_code=target.currency_code,
                quote_currency_code=source.currency_code,
                amount_quote=dto.amount,
                rate=dto.rate,
                amount_base=dto.amount * dto.rate,
                fee=Decimal(0),
                fee_currency_code=None,
                occurred_at=dto.occurred_at or datetime.now(UTC),
                note=dto.note,
                base_account_id=target.id,
                quote_account_id=source.id,
                category_id=dto.category_id,
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

    async def export_rows(
        self,
        book_id: int,
        user_id: int,
        occurred_after: datetime | None = None,
        occurred_before: datetime | None = None,
    ) -> list[TransactionExportRow]:
        """Flattened rows for the CSV export, oldest-relevant first. Read-only data, so `tx.read`
        is enough (D-M4-6) — viewers may export. Archived rows are excluded, matching the list view."""
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.read")
            rows = await self._transactions.list_for_book(
                book_id,
                occurred_after=occurred_after,
                occurred_before=occurred_before,
                archived=False,
                limit=EXPORT_LIMIT,
            )
            accounts = {
                a.id: a.name for a in await self._accounts.list_for_book(book_id, archived=None)
            }
            categories = {
                c.id: c.name
                for c in await self._categories.list_for_book(book_id, include_archived=True)
            }
            return [
                TransactionExportRow(
                    id=row.id,
                    occurred_at=row.occurred_at,
                    kind=str(row.kind),
                    direction=str(row.direction),
                    base_currency_code=row.base_currency_code,
                    quote_currency_code=row.quote_currency_code,
                    amount_quote=row.amount_quote,
                    rate=row.rate,
                    amount_base=row.amount_base,
                    fee=row.fee,
                    fee_currency_code=row.fee_currency_code,
                    base_account=accounts.get(row.base_account_id)
                    if row.base_account_id
                    else None,
                    quote_account=accounts.get(row.quote_account_id)
                    if row.quote_account_id
                    else None,
                    category=categories.get(row.category_id) if row.category_id else None,
                    note=row.note,
                )
                for row in rows
            ]

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

    async def _replay(self, book_id: int, key: str | None) -> TransactionOut | None:
        """D28: a repeated idempotency_key returns the row recorded the first time."""
        if key is None:
            return None
        existing = await self._transactions.get_by_idempotency(book_id, key)
        return None if existing is None else TransactionOut.model_validate(existing)

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

    async def _check_category(self, book_id: int, category_id: int | None) -> None:
        if category_id is None:
            return
        category = await self._categories.get(category_id)
        if category is None or category.book_id != book_id:
            raise CategoryNotFound({"category_id": category_id})

    async def _movement_accounts(
        self, book_id: int, from_account_id: int, to_account_id: int
    ) -> tuple[Account, Account]:
        if from_account_id == to_account_id:
            raise InvalidTransfer({"reason": "same_account"})
        source = await self._accounts.get(from_account_id)
        target = await self._accounts.get(to_account_id)
        for account_id, account in (
            (from_account_id, source),
            (to_account_id, target),
        ):
            if account is None or account.book_id != book_id:
                raise AccountNotInBook({"account_id": account_id, "book_id": book_id})
        assert source is not None and target is not None  # validated above
        return source, target
