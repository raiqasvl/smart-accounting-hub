# FX rate-hint surface. No future-annotations import (DishkaRoute needs concrete response types).
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import FxRateOut
from smart_accounting.services.fx_service import FxService

from ..deps import extract_claims

router = APIRouter(tags=["fx"], route_class=DishkaRoute)


@router.get("/books/{book_id}/fx/latest")
async def fx_latest(
    book_id: int,
    base: str,
    quote: str,
    request: Request,
    jwt: FromDishka[JwtCodec],
    fx_service: FromDishka[FxService],
) -> FxRateOut:
    claims = extract_claims(request, jwt)
    return await fx_service.latest_rate(book_id, claims.user_id, base, quote)
