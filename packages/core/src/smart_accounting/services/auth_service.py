# AuthService — the API-only arm: verify initData, onboard via UserService, mint a JWT.
from __future__ import annotations

from smart_accounting.auth.initdata import verify_init_data
from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.config import Settings
from smart_accounting.schemas import TokenOut
from smart_accounting.services.identity import TgIdentity
from smart_accounting.services.user_service import UserService


class AuthService:
    def __init__(self, user_service: UserService, jwt: JwtCodec, settings: Settings) -> None:
        self._user_service = user_service
        self._jwt = jwt
        self._settings = settings

    async def authenticate(self, init_data: str) -> TokenOut:
        parsed = verify_init_data(init_data, self._settings.BOT_TOKEN)  # raises -> 403
        ident = TgIdentity.from_init_data(parsed)
        user, book = await self._user_service.ensure_user_and_default_book(ident)
        token = self._jwt.issue(user_id=user.id, book_id=book.id, role=book.role)
        return TokenOut(
            access_token=token,
            expires_in=self._settings.JWT_LIFETIME_SECONDS,
            user=user,
            book=book,
        )
