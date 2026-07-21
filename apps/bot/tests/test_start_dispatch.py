# End-to-end /start through the real dispatcher (routing + Dishka + i18n middleware) against a
# real, savepoint-isolated DB, with the bot's network mocked. This is the automated stand-in for
# the manual "send /start" gate: it proves the whole chain minus the Telegram transport.
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest_asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, Update
from aiogram.types import User as TgUser
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.aiogram import setup_dishka
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from smart_accounting.common.uow import UoW
from smart_accounting.config import get_config
from smart_accounting.ioc import DepsProvider
from smart_accounting.models import Book, TgChat, User
from smart_accounting_bot.main import build_dispatcher, setup_dispatcher

DUMMY_TOKEN = "123456:AAHdummyfeedupdatetokenABCDEFGHIJKLMNOPQRS"
CHAT_ID = 700100100
UID = 700100101


@pytest_asyncio.fixture
async def dispatch_env() -> AsyncIterator[tuple]:
    os.environ["DOMAIN"] = "app.example.com"
    get_config.cache_clear()
    base = get_config()

    engine = create_async_engine(base.POSTGRES_DSN)
    conn = await engine.connect()
    trans = await conn.begin()

    class _TestProvider(Provider):
        @provide(scope=Scope.REQUEST, override=True)
        async def uow(self) -> AsyncIterator[UoW]:
            session = AsyncSession(
                bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            try:
                yield UoW(session)
            finally:
                await session.close()

    container = make_async_container(DepsProvider(), _TestProvider())
    dp = build_dispatcher()
    setup_dispatcher(dp)
    setup_dishka(container=container, router=dp)

    bot = Bot(token=DUMMY_TOKEN, default=DefaultBotProperties())
    sent: list[SendMessage] = []
    reply = Message(message_id=999, date=datetime.now(UTC), chat=Chat(id=CHAT_ID, type="private"))

    async def _fake_call(_bot: Bot, method: object, **_kwargs: object) -> Message:
        # aiogram calls session(bot, method, timeout=...); we only care about the method.
        if isinstance(method, SendMessage):
            sent.append(method)
        return reply

    bot.session = AsyncMock(side_effect=_fake_call)  # type: ignore[method-assign]

    await dp.emit_startup(bot=bot, dispatcher=dp)
    try:
        yield dp, bot, conn, sent
    finally:
        await dp.emit_shutdown(bot=bot, dispatcher=dp)
        await container.close()
        if trans.is_active:
            await trans.rollback()
        await conn.close()
        await engine.dispose()
        get_config.cache_clear()


async def test_start_end_to_end_ru(dispatch_env: tuple) -> None:
    dp, bot, conn, sent = dispatch_env
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(UTC),
            chat=Chat(id=CHAT_ID, type="private"),
            from_user=TgUser(id=UID, is_bot=False, first_name="Grace", language_code="ru"),
            text="/start",
        ),
    )
    await dp.feed_update(bot, update)

    # A single message with a WebApp button, localized to Russian.
    assert len(sent) == 1
    method = sent[0]
    assert method.reply_markup is not None
    button = method.reply_markup.inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url == "https://app.example.com"
    assert "Welcome" not in (method.text or "")  # ru locale, not en

    # Rows were created (query on the same savepoint connection).
    q = AsyncSession(bind=conn, expire_on_commit=False)
    user = (await q.execute(select(User).where(User.telegram_user_id == UID))).scalar_one()
    assert user.language == "ru"
    book = (await q.execute(select(Book).where(Book.owner_id == user.id))).scalar_one()
    assert book.base_currency_code == "RUB"
    assert book.name == "Личный"
    tg_chat = await q.get(TgChat, CHAT_ID)
    assert tg_chat is not None
    assert tg_chat.active_book_id == book.id
    await q.close()
