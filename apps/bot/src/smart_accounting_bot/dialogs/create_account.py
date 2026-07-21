# CreateAccountDialog — Currency → Kind → Name → OpeningBalance → Confirm → Done. Calls
# AccountService.create in the chat's active book. Currency is typed (validated server-side).
from __future__ import annotations

from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, Column, Select
from aiogram_dialog.widgets.text import Format
from pydantic import ValidationError

from smart_accounting.errors import AppError
from smart_accounting.schemas import AccountCreateIn
from smart_accounting.services import AccountService

from .common import ACCOUNT_KINDS, btn_labels, i18n_of, resolve_actor, service
from .states import CreateAccount


async def _on_currency(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["currency"] = text.strip().upper()
    await manager.next()


async def _on_kind(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["kind"] = int(item_id)
    await manager.next()


async def _on_name(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["name"] = text.strip()
    await manager.next()


async def _on_opening(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["opening"] = text.strip() or "0"
    await manager.next()


async def _on_confirm(cb: CallbackQuery, _b: Button, manager: DialogManager) -> None:
    i18n = i18n_of(manager)
    actor = await resolve_actor(manager)
    if actor is None:
        await cb.answer(i18n.get("error-no-book"), show_alert=True)
        return
    data = manager.dialog_data
    accounts = await service(manager, AccountService)
    try:
        dto = AccountCreateIn(
            currency_code=str(data["currency"]),
            name=str(data["name"]),
            kind=int(data["kind"]),
            opening_balance=str(data.get("opening", "0")),
        )
        created = await accounts.create(actor.book_id, actor.user_id, dto)
    except ValidationError:
        await cb.answer(i18n.get("error-bad-amount"), show_alert=True)
        return
    except AppError as exc:
        await cb.answer(i18n.get("error-generic", code=exc.code), show_alert=True)
        return
    manager.dialog_data["result_name"] = created.name
    manager.dialog_data["result_balance"] = created.opening_balance
    await manager.next()


def _kind_label(manager: DialogManager, kind: int) -> str:
    key = next((k for value, k in ACCOUNT_KINDS if value == kind), "account-kind-cash")
    return i18n_of(manager).get(key)


async def _currency_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {"prompt": i18n.get("account-currency-prompt"), **btn_labels(i18n)}


async def _kind_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("account-kind-prompt"),
        "kinds": [(str(value), i18n.get(key)) for value, key in ACCOUNT_KINDS],
        **btn_labels(i18n),
    }


async def _name_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {"prompt": i18n.get("account-name-prompt"), **btn_labels(i18n)}


async def _opening_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {"prompt": i18n.get("account-opening-prompt"), **btn_labels(i18n)}


async def _confirm_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    return {
        "prompt": i18n.get(
            "account-confirm",
            name=data.get("name", ""),
            currency=data.get("currency", ""),
            kind=_kind_label(manager, int(data.get("kind", 0))),
            opening=data.get("opening", "0"),
        ),
        **btn_labels(i18n),
    }


async def _done_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    return {
        "message": i18n.get(
            "account-created",
            name=data.get("result_name", ""),
            balance=data.get("result_balance", ""),
        ),
        **btn_labels(i18n),
    }


create_account_dialog = Dialog(
    Window(
        Format("{prompt}"),
        TextInput(id="acc_currency", on_success=_on_currency),
        Cancel(Format("{cancel_label}")),
        state=CreateAccount.currency,
        getter=_currency_getter,
    ),
    Window(
        Format("{prompt}"),
        Column(
            Select(
                Format("{item[1]}"),
                id="acc_kind",
                item_id_getter=lambda item: item[0],
                items="kinds",
                on_click=_on_kind,
            )
        ),
        Back(Format("{back_label}")),
        state=CreateAccount.kind,
        getter=_kind_getter,
    ),
    Window(
        Format("{prompt}"),
        TextInput(id="acc_name", on_success=_on_name),
        Back(Format("{back_label}")),
        state=CreateAccount.name,
        getter=_name_getter,
    ),
    Window(
        Format("{prompt}"),
        TextInput(id="acc_opening", on_success=_on_opening),
        Back(Format("{back_label}")),
        state=CreateAccount.opening,
        getter=_opening_getter,
    ),
    Window(
        Format("{prompt}"),
        Button(Format("{confirm_label}"), id="acc_confirm", on_click=_on_confirm),
        Back(Format("{back_label}")),
        Cancel(Format("{cancel_label}")),
        state=CreateAccount.confirm,
        getter=_confirm_getter,
    ),
    Window(
        Format("{message}"),
        Cancel(Format("{close_label}")),
        state=CreateAccount.done,
        getter=_done_getter,
    ),
)
