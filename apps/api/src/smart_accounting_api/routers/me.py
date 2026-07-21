# GET /me — the authenticated identity endpoint (M1 end-to-end demo target).
# No future-annotations import: FastAPI/DishkaRoute must see the concrete response type.
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.schemas import MeOut
from smart_accounting.services.user_service import UserService

from ..deps import extract_claims

router = APIRouter(tags=["me"], route_class=DishkaRoute)


@router.get("/me")
async def get_me(
    request: Request,
    jwt: FromDishka[JwtCodec],
    user_service: FromDishka[UserService],
) -> MeOut:
    claims = extract_claims(request, jwt)  # raises -> 401
    assert claims.book_id is not None  # guaranteed by extract_claims
    return await user_service.load_me(user_id=claims.user_id, book_id=claims.book_id)
