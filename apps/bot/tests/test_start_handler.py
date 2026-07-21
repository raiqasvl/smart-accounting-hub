# Unit test for the /start handler logic (plain mocks, no Bot session / no DB).
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from smart_accounting.schemas import BookOut, UserOut
from smart_accounting_bot.handlers.commands import handle_start


async def test_start_onboards_binds_chat_and_sends_webapp_button() -> None:
    user_service = AsyncMock()
    user_service.ensure_user_and_default_book.return_value = (
        UserOut(id=7, telegram_user_id=123, first_name="Ada", language="en", timezone="UTC"),
        BookOut(id=3, name="Personal", kind=0, base_currency_code="USD", role=0),
    )
    tg_chats = AsyncMock()

    i18n = MagicMock()
    i18n.get.side_effect = lambda key, **kw: f"{key}"

    msg = MagicMock()
    msg.from_user = MagicMock(
        id=123, first_name="Ada", last_name=None, username="ada", language_code="en"
    )
    msg.chat = MagicMock(id=555)
    msg.answer = AsyncMock(return_value=MagicMock(message_id=999))

    await handle_start(msg, i18n, user_service, tg_chats, domain="app.example.com")

    user_service.ensure_user_and_default_book.assert_awaited_once()
    tg_chats.bind.assert_awaited_once()
    bind_kwargs = tg_chats.bind.call_args.kwargs
    assert bind_kwargs == {"chat_id": 555, "user_id": 7, "active_book_id": 3}

    msg.answer.assert_awaited_once()
    keyboard = msg.answer.call_args.kwargs["reply_markup"]
    button = keyboard.inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url == "https://app.example.com"

    tg_chats.set_last_message.assert_awaited_once_with(555, 999)


async def test_start_ignores_message_without_user() -> None:
    user_service = AsyncMock()
    msg = MagicMock()
    msg.from_user = None
    await handle_start(msg, MagicMock(), user_service, AsyncMock(), domain="x")
    user_service.ensure_user_and_default_book.assert_not_awaited()
