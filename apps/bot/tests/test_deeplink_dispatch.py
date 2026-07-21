# End-to-end `/start invite_<token>` through the real dispatcher (routing + Dishka + i18n +
# aiogram-dialog), against a savepoint-isolated DB with the bot network mocked. Proves the deep
# link onboards the joiner and opens the join-confirm dialog, whose getter previews the invite.
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update
from aiogram.types import User as TgUser
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.aiogram import setup_dishka
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from smart_accounting.auth.rbac import Role
from smart_accounting.common.uow import UoW
from smart_accounting.config import get_config
from smart_accounting.ioc import DepsProvider
from smart_accounting.models import Book, BookInvite, BookMember, User
from smart_accounting_bot.main import setup_dispatcher

DUMMY_TOKEN = "123456:AAHdummydeeplinktokenABCDEFGHIJKLMNOPQRS"
JOINER_CHAT = 700200200
JOINER_UID = 700200201
INVITE_TOKEN = "e2e-deeplink-token"
BOOK_NAME = "SharedBook"


@pytest_asyncio.fixture
async def dispatch_env() -> AsyncIterator[tuple]:
    os.environ["DOMAIN"] = "app.example.com"
    get_config.cache_clear()
    base = get_config()

    engine = create_async_engine(base.POSTGRES_DSN)
    conn = await engine.connect()
    trans = await conn.begin()

    # Seed an inviter, their book, and a valid single-use invite.
    seed = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
    inviter = User(telegram_user_id=700200100, first_name="Owner", language="en", timezone="UTC")
    seed.add(inviter)
    await seed.flush()
    book = Book(owner_id=inviter.id, name=BOOK_NAME, kind=0, base_currency_code="USD")
    seed.add(book)
    await seed.flush()
    seed.add(BookMember(book_id=book.id, user_id=inviter.id, role=int(Role.OWNER)))
    seed.add(
        BookInvite(
            book_id=book.id,
            invited_by=inviter.id,
            token=INVITE_TOKEN,
            role=int(Role.EDITOR),
            expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        )
    )
    await seed.commit()
    await seed.close()

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
    dp = Dispatcher(storage=MemoryStorage())
    setup_dispatcher(dp)
    setup_dishka(container=container, router=dp)

    bot = Bot(token=DUMMY_TOKEN, default=DefaultBotProperties())
    sent: list[object] = []
    reply = Message(
        message_id=999, date=datetime.now(UTC), chat=Chat(id=JOINER_CHAT, type="private")
    )

    async def _fake_call(_bot: Bot, method: object, **_kwargs: object) -> Message:
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


async def test_invite_deeplink_onboards_and_opens_join_dialog(dispatch_env: tuple) -> None:
    dp, bot, conn, sent = dispatch_env
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(UTC),
            chat=Chat(id=JOINER_CHAT, type="private"),
            from_user=TgUser(id=JOINER_UID, is_bot=False, first_name="Joiner", language_code="en"),
            text=f"/start {'invite_'}{INVITE_TOKEN}",
        ),
    )
    await dp.feed_update(bot, update)

    # The join-confirm window rendered, previewing the invited book by name.
    texts = [getattr(m, "text", "") or "" for m in sent]
    assert any(BOOK_NAME in t for t in texts), texts

    # The joiner was onboarded (deep link onboards before opening the dialog).
    q = AsyncSession(bind=conn, expire_on_commit=False)
    joiner = (
        await q.execute(select(User).where(User.telegram_user_id == JOINER_UID))
    ).scalar_one_or_none()
    assert joiner is not None
    await q.close()
