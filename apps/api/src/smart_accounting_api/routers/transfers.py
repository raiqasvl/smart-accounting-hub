# Account-to-account movements. Each is ONE fx_transactions row touching both accounts
# (quote_account_id = money out, base_account_id = money in). No future-annotations import.
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request, Response

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import FxConversionCreateIn, TransactionOut, TransferCreateIn
from smart_accounting.services.transaction_service import TransactionService

from ..deps import extract_claims

router = APIRouter(tags=["transfers"], route_class=DishkaRoute)


@router.post("/books/{book_id}/transfers", status_code=201)
async def create_transfer(
    book_id: int,
    body: TransferCreateIn,
    request: Request,
    response: Response,
    jwt: FromDishka[JwtCodec],
    transaction_service: FromDishka[TransactionService],
) -> TransactionOut:
    claims = extract_claims(request, jwt)
    tx, replayed = await transaction_service.record_transfer(book_id, claims.user_id, body)
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replayed"] = "true"
    return tx


@router.post("/books/{book_id}/fx-conversions", status_code=201)
async def create_fx_conversion(
    book_id: int,
    body: FxConversionCreateIn,
    request: Request,
    response: Response,
    jwt: FromDishka[JwtCodec],
    transaction_service: FromDishka[TransactionService],
) -> TransactionOut:
    claims = extract_claims(request, jwt)
    tx, replayed = await transaction_service.record_fx_conversion(book_id, claims.user_id, body)
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replayed"] = "true"
    return tx
