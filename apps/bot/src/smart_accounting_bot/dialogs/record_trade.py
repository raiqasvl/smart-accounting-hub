# RecordTradeDialog — Direction → Quote currency → Amount → Rate → Confirm → Done. Records a
# single-leg plain_cash trade (M3). Base currency is the book's base; quote is picked from the
# currency catalogue (no free-text typos). A fresh idempotency_key per Confirm dedupes double-taps.
from __future__ import annotations

import uuid
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, Column, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Format
from pydantic import ValidationError

from smart_accounting.errors import AppError
from smart_accounting.schemas import TransactionCreateIn
from smart_accounting.services import BookService, CurrencyService, FxService, TransactionService

from .common import btn_labels, i18n_of, resolve_actor, service
from .states import RecordTrade
from .widgets import category_options

_DIRECTIONS: list[tuple[str, str]] = [("sell", "trade-dir-sell"), ("buy", "trade-dir-buy")]


def _dir_key(direction: str) -> str:
    return "trade-dir-buy" if direction == "buy" else "trade-dir-sell"


async def _on_direction(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["direction"] = item_id
    await manager.next()


async def _on_quote(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["quote"] = item_id
    await manager.next()


async def _on_amount(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["amount"] = text.strip()
    await manager.next()


async def _on_rate(
    msg: Message, _w: ManagedTextInput[str], manager: DialogManager, text: str
) -> None:
    manager.dialog_data["rate"] = text.strip()
    await manager.next()


async def _on_category(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["category_id"] = int(item_id)
    await manager.next()


async def _skip_category(cb: CallbackQuery, _b: Button, manager: DialogManager) -> None:
    manager.dialog_data.pop("category_id", None)
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
        dto = TransactionCreateIn(
            direction=data["direction"],
            base_currency_code=data["base"],
            quote_currency_code=data["quote"],
            amount_quote=data["amount"],
            rate=data["rate"],
            category_id=data.get("category_id"),
            idempotency_key=data["idem"],
        )
        tx, _replayed = await txs.record(actor.book_id, actor.user_id, dto)
    except ValidationError:
        await cb.answer(i18n.get("error-bad-amount"), show_alert=True)
        return
    except AppError as exc:
        await cb.answer(i18n.get("error-generic", code=exc.code), show_alert=True)
        return
    manager.dialog_data["result_base"] = tx.amount_base
    await manager.next()


async def _direction_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("trade-direction-prompt"),
        "directions": [(value, i18n.get(key)) for value, key in _DIRECTIONS],
        **btn_labels(i18n),
    }


async def _quote_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    currencies: list[tuple[str, str]] = []
    actor = await resolve_actor(manager)
    if actor is not None:
        svc = await service(manager, CurrencyService)
        rows = await svc.list_for_book(actor.book_id, actor.user_id)
        currencies = [(c.code, c.code) for c in rows]
    return {"prompt": i18n.get("trade-quote-prompt"), "currencies": currencies, **btn_labels(i18n)}


async def _amount_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("trade-amount-prompt", quote=manager.dialog_data.get("quote", "")),
        **btn_labels(i18n),
    }


async def _rate_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    base = ""
    hint = "—"
    actor = await resolve_actor(manager)
    if actor is not None:
        books = await service(manager, BookService)
        book = await books.get(actor.book_id, actor.user_id)
        base = book.base_currency_code
        data["base"] = base
        fx = await service(manager, FxService)
        fx_hint = await fx.latest_rate(actor.book_id, actor.user_id, base, str(data.get("quote", "")))
        if fx_hint.rate is not None:
            hint = format(fx_hint.rate, ".4f")
    return {
        "prompt": i18n.get("trade-rate-prompt", base=base, quote=data.get("quote", ""), hint=hint),
        **btn_labels(i18n),
    }


async def _category_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("trade-category-prompt"),
        "categories": await category_options(manager),
        "skip_label": i18n.get("btn-skip"),
        **btn_labels(i18n),
    }


async def _confirm_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    data.setdefault("idem", uuid.uuid4().hex)  # one key per Confirm window → double-tap safe
    return {
        "prompt": i18n.get(
            "trade-confirm",
            direction=i18n.get(_dir_key(str(data.get("direction", "sell")))),
            base=data.get("base", ""),
            quote=data.get("quote", ""),
            amount=data.get("amount", ""),
            rate=data.get("rate", ""),
        ),
        **btn_labels(i18n),
    }


async def _done_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "message": i18n.get("trade-recorded", base=manager.dialog_data.get("result_base", "")),
        **btn_labels(i18n),
    }


record_trade_dialog = Dialog(
    Window(
        Format("{prompt}"),
        Column(
            Select(
                Format("{item[1]}"),
                id="trade_dir",
                item_id_getter=lambda item: item[0],
                items="directions",
                on_click=_on_direction,
            )
        ),
        Cancel(Format("{cancel_label}")),
        state=RecordTrade.direction,
        getter=_direction_getter,
    ),
    Window(
        Format("{prompt}"),
        ScrollingGroup(
            Select(
                Format("{item[1]}"),
                id="trade_quote",
                item_id_getter=lambda item: item[0],
                items="currencies",
                on_click=_on_quote,
            ),
            id="trade_quote_sg",
            width=3,
            height=6,
        ),
        Back(Format("{back_label}")),
        state=RecordTrade.quote,
        getter=_quote_getter,
    ),
    Window(
        Format("{prompt}"),
        TextInput(id="trade_amount", on_success=_on_amount),
        Back(Format("{back_label}")),
        state=RecordTrade.amount,
        getter=_amount_getter,
    ),
    Window(
        Format("{prompt}"),
        TextInput(id="trade_rate", on_success=_on_rate),
        Back(Format("{back_label}")),
        state=RecordTrade.rate,
        getter=_rate_getter,
    ),
    Window(
        Format("{prompt}"),
        ScrollingGroup(
            Select(
                Format("{item[1]}"),
                id="trade_category",
                item_id_getter=lambda item: item[0],
                items="categories",
                on_click=_on_category,
            ),
            id="trade_category_sg",
            width=2,
            height=6,
        ),
        Button(Format("{skip_label}"), id="trade_skip_category", on_click=_skip_category),
        Back(Format("{back_label}")),
        state=RecordTrade.category,
        getter=_category_getter,
    ),
    Window(
        Format("{prompt}"),
        Button(Format("{confirm_label}"), id="trade_confirm", on_click=_on_confirm),
        Back(Format("{back_label}")),
        Cancel(Format("{cancel_label}")),
        state=RecordTrade.confirm,
        getter=_confirm_getter,
    ),
    Window(
        Format("{message}"),
        Cancel(Format("{close_label}")),
        state=RecordTrade.done,
        getter=_done_getter,
    ),
)
