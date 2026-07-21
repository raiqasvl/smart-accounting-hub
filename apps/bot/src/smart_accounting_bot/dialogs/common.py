# Shared dialog helpers. Dialogs pull services from the per-update Dishka container that the
# aiogram integration stashes in middleware_data (key "dishka_container"), and resolve the acting
# (user_id, book_id) via TgChatService — never touching repositories directly (D22).
from __future__ import annotations

from dataclasses import dataclass

from aiogram_dialog import DialogManager
from aiogram_i18n import I18nContext
from dishka import AsyncContainer

from smart_accounting.auth.rbac import Role
from smart_accounting.services import TgChatService


@dataclass(frozen=True)
class Actor:
    """The acting user + their currently-active book, resolved from the chat."""

    user_id: int
    book_id: int


# Enumerations shared by dialogs and their Fluent label keys.
BOOK_KINDS: list[tuple[int, str]] = [
    (0, "book-kind-personal"),
    (1, "book-kind-family"),
    (2, "book-kind-business"),
]
ACCOUNT_KINDS: list[tuple[int, str]] = [
    (0, "account-kind-cash"),
    (1, "account-kind-bank"),
    (2, "account-kind-card"),
    (3, "account-kind-brokerage"),
    (4, "account-kind-other"),
]
_ROLE_KEYS: dict[int, str] = {
    int(Role.OWNER): "role-owner",
    int(Role.ADMIN): "role-admin",
    int(Role.EDITOR): "role-editor",
    int(Role.VIEWER): "role-viewer",
}


async def service[T](manager: DialogManager, cls: type[T]) -> T:
    container: AsyncContainer = manager.middleware_data["dishka_container"]
    resolved: T = await container.get(cls)
    return resolved


def i18n_of(manager: DialogManager) -> I18nContext:
    i18n: I18nContext = manager.middleware_data["i18n"]
    return i18n


def chat_id_of(manager: DialogManager) -> int:
    chat = manager.middleware_data["event_chat"]
    return int(chat.id)


async def resolve_actor(manager: DialogManager) -> Actor | None:
    """The acting user + active book for this chat, or None if the book slot is empty."""
    tg_chats = await service(manager, TgChatService)
    ctx = await tg_chats.context(chat_id_of(manager))
    if ctx is None or ctx[1] is None:
        return None
    return Actor(user_id=ctx[0], book_id=ctx[1])


def role_label(manager: DialogManager, role: int) -> str:
    return i18n_of(manager).get(_ROLE_KEYS.get(role, "role-viewer"))


def btn_labels(i18n: I18nContext) -> dict[str, str]:
    """Localized labels for the shared confirm/back/cancel/close buttons, spread into getters."""
    return {
        "confirm_label": i18n.get("btn-confirm"),
        "back_label": i18n.get("btn-back"),
        "cancel_label": i18n.get("btn-cancel"),
        "close_label": i18n.get("btn-close"),
    }
