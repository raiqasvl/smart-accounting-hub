# FxService — read-side rate hints from exchange_rates (D16: informational only).
from __future__ import annotations

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.exchange_rates import ExchangeRatesRepo
from smart_accounting.schemas import FxRateOut
from smart_accounting.services.authz import resolve_role


class FxService:
    def __init__(self, uow: UoW, rates: ExchangeRatesRepo, members: BookMembersRepo) -> None:
        self._uow = uow
        self._rates = rates
        self._members = members

    async def latest_rate(self, book_id: int, user_id: int, base: str, quote: str) -> FxRateOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.read")
            rate = await self._rates.latest_cross(base, quote)
            return FxRateOut(base=base, quote=quote, rate=rate)
