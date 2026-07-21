# Currencies surface. No future-annotations import (DishkaRoute needs concrete response types).
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import CurrencyCreateIn, CurrencyOut
from smart_accounting.services.currency_service import CurrencyService

from ..deps import extract_claims

router = APIRouter(tags=["currencies"], route_class=DishkaRoute)


@router.get("/currencies")
async def list_currencies(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    currency_service: FromDishka[CurrencyService],
) -> list[CurrencyOut]:
    claims = extract_claims(request, jwt)
    return await currency_service.list_for_book(book_id, claims.user_id)


@router.post("/books/{book_id}/currencies")
async def add_currency(
    book_id: int,
    body: CurrencyCreateIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    currency_service: FromDishka[CurrencyService],
) -> CurrencyOut:
    claims = extract_claims(request, jwt)
    return await currency_service.add_override(book_id, claims.user_id, body)
