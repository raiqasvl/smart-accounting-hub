# Weighted-average aggregate — the M3 headline arithmetic (D16). DB-backed via the savepoint session.
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from smart_accounting.common.uow import UoW
from smart_accounting.models import Book, FxTransaction, User
from smart_accounting.models.fx_transaction import TransactionDirection, TransactionKind
from smart_accounting.repositories.reports import ReportsRepo


async def _seed_book(session: AsyncSession) -> Book:
    user = User(telegram_user_id=999_000_001, language="en", timezone="UTC")
    session.add(user)
    await session.flush()
    book = Book(owner_id=user.id, name="Test", kind=0, base_currency_code="RUB")
    session.add(book)
    await session.flush()
    return book


def _sell_leg(book: Book, amount_quote: str, rate: str) -> FxTransaction:
    aq = Decimal(amount_quote)
    r = Decimal(rate)
    return FxTransaction(
        book_id=book.id,
        created_by_user_id=book.owner_id,
        kind=TransactionKind.plain_cash,
        direction=TransactionDirection.sell,
        base_currency_code="RUB",
        quote_currency_code="USD",
        amount_quote=aq,
        rate=r,
        amount_base=aq * r,  # D16 invariant
        fee=Decimal(0),
        fee_currency_code=None,
        occurred_at=datetime(2026, 7, 1, tzinfo=UTC),
        note=None,
        base_account_id=None,
        quote_account_id=None,
        idempotency_key=None,
    )


async def test_weighted_avg_matches_fixture(db_session: AsyncSession) -> None:
    book = await _seed_book(db_session)
    db_session.add_all([_sell_leg(book, "1000", "90.0"), _sell_leg(book, "10000", "90.3")])
    await db_session.flush()

    repo = ReportsRepo(UoW(db_session))
    avg, count, total = await repo.weighted_avg_rate(book.id, "USD", TransactionDirection.sell)

    assert count == 2
    assert total == Decimal("11000")
    assert avg is not None
    # (1000*90.0 + 10000*90.3) / 11000 = 993000 / 11000 = 90.272727...
    assert avg.quantize(Decimal("0.0001")) == Decimal("90.2727")


async def test_weighted_avg_empty_returns_none(db_session: AsyncSession) -> None:
    book = await _seed_book(db_session)
    repo = ReportsRepo(UoW(db_session))
    avg, count, total = await repo.weighted_avg_rate(book.id, "USD", TransactionDirection.sell)

    assert avg is None
    assert count == 0
    assert total == Decimal(0)


async def test_weighted_avg_ignores_archived_and_other_direction(db_session: AsyncSession) -> None:
    book = await _seed_book(db_session)
    keep = _sell_leg(book, "1000", "90.0")
    archived = _sell_leg(book, "5000", "80.0")
    archived.archived = True
    buy = _sell_leg(book, "5000", "70.0")
    buy.direction = TransactionDirection.buy
    db_session.add_all([keep, archived, buy])
    await db_session.flush()

    repo = ReportsRepo(UoW(db_session))
    avg, count, total = await repo.weighted_avg_rate(book.id, "USD", TransactionDirection.sell)

    assert count == 1
    assert total == Decimal("1000")
    assert avg is not None
    assert avg.quantize(Decimal("0.0001")) == Decimal("90.0000")
