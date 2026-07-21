# JoinViaInviteDialog — one Confirm window: "Join '{book}' as {role}?" → InviteService.accept then
# switch the chat to the joined book. Started by the /start invite_<token> deep-link handler.
from __future__ import annotations

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Format

from smart_accounting.errors import AppError
from smart_accounting.services import BookService, InviteService

from .common import btn_labels, i18n_of, resolve_actor, role_label, service
from .states import JoinInvite


def _token(manager: DialogManager) -> str:
    data = manager.start_data
    return str(data.get("token", "")) if isinstance(data, dict) else ""


async def _on_accept(cb: CallbackQuery, _b: Button, manager: DialogManager) -> None:
    i18n = i18n_of(manager)
    actor = await resolve_actor(manager)
    if actor is None:
        await cb.answer(i18n.get("error-no-book"), show_alert=True)
        return
    invites = await service(manager, InviteService)
    books = await service(manager, BookService)
    try:
        joined = await invites.accept(_token(manager), actor.user_id)
        await books.switch(actor.user_id, joined.id)
    except AppError as exc:
        await cb.answer(i18n.get("error-generic", code=exc.code), show_alert=True)
        return
    manager.dialog_data["result"] = joined.name
    await manager.next()


async def _confirm_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    invites = await service(manager, InviteService)
    try:
        book_name, role = await invites.preview(_token(manager))
    except AppError as exc:
        return {
            "prompt": i18n.get("invite-unavailable", reason=exc.code),
            "can_accept": False,
            **btn_labels(i18n),
        }
    return {
        "prompt": i18n.get("invite-confirm", book=book_name, role=role_label(manager, role)),
        "can_accept": True,
        "accept_label": i18n.get("btn-accept"),
        **btn_labels(i18n),
    }


async def _done_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "message": i18n.get("invite-joined", book=manager.dialog_data.get("result", "")),
        **btn_labels(i18n),
    }


join_invite_dialog = Dialog(
    Window(
        Format("{prompt}"),
        Button(
            Format("{accept_label}"),
            id="invite_accept",
            on_click=_on_accept,
            when="can_accept",
        ),
        Cancel(Format("{cancel_label}")),
        state=JoinInvite.confirm,
        getter=_confirm_getter,
    ),
    Window(
        Format("{message}"),
        Cancel(Format("{close_label}")),
        state=JoinInvite.done,
        getter=_done_getter,
    ),
)
