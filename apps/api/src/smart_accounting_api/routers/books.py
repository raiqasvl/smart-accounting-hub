# Books surface. No future-annotations import (DishkaRoute needs concrete response types).
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import BookCreateIn, BookOut, BookPatchIn, TokenOut
from smart_accounting.services.book_service import BookService

from ..deps import extract_claims

router = APIRouter(tags=["books"], route_class=DishkaRoute)


@router.post("/books")
async def create_book(
    body: BookCreateIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    book_service: FromDishka[BookService],
) -> BookOut:
    claims = extract_claims(request, jwt)
    return await book_service.create(claims.user_id, body)


@router.get("/books")
async def list_books(
    request: Request,
    jwt: FromDishka[JwtCodec],
    book_service: FromDishka[BookService],
) -> list[BookOut]:
    claims = extract_claims(request, jwt)
    return await book_service.list_for_user(claims.user_id)


@router.get("/books/{book_id}")
async def get_book(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    book_service: FromDishka[BookService],
) -> BookOut:
    claims = extract_claims(request, jwt)
    return await book_service.get(book_id, claims.user_id)


@router.patch("/books/{book_id}")
async def patch_book(
    book_id: int,
    body: BookPatchIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    book_service: FromDishka[BookService],
) -> BookOut:
    claims = extract_claims(request, jwt)
    return await book_service.update(book_id, claims.user_id, body)


@router.post("/books/{book_id}/switch")
async def switch_book(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    book_service: FromDishka[BookService],
) -> TokenOut:
    claims = extract_claims(request, jwt)
    return await book_service.switch(claims.user_id, book_id)
