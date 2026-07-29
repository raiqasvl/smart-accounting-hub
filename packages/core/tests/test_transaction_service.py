# TransactionService + ReportService integration (DB-backed, savepoint session).
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from smart_accounting.auth.rbac import Role
from smart_accounting.common.uow import UoW
from smart_accounting.errors import CurrencyUnknown, Forbidden
from smart_accounting.models import Book, BookMember, User
from smart_accounting.repositories.accounts import AccountsRepo
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.categories import CategoriesRepo
from smart_accounting.repositories.currencies import CurrenciesRepo
from smart_accounting.repositories.reports import ReportsRepo
from smart_accounting.repositories.transactions import TransactionsRepo
from smart_accounting.schemas import TransactionCreateIn
from smart_accounting.services.report_service import ReportService
from smart_accounting.services.transaction_service import TransactionService


async def _seed_member(session: AsyncSession, tg_id: int, role: int = int(Role.OWNER)) -> tuple[int, int]:
    user = User(telegram_user_id=tg_id, language="en", timezone="UTC")
    session.add(user)
    await session.flush()
    book = Book(owner_id=user.id, name="Test", kind=0, base_currency_code="RUB")
    session.add(book)
    await session.flush()
    session.add(BookMember(book_id=book.id, user_id=user.id, role=role))
    await session.flush()
    return user.id, book.id


def _tx_service(session: AsyncSession) -> TransactionService:
    uow = UoW(session)
    return TransactionService(
        uow,
        TransactionsRepo(uow),
        AccountsRepo(uow),
        CurrenciesRepo(uow),
        CategoriesRepo(uow),
        BookMembersRepo(uow),
    )


def _sell(**over: object) -> TransactionCreateIn:
    base = {
        "direction": "sell",
        "base_currency_code": "RUB",
        "quote_currency_code": "USD",
        "amount_quote": Decimal("1000"),
        "rate": Decimal("90.0"),
    }
    base.update(over)
    return TransactionCreateIn(**base)  # type: ignore[arg-type]


async def test_record_computes_amount_base_and_is_idempotent(db_session: AsyncSession) -> None:
    user_id, book_id = await _seed_member(db_session, tg_id=900_100_001)
    svc = _tx_service(db_session)
    dto = _sell(idempotency_key="key-1")

    out1, replayed1 = await svc.record(book_id, user_id, dto)
    out2, replayed2 = await svc.record(book_id, user_id, dto)

    assert replayed1 is False
    assert replayed2 is True
    assert out1.id == out2.id
    assert out1.amount_base == Decimal("90000")  # 1000 * 90.0 (D16)
    assert out1.kind == "plain_cash"


async def test_record_rejects_unknown_currency(db_session: AsyncSession) -> None:
    user_id, book_id = await _seed_member(db_session, tg_id=900_100_002)
    svc = _tx_service(db_session)
    with pytest.raises(CurrencyUnknown):
        await svc.record(book_id, user_id, _sell(quote_currency_code="ZZZ"))


async def test_viewer_cannot_record(db_session: AsyncSession) -> None:
    user_id, book_id = await _seed_member(db_session, tg_id=900_100_003, role=int(Role.VIEWER))
    svc = _tx_service(db_session)
    with pytest.raises(Forbidden):
        await svc.record(book_id, user_id, _sell())


async def test_weighted_avg_through_service(db_session: AsyncSession) -> None:
    user_id, book_id = await _seed_member(db_session, tg_id=900_100_004)
    svc = _tx_service(db_session)
    await svc.record(book_id, user_id, _sell(amount_quote=Decimal("1000"), rate=Decimal("90.0")))
    await svc.record(book_id, user_id, _sell(amount_quote=Decimal("10000"), rate=Decimal("90.3")))

    uow = UoW(db_session)
    report = ReportService(uow, ReportsRepo(uow), AccountsRepo(uow), BookMembersRepo(uow))
    result = await report.weighted_avg(book_id, user_id, "USD", "sell")

    assert result.sample_count == 2
    assert result.sum_amount_quote == Decimal("11000")
    assert result.weighted_avg_rate is not None
    assert result.weighted_avg_rate.quantize(Decimal("0.0001")) == Decimal("90.2727")
