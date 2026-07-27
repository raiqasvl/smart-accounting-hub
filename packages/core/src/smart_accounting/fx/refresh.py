# FX rate refresh task — runs in the apps/api process lifespan (no worker container at MVP).
# Fetches the latest Frankfurter rates and appends exchange_rates rows. Must never die: the loop
# catches and logs every exception. When v1.1 needs recurring jobs this migrates to apps/worker.
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from smart_accounting.common.uow import UoW
from smart_accounting.fx.clients import FxClient
from smart_accounting.repositories.exchange_rates import ExchangeRatesRepo

log = logging.getLogger(__name__)


async def refresh_once(
    sessionmaker: async_sessionmaker[AsyncSession], client: FxClient, base: str = "USD"
) -> int:
    """Fetch once and persist. Returns the number of rows inserted."""
    rates = await client.fetch_latest(base)
    async with sessionmaker() as session:
        repo = ExchangeRatesRepo(UoW(session))
        inserted = await repo.insert_many(
            base=base, source="frankfurter", fetched_at=datetime.now(UTC), rates=rates
        )
        await session.commit()
    return inserted


async def refresh_loop(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    client: FxClient,
    interval_seconds: int = 3600,
    base: str = "USD",
) -> None:
    while True:
        try:
            count = await refresh_once(sessionmaker, client, base)
            log.info("fx_refresh_ok rows=%d base=%s", count, base)
        except Exception:
            # The loop must survive any provider/DB hiccup — log and retry next tick.
            log.exception("fx_refresh_failed")
        await asyncio.sleep(interval_seconds)
