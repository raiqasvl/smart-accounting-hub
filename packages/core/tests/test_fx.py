# FX provider client + refresh task. HTTP is mocked with respx; the DB write uses a savepoint-
# isolated sessionmaker bound to its own rolled-back connection (refresh_once commits internally).
from __future__ import annotations

from decimal import Decimal

import httpx
import respx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from smart_accounting.config import get_config
from smart_accounting.fx.clients import FrankfurterClient
from smart_accounting.fx.refresh import refresh_once
from smart_accounting.models import ExchangeRate

_LATEST = "https://api.frankfurter.dev/v1/latest"
_PAYLOAD = {"base": "USD", "rates": {"RUB": 90.3, "EUR": 0.92}}


@respx.mock
async def test_frankfurter_parses_rates() -> None:
    route = respx.get(_LATEST).mock(return_value=httpx.Response(200, json=_PAYLOAD))
    async with httpx.AsyncClient() as http:
        client = FrankfurterClient(http, "https://api.frankfurter.dev/v1")
        rates = await client.fetch_latest("USD")

    assert route.called
    assert rates["RUB"] == Decimal("90.3")
    assert rates["EUR"] == Decimal("0.92")


@respx.mock
async def test_refresh_once_inserts_rows() -> None:
    respx.get(_LATEST).mock(return_value=httpx.Response(200, json=_PAYLOAD))
    engine = create_async_engine(get_config().POSTGRES_DSN)
    conn = await engine.connect()
    trans = await conn.begin()
    sessionmaker = async_sessionmaker(
        bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        async with httpx.AsyncClient() as http:
            client = FrankfurterClient(http, "https://api.frankfurter.dev/v1")
            count = await refresh_once(sessionmaker, client, base="USD")

        assert count == 2
        async with sessionmaker() as session:
            total = (
                await session.execute(
                    select(func.count())
                    .select_from(ExchangeRate)
                    .where(
                        ExchangeRate.source == "frankfurter",
                        ExchangeRate.base_currency_code == "USD",
                        ExchangeRate.quote_currency_code.in_(["RUB", "EUR"]),
                    )
                )
            ).scalar_one()
        assert total >= 2
    finally:
        if trans.is_active:
            await trans.rollback()
        await conn.close()
        await engine.dispose()
