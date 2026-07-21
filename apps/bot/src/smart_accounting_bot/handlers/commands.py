# Top-level command handlers. M1: bare /start (onboard + WebApp button). Deep-link invites,
# /books, /lang, /avg, /trade land in M2-M3.
#
# D22: this module imports only smart_accounting.services (+ config); never models/repositories.
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram_i18n import I18nContext
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from smart_accounting.config import get_config
from smart_accounting.services import TgChatService, TgIdentity, UserService

router = Router(name="commands")


async def handle_start(
    msg: Message,
    i18n: I18nContext,
    user_service: UserService,
    tg_chats: TgChatService,
    domain: str,
) -> None:
    """Onboard the sender (idempotent), bind the chat to their book, and send the WebApp button.

    Split out from the injected handler so it can be unit-tested with plain mocks."""
    tg_user = msg.from_user
    if tg_user is None:
        return
    ident = TgIdentity(
        telegram_user_id=tg_user.id,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        username=tg_user.username,
        language_code=tg_user.language_code,
    )
    user, book = await user_service.ensure_user_and_default_book(ident)
    await tg_chats.bind(chat_id=msg.chat.id, user_id=user.id, active_book_id=book.id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("open-app-button"),
                    web_app=WebAppInfo(url=f"https://{domain}"),
                )
            ]
        ]
    )
    sent = await msg.answer(
        i18n.get("start-welcome", name=user.first_name or user.username or "there"),
        reply_markup=keyboard,
    )
    await tg_chats.set_last_message(msg.chat.id, sent.message_id)


@router.message(CommandStart(deep_link=False))
@inject
async def start(
    msg: Message,
    i18n: I18nContext,
    user_service: FromDishka[UserService],
    tg_chats: FromDishka[TgChatService],
) -> None:
    await handle_start(msg, i18n, user_service, tg_chats, get_config().DOMAIN)
