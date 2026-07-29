# Categories surface. No future-annotations import (DishkaRoute needs concrete response types).
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import (
    CategoryCreateIn,
    CategoryMoveIn,
    CategoryOut,
    CategoryPatchIn,
)
from smart_accounting.services.category_service import CategoryService

from ..deps import extract_claims

router = APIRouter(tags=["categories"], route_class=DishkaRoute)


@router.post("/books/{book_id}/categories", status_code=201)
async def create_category(
    book_id: int,
    body: CategoryCreateIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    category_service: FromDishka[CategoryService],
) -> CategoryOut:
    claims = extract_claims(request, jwt)
    return await category_service.create(book_id, claims.user_id, body)


@router.get("/books/{book_id}/categories")
async def list_categories(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    category_service: FromDishka[CategoryService],
    include_archived: bool = False,
) -> list[CategoryOut]:
    claims = extract_claims(request, jwt)
    return await category_service.list_for_book(book_id, claims.user_id, include_archived)


@router.patch("/categories/{category_id}")
async def patch_category(
    category_id: int,
    body: CategoryPatchIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    category_service: FromDishka[CategoryService],
) -> CategoryOut:
    claims = extract_claims(request, jwt)
    return await category_service.patch(category_id, claims.user_id, body)


@router.post("/categories/{category_id}/move")
async def move_category(
    category_id: int,
    body: CategoryMoveIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    category_service: FromDishka[CategoryService],
) -> CategoryOut:
    claims = extract_claims(request, jwt)
    return await category_service.move(category_id, claims.user_id, body)


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    category_service: FromDishka[CategoryService],
) -> dict[str, int]:
    claims = extract_claims(request, jwt)
    await category_service.delete(category_id, claims.user_id)
    return {"deleted": category_id}
