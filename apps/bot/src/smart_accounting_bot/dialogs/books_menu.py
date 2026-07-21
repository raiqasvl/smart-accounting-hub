# BooksMenuDialog — /books picker: list the caller's books and switch the active one on tap.
from __future__ import annotations

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Cancel, Column, Select
from aiogram_dialog.widgets.text import Format

from smart_accounting.errors import AppError
from smart_accounting.services import BookService

from .common import btn_labels, i18n_of, resolve_actor, role_label, service
from .states import BooksMenu


async def _on_pick(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    i18n = i18n_of(manager)
    actor = await resolve_actor(manager)
    if actor is None:
        await cb.answer(i18n.get("error-no-book"), show_alert=True)
        return
    books = await service(manager, BookService)
    try:
        token = await books.switch(actor.user_id, int(item_id))
    except AppError as exc:
        await cb.answer(i18n.get("error-generic", code=exc.code), show_alert=True)
        return
    manager.dialog_data["result"] = token.book.name
    await manager.next()


async def _choose_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    actor = await resolve_actor(manager)
    books = await service(manager, BookService)
    rows = await books.list_for_user(actor.user_id) if actor else []
    return {
        "prompt": i18n.get("books-prompt"),
        "books": [
            (str(b.id), i18n.get("books-row", name=b.name, role=role_label(manager, b.role)))
            for b in rows
        ],
        **btn_labels(i18n),
    }


async def _done_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "message": i18n.get("books-switched", name=manager.dialog_data.get("result", "")),
        **btn_labels(i18n),
    }


books_menu_dialog = Dialog(
    Window(
        Format("{prompt}"),
        Column(
            Select(
                Format("{item[1]}"),
                id="books_pick",
                item_id_getter=lambda item: item[0],
                items="books",
                on_click=_on_pick,
            )
        ),
        Cancel(Format("{cancel_label}")),
        state=BooksMenu.choose,
        getter=_choose_getter,
    ),
    Window(
        Format("{message}"),
        Cancel(Format("{close_label}")),
        state=BooksMenu.done,
        getter=_done_getter,
    ),
)
