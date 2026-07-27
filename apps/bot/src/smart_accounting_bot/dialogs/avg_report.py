# AvgReportDialog — Direction → Quote currency → Period → Result. Renders the headline
# weighted-average rate (D16) for the chat's active book.
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Back, Cancel, Column, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Format

from smart_accounting.services import CurrencyService, ReportService

from .common import btn_labels, i18n_of, resolve_actor, service
from .states import AvgReport

_DIRECTIONS: list[tuple[str, str]] = [("sell", "trade-dir-sell"), ("buy", "trade-dir-buy")]
_PERIODS: list[tuple[str, str]] = [
    ("30d", "avg-period-30d"),
    ("month", "avg-period-month"),
    ("all", "avg-period-all"),
]


def _dir_key(direction: str) -> str:
    return "trade-dir-buy" if direction == "buy" else "trade-dir-sell"


def _period_range(period: str) -> tuple[datetime | None, datetime | None]:
    now = datetime.now(UTC)
    if period == "30d":
        return now - timedelta(days=30), None
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), None
    return None, None


async def _on_direction(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["direction"] = item_id
    await manager.next()


async def _on_quote(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["quote"] = item_id
    await manager.next()


async def _on_period(cb: CallbackQuery, _w: Any, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["period"] = item_id
    await manager.next()


async def _direction_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("avg-direction-prompt"),
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
    return {"prompt": i18n.get("avg-quote-prompt"), "currencies": currencies, **btn_labels(i18n)}


async def _period_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    return {
        "prompt": i18n.get("avg-period-prompt"),
        "periods": [(value, i18n.get(key)) for value, key in _PERIODS],
        **btn_labels(i18n),
    }


async def _result_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    manager = dialog_manager
    i18n = i18n_of(manager)
    data = manager.dialog_data
    actor = await resolve_actor(manager)
    if actor is None:
        return {"message": i18n.get("error-no-book"), **btn_labels(i18n)}
    reports = await service(manager, ReportService)
    period_from, period_to = _period_range(str(data.get("period", "all")))
    report = await reports.weighted_avg(
        actor.book_id,
        actor.user_id,
        str(data["quote"]),
        str(data["direction"]),
        period_from,
        period_to,
    )
    direction_label = i18n.get(_dir_key(str(data["direction"])))
    if report.weighted_avg_rate is None:
        message = i18n.get("avg-empty", quote=str(data["quote"]), direction=direction_label)
    else:
        message = i18n.get(
            "avg-result",
            direction=direction_label,
            quote=str(data["quote"]),
            rate=format(report.weighted_avg_rate, ".4f"),
            count=report.sample_count,
            total=format(report.sum_amount_quote, "f"),
        )
    return {"message": message, **btn_labels(i18n)}


avg_report_dialog = Dialog(
    Window(
        Format("{prompt}"),
        Column(
            Select(
                Format("{item[1]}"),
                id="avg_dir",
                item_id_getter=lambda item: item[0],
                items="directions",
                on_click=_on_direction,
            )
        ),
        Cancel(Format("{cancel_label}")),
        state=AvgReport.direction,
        getter=_direction_getter,
    ),
    Window(
        Format("{prompt}"),
        ScrollingGroup(
            Select(
                Format("{item[1]}"),
                id="avg_quote",
                item_id_getter=lambda item: item[0],
                items="currencies",
                on_click=_on_quote,
            ),
            id="avg_quote_sg",
            width=3,
            height=6,
        ),
        Back(Format("{back_label}")),
        state=AvgReport.quote,
        getter=_quote_getter,
    ),
    Window(
        Format("{prompt}"),
        Column(
            Select(
                Format("{item[1]}"),
                id="avg_period",
                item_id_getter=lambda item: item[0],
                items="periods",
                on_click=_on_period,
            )
        ),
        Back(Format("{back_label}")),
        state=AvgReport.period,
        getter=_period_getter,
    ),
    Window(
        Format("{message}"),
        Cancel(Format("{close_label}")),
        state=AvgReport.result,
        getter=_result_getter,
    ),
)
