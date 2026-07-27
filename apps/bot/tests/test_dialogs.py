# Unit tests for the M2 dialog service-call handlers (the on_click/on_success callbacks). These
# drive the handlers with a faked DialogManager whose Dishka container yields mocked services, so
# they assert the exact service calls without spinning up the aiogram-dialog engine. Actual
# persistence is covered by the API-layer suites (test_books / test_accounts / test_invites).
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from smart_accounting.schemas import (
    AccountOut,
    BookOut,
    TokenOut,
    TransactionOut,
    UserOut,
    WeightedAvgReportOut,
)
from smart_accounting.services import (
    AccountService,
    BookService,
    InviteService,
    ReportService,
    TgChatService,
    TransactionService,
)
from smart_accounting_bot.dialogs.avg_report import _result_getter as avg_result_getter
from smart_accounting_bot.dialogs.books_menu import _on_pick
from smart_accounting_bot.dialogs.create_account import _on_confirm as account_confirm
from smart_accounting_bot.dialogs.create_book import _on_confirm as book_confirm
from smart_accounting_bot.dialogs.join_invite import _on_accept
from smart_accounting_bot.dialogs.record_trade import _on_confirm as trade_confirm


def _manager(
    services: dict[type, Any],
    *,
    chat_id: int = 555,
    dialog_data: dict[str, Any] | None = None,
    start_data: dict[str, Any] | None = None,
) -> MagicMock:
    manager = MagicMock()
    manager.dialog_data = dialog_data if dialog_data is not None else {}
    manager.start_data = start_data
    manager.next = AsyncMock()
    manager.done = AsyncMock()

    i18n = MagicMock()
    i18n.get.side_effect = lambda key, **kw: key
    i18n.locale = "en"

    container = MagicMock()
    container.get = AsyncMock(side_effect=lambda cls: services[cls])

    event_chat = MagicMock()
    event_chat.id = chat_id
    manager.middleware_data = {
        "dishka_container": container,
        "i18n": i18n,
        "event_chat": event_chat,
    }
    return manager


def _chat_service(user_id: int = 7, book_id: int = 3) -> AsyncMock:
    tg = AsyncMock()
    tg.context = AsyncMock(return_value=(user_id, book_id))
    return tg


async def test_create_book_confirm_creates_and_switches() -> None:
    books = AsyncMock()
    books.create = AsyncMock(
        return_value=BookOut(id=9, name="Biz", kind=2, base_currency_code="EUR", role=0)
    )
    books.switch = AsyncMock()
    manager = _manager(
        {TgChatService: _chat_service(), BookService: books},
        dialog_data={"name": "Biz", "kind": 2, "currency": "EUR"},
    )

    await book_confirm(AsyncMock(), MagicMock(), manager)

    books.create.assert_awaited_once()
    user_id, dto = books.create.call_args.args
    assert user_id == 7
    assert (dto.name, dto.kind, dto.base_currency_code) == ("Biz", 2, "EUR")
    books.switch.assert_awaited_once_with(7, 9)
    manager.next.assert_awaited_once()
    assert manager.dialog_data["result"] == "Biz"


async def test_create_account_confirm_creates_in_active_book() -> None:
    accounts = AsyncMock()
    accounts.create = AsyncMock(
        return_value=AccountOut(
            id=1,
            book_id=3,
            currency_code="USD",
            name="Cash",
            kind=0,
            archived=False,
            opening_balance=Decimal("500"),
        )
    )
    manager = _manager(
        {TgChatService: _chat_service(), AccountService: accounts},
        dialog_data={"currency": "USD", "kind": 0, "name": "Cash", "opening": "500"},
    )

    await account_confirm(AsyncMock(), MagicMock(), manager)

    accounts.create.assert_awaited_once()
    book_id, user_id, dto = accounts.create.call_args.args
    assert (book_id, user_id) == (3, 7)
    assert (dto.currency_code, dto.name, dto.opening_balance) == ("USD", "Cash", Decimal("500"))
    manager.next.assert_awaited_once()
    assert manager.dialog_data["result_name"] == "Cash"


