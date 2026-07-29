# Reports surface. No future-annotations import (DishkaRoute needs concrete response types).
from datetime import datetime
from typing import Literal

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import AccountBalanceSeriesOut, WeightedAvgReportOut
from smart_accounting.services.report_service import ReportService

from ..deps import extract_claims

router = APIRouter(tags=["reports"], route_class=DishkaRoute)


@router.get("/books/{book_id}/reports/weighted-avg-rate")
async def weighted_avg_rate(
    book_id: int,
    quote: str,
    direction: Literal["buy", "sell"],
    request: Request,
    jwt: FromDishka[JwtCodec],
    report_service: FromDishka[ReportService],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> WeightedAvgReportOut:
    claims = extract_claims(request, jwt)
    return await report_service.weighted_avg(
        book_id, claims.user_id, quote, direction, date_from, date_to
    )


@router.get("/books/{book_id}/reports/account-balance")
async def account_balance(
    book_id: int,
    account_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    report_service: FromDishka[ReportService],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> AccountBalanceSeriesOut:
    claims = extract_claims(request, jwt)
    return await report_service.account_balance_series(
        book_id, claims.user_id, account_id, date_from, date_to
    )
