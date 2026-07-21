# TgChatService — the bot's arm for the bot-owned tg_chats table. Exists so the bot binds a
# chat to a user+book via a *service* and never imports repositories directly (D22).
from __future__ import annotations

from smart_accounting.common.uow import UoW
from smart_accounting.repositories.tg_chats import TgChatsRepo


class TgChatService:
    def __init__(self, uow: UoW, tg_chats: TgChatsRepo) -> None:
        self._uow = uow
        self._tg_chats = tg_chats

    async def bind(
        self,
        *,
        chat_id: int,
        user_id: int,
        active_book_id: int,
        last_message_id: int | None = None,
    ) -> None:
        async with self._uow:
            await self._tg_chats.upsert(
                chat_id=chat_id, user_id=user_id, active_book_id=active_book_id
            )
            if last_message_id is not None:
                await self._tg_chats.set_last_message_id(chat_id, last_message_id)

    async def set_last_message(self, chat_id: int, message_id: int) -> None:
        async with self._uow:
            await self._tg_chats.set_last_message_id(chat_id, message_id)

    async def context(self, chat_id: int) -> tuple[int, int | None] | None:
        """This chat's (domain user_id, active_book_id) — the bot's way to resolve who/where a
        command applies to without touching repositories. None if the chat was never onboarded."""
        async with self._uow:
            chat = await self._tg_chats.get(chat_id)
            if chat is None:
                return None
            return chat.user_id, chat.active_book_id
