# Shared fixtures for the core test suite.
#
# M1 runs integration tests against the local compose Postgres (already migrated). Each test
# gets a session bound to an outer transaction that is rolled back at teardown, so committed
# rows never persist (SQLAlchemy 2.0 `join_transaction_mode="create_savepoint"` turns the
# service's own commits into savepoints inside that transaction).
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from smart_accounting.config import get_config


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_config().POSTGRES_DSN)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(
        bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        await session.close()
        if trans.is_active:
            await trans.rollback()
        await conn.close()
        await engine.dispose()
