# CurrencyService — the system catalogue + per-book currency overrides.
from __future__ import annotations

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.errors import CurrencyExists
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.currencies import CurrenciesRepo
from smart_accounting.schemas import CurrencyCreateIn, CurrencyOut
from smart_accounting.services.authz import resolve_role


class CurrencyService:
    def __init__(self, uow: UoW, currencies: CurrenciesRepo, members: BookMembersRepo) -> None:
        self._uow = uow
        self._currencies = currencies
        self._members = members

    async def list_for_book(self, book_id: int, user_id: int) -> list[CurrencyOut]:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "book.read")
            rows = await self._currencies.list_visible(book_id)
            return [CurrencyOut.model_validate(row) for row in rows]

    async def add_override(self, book_id: int, user_id: int, dto: CurrencyCreateIn) -> CurrencyOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "account.write")
            if await self._currencies.get_book_override(book_id, dto.code) is not None:
                raise CurrencyExists({"code": dto.code})
            currency = await self._currencies.insert(
                book_id=book_id,
                code=dto.code,
                symbol=dto.symbol,
                decimals=dto.decimals,
                kind=dto.kind,
            )
            return CurrencyOut.model_validate(currency)
