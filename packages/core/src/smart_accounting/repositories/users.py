# users repository — queries only, no transaction management.
from __future__ import annotations

from sqlalchemy import select

from smart_accounting.common.uow import UoW
from smart_accounting.models import User


class UsersRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def get(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def insert(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language: str,
        timezone: str = "UTC",
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
            timezone=timezone,
        )
        self._session.add(user)
        await self._session.flush()
        return user
