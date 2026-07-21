# Invites surface. No future-annotations import (DishkaRoute needs concrete response types).
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import BookOut, InviteCreateIn, InviteOut
from smart_accounting.services.invite_service import InviteService

from ..deps import extract_claims

router = APIRouter(tags=["invites"], route_class=DishkaRoute)


@router.post("/books/{book_id}/invites")
async def create_invite(
    book_id: int,
    body: InviteCreateIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    invite_service: FromDishka[InviteService],
) -> InviteOut:
    claims = extract_claims(request, jwt)
    return await invite_service.create(book_id, claims.user_id, body)


@router.get("/books/{book_id}/invites")
async def list_invites(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    invite_service: FromDishka[InviteService],
) -> list[InviteOut]:
    claims = extract_claims(request, jwt)
    return await invite_service.list_pending(book_id, claims.user_id)


@router.delete("/books/{book_id}/invites/{invite_id}")
async def revoke_invite(
    book_id: int,
    invite_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    invite_service: FromDishka[InviteService],
) -> dict[str, int]:
    claims = extract_claims(request, jwt)
    await invite_service.revoke(book_id, invite_id, claims.user_id)
    return {"revoked": invite_id}


@router.post("/invites/{token}/accept")
async def accept_invite(
    token: str,
    request: Request,
    jwt: FromDishka[JwtCodec],
    invite_service: FromDishka[InviteService],
) -> BookOut:
    claims = extract_claims(request, jwt)
    return await invite_service.accept(token, claims.user_id)
