# CreateBookDialog — Name → Kind → BaseCurrency → Confirm → Done. Calls BookService.create then
# switches the chat's active book to the new one. All text localized via per-window getters.
from __future__ import annotations

from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, Column, Select
from aiogram_dialog.widgets.text import Format

from smart_accounting.errors import AppError
from smart_accounting.schemas import BookCreateIn
from smart_accounting.services import BookService

from .common import BOOK_KINDS, btn_labels, i18n_of, resolve_actor, service
from .states import CreateBook


async def _on_name(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["name"] = text.strip()
    await manager.next()


async def _on_kind(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["kind"] = int(item_id)
    await manager.next()


async def _on_currency(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["currency"] = text.strip().upper()
    await manager.next()


async def _on_confirm(cb: CallbackQuery, _b: Button, manager: DialogManager) -> None:
    i18n = i18n_of(manager)
    actor = await resolve_actor(manager)
    if actor is None:
        await cb.answer(i18n.get("error-no-book"), show_alert=True)
        return
    data = manager.dialog_data
    books = await service(manager, BookService)
    try:
        created = await books.create(
            actor.user_id,
            BookCreateIn(
                name=str(data["name"]),
                kind=int(data["kind"]),
                base_currency_code=str(data["currency"]),
                default_language=i18n.locale,
            ),
        )
        await books.switch(actor.user_id, created.id)
    except AppError as exc:
        await cb.answer(i18n.get("error-generic", code=exc.code), show_alert=True)
        return
    manager.dialog_data["result"] = created.name
    await manager.next()


def _kind_label(manager: DialogManager, kind: int) -> str:
    key = next((k for value, k in BOOK_KINDS if value == kind), "book-kind-personal")
    return i18n_of(manager).get(key)


async def _name_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {"prompt": i18n.get("book-name-prompt"), **btn_labels(i18n)}


async def _kind_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("book-kind-prompt"),
        "kinds": [(str(value), i18n.get(key)) for value, key in BOOK_KINDS],
        **btn_labels(i18n),
    }


async def _currency_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {"prompt": i18n.get("book-currency-prompt"), **btn_labels(i18n)}


async def _confirm_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    return {
        "prompt": i18n.get(
            "book-confirm",
            name=data.get("name", ""),
            kind=_kind_label(manager, int(data.get("kind", 0))),
            currency=data.get("currency", ""),
        ),
        **btn_labels(i18n),
    }


async def _done_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "message": i18n.get("book-created", name=manager.dialog_data.get("result", "")),
        **btn_labels(i18n),
    }


create_book_dialog = Dialog(
    Window(
        Format("{prompt}"),
        TextInput(id="book_name", on_success=_on_name),
        Cancel(Format("{cancel_label}")),
        state=CreateBook.name,
        getter=_name_getter,
    ),
    Window(
        Format("{prompt}"),
        Column(
            Select(
                Format("{item[1]}"),
                id="book_kind",
                item_id_getter=lambda item: item[0],
                items="kinds",
                on_click=_on_kind,
            )
        ),
        Back(Format("{back_label}")),
        state=CreateBook.kind,
        getter=_kind_getter,
    ),
    Window(
        Format("{prompt}"),
        TextInput(id="book_currency", on_success=_on_currency),
        Back(Format("{back_label}")),
        state=CreateBook.currency,
        getter=_currency_getter,
    ),
    Window(
        Format("{prompt}"),
        Button(Format("{confirm_label}"), id="book_confirm", on_click=_on_confirm),
        Back(Format("{back_label}")),
        Cancel(Format("{cancel_label}")),
        state=CreateBook.confirm,
        getter=_confirm_getter,
    ),
    Window(
        Format("{message}"),
        Cancel(Format("{close_label}")),
        state=CreateBook.done,
        getter=_done_getter,
    ),
)
