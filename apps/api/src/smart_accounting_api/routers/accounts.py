# Accounts surface. No future-annotations import (DishkaRoute needs concrete response types).
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import AccountCreateIn, AccountOut, AccountPatchIn
from smart_accounting.services.account_service import AccountService

from ..deps import extract_claims

router = APIRouter(tags=["accounts"], route_class=DishkaRoute)


@router.post("/books/{book_id}/accounts")
async def create_account(
    book_id: int,
    body: AccountCreateIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    account_service: FromDishka[AccountService],
) -> AccountOut:
    claims = extract_claims(request, jwt)
    return await account_service.create(book_id, claims.user_id, body)


@router.get("/books/{book_id}/accounts")
async def list_accounts(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    account_service: FromDishka[AccountService],
    archived: bool | None = None,
) -> list[AccountOut]:
    claims = extract_claims(request, jwt)
    return await account_service.list_for_book(book_id, claims.user_id, archived)


@router.patch("/accounts/{account_id}")
async def patch_account(
    account_id: int,
    body: AccountPatchIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    account_service: FromDishka[AccountService],
) -> AccountOut:
    claims = extract_claims(request, jwt)
    return await account_service.patch(account_id, claims.user_id, body)


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    account_service: FromDishka[AccountService],
) -> dict[str, int]:
    claims = extract_claims(request, jwt)
    await account_service.delete(account_id, claims.user_id)
    return {"deleted": account_id}
