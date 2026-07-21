# Mini-App auth surface (D12). POST /auth/telegram: verify initData -> onboard -> mint JWT.
# No future-annotations import: FastAPI/DishkaRoute must see the concrete response type.
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_accounting.schemas import AuthTelegramIn, TokenOut
from smart_accounting.services.auth_service import AuthService

router = APIRouter(tags=["auth"], route_class=DishkaRoute)


@router.post("/auth/telegram")
async def auth_telegram(body: AuthTelegramIn, auth_service: FromDishka[AuthService]) -> TokenOut:
    return await auth_service.authenticate(body.init_data)
