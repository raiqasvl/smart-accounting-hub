# InternalTransferDialog — FromAccount → ToAccount → Amount → Confirm → Done. Moves money between
# two accounts of the same currency (one row, kind=internal_transfer). The to-account list is
# filtered to the from-account's currency, so a mismatch can't be picked in the first place.
from __future__ import annotations

import uuid
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Format
from pydantic import ValidationError

from smart_accounting.errors import AppError
from smart_accounting.schemas import TransferCreateIn
from smart_accounting.services import TransactionService

from .common import btn_labels, i18n_of, resolve_actor, service
from .states import InternalTransfer
from .widgets import account_by_id, account_options


async def _on_from(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["from_id"] = int(item_id)
    account = await account_by_id(manager, int(item_id))
    if account is not None:
        manager.dialog_data["currency"] = account.currency_code
        manager.dialog_data["from_name"] = account.name
    await manager.next()


async def _on_to(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["to_id"] = int(item_id)
    account = await account_by_id(manager, int(item_id))
    if account is not None:
        manager.dialog_data["to_name"] = account.name
    await manager.next()


async def _on_amount(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["amount"] = text.strip()
    await manager.next()


async def _on_confirm(cb: CallbackQuery, _b: Button, manager: DialogManager) -> None:
    i18n = i18n_of(manager)
    actor = await resolve_actor(manager)
    if actor is None:
        await cb.answer(i18n.get("error-no-book"), show_alert=True)
        return
    data = manager.dialog_data
    txs = await service(manager, TransactionService)
    try:
        dto = TransferCreateIn(
            from_account_id=int(data["from_id"]),
            to_account_id=int(data["to_id"]),
            amount=data["amount"],
            idempotency_key=data["idem"],
        )
        await txs.record_transfer(actor.book_id, actor.user_id, dto)
    except ValidationError:
        await cb.answer(i18n.get("error-bad-amount"), show_alert=True)
        return
    except AppError as exc:
        await cb.answer(i18n.get("error-generic", code=exc.code), show_alert=True)
        return
    await manager.next()


async def _from_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("transfer-from-prompt"),
        "accounts": await account_options(manager),
        **btn_labels(i18n),
    }


async def _to_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    return {
        "prompt": i18n.get("transfer-to-prompt", currency=data.get("currency", "")),
        "accounts": await account_options(
            manager,
            currency_code=str(data.get("currency")) if data.get("currency") else None,
            exclude_id=int(data["from_id"]) if data.get("from_id") else None,
        ),
        **btn_labels(i18n),
    }


async def _amount_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get(
            "transfer-amount-prompt", currency=manager.dialog_data.get("currency", "")
        ),
        **btn_labels(i18n),
    }


async def _confirm_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    data.setdefault("idem", uuid.uuid4().hex)
    return {
        "prompt": i18n.get(
            "transfer-confirm",
            amount=data.get("amount", ""),
            currency=data.get("currency", ""),
            source=data.get("from_name", ""),
            target=data.get("to_name", ""),
        ),
        **btn_labels(i18n),
    }


async def _done_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    return {
        "message": i18n.get(
            "transfer-done",
            amount=data.get("amount", ""),
            currency=data.get("currency", ""),
            target=data.get("to_name", ""),
        ),
        **btn_labels(i18n),
    }


internal_transfer_dialog = Dialog(
    Window(
        Format("{prompt}"),
        ScrollingGroup(
            Select(
                Format("{item[1]}"),
                id="tr_from",
                item_id_getter=lambda item: item[0],
                items="accounts",
                on_click=_on_from,
            ),
            id="tr_from_sg",
            width=1,
            height=6,
        ),
        Cancel(Format("{cancel_label}")),
        state=InternalTransfer.from_account,
        getter=_from_getter,
    ),
    Window(
        Format("{prompt}"),
        ScrollingGroup(
            Select(
                Format("{item[1]}"),
                id="tr_to",
                item_id_getter=lambda item: item[0],
                items="accounts",
                on_click=_on_to,
            ),
            id="tr_to_sg",
            width=1,
            height=6,
        ),
        Back(Format("{back_label}")),
        state=InternalTransfer.to_account,
        getter=_to_getter,
    ),
    Window(
        Format("{prompt}"),
        TextInput(id="tr_amount", on_success=_on_amount),
        Back(Format("{back_label}")),
        state=InternalTransfer.amount,
        getter=_amount_getter,
    ),
    Window(
        Format("{prompt}"),
        Button(Format("{confirm_label}"), id="tr_confirm", on_click=_on_confirm),
        Back(Format("{back_label}")),
        Cancel(Format("{cancel_label}")),
        state=InternalTransfer.confirm,
        getter=_confirm_getter,
    ),
    Window(
        Format("{message}"),
        Cancel(Format("{close_label}")),
        state=InternalTransfer.done,
        getter=_done_getter,
    ),
)
