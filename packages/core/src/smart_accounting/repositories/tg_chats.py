# tg_chats repository — queries only, no transaction management. Bot-owned table (D15).
from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from smart_accounting.common.uow import UoW
from smart_accounting.models import TgChat


class TgChatsRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def get(self, chat_id: int) -> TgChat | None:
        return await self._session.get(TgChat, chat_id)

    async def upsert(self, *, chat_id: int, user_id: int, active_book_id: int | None) -> None:
        stmt = pg_insert(TgChat).values(
            chat_id=chat_id, user_id=user_id, active_book_id=active_book_id
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[TgChat.chat_id],
            set_={"user_id": user_id, "active_book_id": active_book_id},
        )
        await self._session.execute(stmt)

    async def set_active_book(self, chat_id: int, active_book_id: int | None) -> None:
        await self._session.execute(
            update(TgChat).where(TgChat.chat_id == chat_id).values(active_book_id=active_book_id)
        )

    async def set_last_message_id(self, chat_id: int, message_id: int) -> None:
        await self._session.execute(
            update(TgChat).where(TgChat.chat_id == chat_id).values(last_message_id=message_id)
        )
