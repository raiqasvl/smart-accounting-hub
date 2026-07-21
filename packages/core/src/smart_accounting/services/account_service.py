# AccountService — per-book accounts (where money sits). One transaction per method (UoW).
# The bare /accounts/{id} routes carry no book_id, so patch/delete load the account first, then
# resolve the caller's role for *that* account's book_id before checking the permission.
from __future__ import annotations

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.errors import AccountInUse, CurrencyUnknown, NotFound
from smart_accounting.repositories.accounts import AccountsRepo
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.currencies import CurrenciesRepo
from smart_accounting.schemas import AccountCreateIn, AccountOut, AccountPatchIn
from smart_accounting.services.authz import resolve_role


class AccountService:
    def __init__(
        self,
        uow: UoW,
        accounts: AccountsRepo,
        currencies: CurrenciesRepo,
        members: BookMembersRepo,
    ) -> None:
        self._uow = uow
        self._accounts = accounts
        self._currencies = currencies
        self._members = members

    async def create(self, book_id: int, user_id: int, dto: AccountCreateIn) -> AccountOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "account.write")
            if not await self._currencies.code_visible(book_id, dto.currency_code):
                raise CurrencyUnknown({"code": dto.currency_code})
            account = await self._accounts.insert(
                book_id=book_id,
                currency_code=dto.currency_code,
                name=dto.name,
                kind=dto.kind,
                opening_balance=dto.opening_balance,
            )
            return AccountOut.model_validate(account)

    async def list_for_book(
        self, book_id: int, user_id: int, archived: bool | None = None
    ) -> list[AccountOut]:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "book.read")
            rows = await self._accounts.list_for_book(book_id, archived)
            return [AccountOut.model_validate(row) for row in rows]

    async def patch(self, account_id: int, user_id: int, dto: AccountPatchIn) -> AccountOut:
        async with self._uow:
            account = await self._accounts.get(account_id)
            if account is None:
                raise NotFound({"account_id": account_id})
            role = await resolve_role(self._members, account.book_id, user_id)
            require_permission(role, "account.write")
            updated = await self._accounts.update(account_id, name=dto.name, archived=dto.archived)
            assert updated is not None  # loaded above, same transaction
            return AccountOut.model_validate(updated)

    async def delete(self, account_id: int, user_id: int) -> None:
        async with self._uow:
            account = await self._accounts.get(account_id)
            if account is None:
                raise NotFound({"account_id": account_id})
            role = await resolve_role(self._members, account.book_id, user_id)
            require_permission(role, "book.delete")  # owner-only hard delete
            if await self._accounts.has_transactions(account_id):
                raise AccountInUse({"account_id": account_id})
            await self._accounts.delete(account_id)
