# Top-level command handlers.
#   /start                     onboard + WebApp button (M1)
#   /start invite_<token>      onboard + open the join-via-invite dialog (M2)
#   /books /newbook /newaccount open the corresponding aiogram-dialog flow (M2)
#
# D22: this module imports only smart_accounting.services (+ config); never models/repositories.
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram_dialog import DialogManager, StartMode
from aiogram_i18n import I18nContext
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from smart_accounting.config import get_config
from smart_accounting.schemas import BookOut, UserOut
from smart_accounting.services import TgChatService, TgIdentity, UserService

from ..dialogs.states import BooksMenu, CreateAccount, CreateBook, JoinInvite

router = Router(name="commands")

_INVITE_PREFIX = "invite_"


async def ensure_onboarded(
    msg: Message, user_service: UserService, tg_chats: TgChatService
) -> tuple[UserOut, BookOut] | None:
    """Idempotently create the user + default book and bind this chat to them. Returns the DTOs,
    or None if the update carried no sender (e.g. a channel post)."""
    tg_user = msg.from_user
    if tg_user is None:
        return None
    ident = TgIdentity(
        telegram_user_id=tg_user.id,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        username=tg_user.username,
        language_code=tg_user.language_code,
    )
    user, book = await user_service.ensure_user_and_default_book(ident)
    await tg_chats.bind(chat_id=msg.chat.id, user_id=user.id, active_book_id=book.id)
    return user, book


async def handle_start(
    msg: Message,
    i18n: I18nContext,
    user_service: UserService,
    tg_chats: TgChatService,
    domain: str,
) -> None:
    """Plain /start: onboard, then send the WebApp button. Split out for unit testing."""
    onboarded = await ensure_onboarded(msg, user_service, tg_chats)
    if onboarded is None:
        return
    user, _book = onboarded
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


@router.message(CommandStart(deep_link=True))
@inject
async def start_deep_link(
    msg: Message,
    command: CommandObject,
    i18n: I18nContext,
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    tg_chats: FromDishka[TgChatService],
) -> None:
    payload = command.args or ""
    if payload.startswith(_INVITE_PREFIX):
        # Onboard first so the joiner exists + has a chat row, then open the confirm dialog.
        if await ensure_onboarded(msg, user_service, tg_chats) is None:
            return
        token = payload[len(_INVITE_PREFIX) :]
        await dialog_manager.start(
            JoinInvite.confirm, data={"token": token}, mode=StartMode.RESET_STACK
        )
        return
    await handle_start(msg, i18n, user_service, tg_chats, get_config().DOMAIN)


@router.message(CommandStart(deep_link=False))
@inject
async def start(
    msg: Message,
    i18n: I18nContext,
    user_service: FromDishka[UserService],
    tg_chats: FromDishka[TgChatService],
) -> None:
    await handle_start(msg, i18n, user_service, tg_chats, get_config().DOMAIN)


@router.message(Command("books"))
@inject
async def books(
    msg: Message,
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    tg_chats: FromDishka[TgChatService],
) -> None:
    if await ensure_onboarded(msg, user_service, tg_chats) is None:
        return
    await dialog_manager.start(BooksMenu.choose, mode=StartMode.RESET_STACK)


@router.message(Command("newbook"))
@inject
async def new_book(
    msg: Message,
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    tg_chats: FromDishka[TgChatService],
) -> None:
    if await ensure_onboarded(msg, user_service, tg_chats) is None:
        return
    await dialog_manager.start(CreateBook.name, mode=StartMode.RESET_STACK)


@router.message(Command("newaccount"))
@inject
async def new_account(
    msg: Message,
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    tg_chats: FromDishka[TgChatService],
) -> None:
    if await ensure_onboarded(msg, user_service, tg_chats) is None:
        return
    await dialog_manager.start(CreateAccount.currency, mode=StartMode.RESET_STACK)
