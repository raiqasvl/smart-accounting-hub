# ReportService — read-side aggregates. The headline weighted-average rate (D16).
from __future__ import annotations

from datetime import datetime

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.models.fx_transaction import TransactionDirection
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.reports import ReportsRepo
from smart_accounting.schemas import WeightedAvgReportOut
from smart_accounting.services.authz import resolve_role


class ReportService:
    def __init__(self, uow: UoW, reports: ReportsRepo, members: BookMembersRepo) -> None:
        self._uow = uow
        self._reports = reports
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