async def test_join_invite_accept_adds_member_and_switches() -> None:
    invites = AsyncMock()
    invites.accept = AsyncMock(
        return_value=BookOut(id=5, name="Shared", kind=1, base_currency_code="USD", role=2)
    )
    books = AsyncMock()
    books.switch = AsyncMock()
    manager = _manager(
        {TgChatService: _chat_service(), InviteService: invites, BookService: books},
        start_data={"token": "tok123"},
    )

    await _on_accept(AsyncMock(), MagicMock(), manager)

    invites.accept.assert_awaited_once_with("tok123", 7)
    books.switch.assert_awaited_once_with(7, 5)
    manager.next.assert_awaited_once()
    assert manager.dialog_data["result"] == "Shared"


async def test_books_menu_pick_switches_active_book() -> None:
    books = AsyncMock()
    books.switch = AsyncMock(
        return_value=TokenOut(
            access_token="t",
            expires_in=1800,
            user=UserOut(id=7, telegram_user_id=1, language="en", timezone="UTC"),
            book=BookOut(id=5, name="Family", kind=1, base_currency_code="USD", role=1),
        )
    )
    manager = _manager({TgChatService: _chat_service(), BookService: books})

    await _on_pick(AsyncMock(), MagicMock(), manager, "5")

    books.switch.assert_awaited_once_with(7, 5)
    manager.next.assert_awaited_once()
    assert manager.dialog_data["result"] == "Family"


async def test_record_trade_confirm_records() -> None:
    txs = AsyncMock()
    txs.record = AsyncMock(
        return_value=(
            TransactionOut(
                id=1,
                book_id=3,
                created_by_user_id=7,
                kind="plain_cash",
                direction="sell",
                base_currency_code="RUB",
                quote_currency_code="USD",
                amount_quote=Decimal("1000"),
                rate=Decimal("90"),
                amount_base=Decimal("90000"),
                fee=Decimal("0"),
                fee_currency_code=None,
                base_account_id=None,
                quote_account_id=None,
                occurred_at=datetime.now(UTC),
                note=None,
                archived=False,
            ),
            False,
        )
    )
    manager = _manager(
        {TgChatService: _chat_service(), TransactionService: txs},
        dialog_data={
            "direction": "sell",
            "base": "RUB",
            "quote": "USD",
            "amount": "1000",
            "rate": "90",
            "idem": "k1",
        },
    )

    await trade_confirm(AsyncMock(), MagicMock(), manager)

    txs.record.assert_awaited_once()
    book_id, user_id, dto = txs.record.call_args.args
    assert (book_id, user_id) == (3, 7)
    assert (dto.direction, dto.quote_currency_code) == ("sell", "USD")
    assert (dto.amount_quote, dto.rate) == (Decimal("1000"), Decimal("90"))
    manager.next.assert_awaited_once()
    assert manager.dialog_data["result_base"] == Decimal("90000")


async def test_avg_report_result_renders() -> None:
    reports = AsyncMock()
    reports.weighted_avg = AsyncMock(
        return_value=WeightedAvgReportOut(
            book_id=3,
            quote_currency_code="USD",
            direction="sell",
            weighted_avg_rate=Decimal("90.2727"),
            sample_count=2,
            sum_amount_quote=Decimal("11000"),
            period_from=None,
            period_to=None,
        )
    )
    manager = _manager(
        {TgChatService: _chat_service(), ReportService: reports},
        dialog_data={"direction": "sell", "quote": "USD", "period": "all"},
    )

    result = await avg_result_getter(dialog_manager=manager)

    reports.weighted_avg.assert_awaited_once()
    book_id, user_id, quote, direction, _from, _to = reports.weighted_avg.call_args.args
    assert (book_id, user_id, quote, direction) == (3, 7, "USD", "sell")
    assert result["message"] == "avg-result"


async def test_create_book_confirm_without_active_book_aborts() -> None:
    tg = AsyncMock()
    tg.context = AsyncMock(return_value=None)  # chat never onboarded
    books = AsyncMock()
    manager = _manager(
        {TgChatService: tg, BookService: books},
        dialog_data={"name": "X", "kind": 0, "currency": "USD"},
    )
    cb = AsyncMock()

    await book_confirm(cb, MagicMock(), manager)

    books.create.assert_not_awaited()
    cb.answer.assert_awaited_once()
    manager.next.assert_not_awaited()
