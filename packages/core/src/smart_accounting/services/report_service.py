# ReportService — read-side aggregates. The headline weighted-average rate (D16).
from __future__ import annotations

from datetime import datetime

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.errors import AccountNotInBook
from smart_accounting.models.fx_transaction import TransactionDirection
from smart_accounting.repositories.accounts import AccountsRepo
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.reports import ReportsRepo
from smart_accounting.schemas import (
    AccountBalanceSeriesOut,
    BalancePointOut,
    WeightedAvgReportOut,
)
from smart_accounting.services.authz import resolve_role


class ReportService:
    def __init__(
        self,
        uow: UoW,
        reports: ReportsRepo,
        accounts: AccountsRepo,
        members: BookMembersRepo,
    ) -> None:
        self._uow = uow
        self._reports = reports
        self._accounts = accounts
        self._members = members

    async def weighted_avg(
        self,
        book_id: int,
        user_id: int,
        quote_currency_code: str,
        direction: str,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> WeightedAvgReportOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.read")
            avg, count, total = await self._reports.weighted_avg_rate(
                book_id,
                quote_currency_code,
                TransactionDirection(direction),
                period_from,
                period_to,
            )
            return WeightedAvgReportOut(
                book_id=book_id,
                quote_currency_code=quote_currency_code,
                direction=direction,
                weighted_avg_rate=avg,
                sample_count=count,
                sum_amount_quote=total,
                period_from=period_from,
                period_to=period_to,
            )

    async def account_balance_series(
        self,
        book_id: int,
        user_id: int,
        account_id: int,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> AccountBalanceSeriesOut:
        """Running balance over time. Sign rule (uniform across trades and movements): on a `sell`
        the quote account pays out and the base account receives; a `buy` is the mirror image."""
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "tx.read")
            account = await self._accounts.get(account_id)
            if account is None or account.book_id != book_id:
                raise AccountNotInBook({"account_id": account_id, "book_id": book_id})

            balance = account.opening_balance
            points: list[BalancePointOut] = []
            legs = await self._reports.legs_for_account(
                book_id, account_id, period_from, period_to
            )
            for leg in legs:
                outgoing = leg.direction == TransactionDirection.sell
                if leg.quote_account_id == account_id:
                    balance += -leg.amount_quote if outgoing else leg.amount_quote
                if leg.base_account_id == account_id:
                    balance += leg.amount_base if outgoing else -leg.amount_base
                points.append(BalancePointOut(at=leg.occurred_at, balance=balance))

            return AccountBalanceSeriesOut(
                account_id=account_id,
                currency_code=account.currency_code,
                opening_balance=account.opening_balance,
                points=points,
            )
