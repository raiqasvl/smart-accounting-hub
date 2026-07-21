# Shared API test harness: a savepoint-isolated app client, initData signing, and a `login`
# helper that onboards a user and returns their bearer headers + user/book.
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from dishka import Provider, Scope, make_async_container, provide
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from smart_accounting.common.uow import UoW
from smart_accounting.config import Settings, get_config
from smart_accounting.ioc import DepsProvider
from smart_accounting_api.main import create_app

TEST_BOT_TOKEN = "123456:api-integration-test-bot-token"
TEST_JWT_SECRET = "api-test-jwt-secret-at-least-32-bytes!!"


def sign_init_data(user: dict[str, Any], bot_token: str = TEST_BOT_TOKEN) -> str:
    fields = {"auth_date": str(int(time.time())), "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


@pytest_asyncio.fixture
async def conn() -> AsyncIterator[Any]:
    """One connection wrapping an outer transaction; every session (the app's UoW and the test's
    own `db`) joins it via savepoints, so a single rollback at teardown isolates the test."""
    base = get_config()
    engine = create_async_engine(base.POSTGRES_DSN)
    connection = await engine.connect()
    trans = await connection.begin()
    try:
        yield connection
    finally:
        if trans.is_active:
            await trans.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(conn: Any) -> AsyncIterator[AsyncClient]:
    base = get_config()

    class _TestProvider(Provider):
        @provide(scope=Scope.APP, override=True)
        def settings(self) -> Settings:
            return Settings(
                POSTGRES_DSN=base.POSTGRES_DSN,
                REDIS_DSN=base.REDIS_DSN,
                BOT_TOKEN=TEST_BOT_TOKEN,
                JWT_SECRET=TEST_JWT_SECRET,
            )

        @provide(scope=Scope.REQUEST, override=True)
        async def uow(self) -> AsyncIterator[UoW]:
            session = AsyncSession(
                bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            try:
                yield UoW(session)
            finally:
                await session.close()

    container = make_async_container(DepsProvider(), _TestProvider())
    transport = ASGITransport(app=create_app(container))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await container.close()


@pytest_asyncio.fixture
async def db(conn: Any) -> AsyncIterator[AsyncSession]:
    """A session on the same connection as the app, for seeding rows the HTTP surface can't yet
    create (e.g. a non-owner membership before invites exist). Commits release into the outer tx."""
    session = AsyncSession(
        bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def signer() -> Callable[..., str]:
    return sign_init_data


@pytest.fixture
def login(client: AsyncClient) -> Callable[..., Any]:
    async def _login(
        telegram_id: int, first_name: str = "User", language_code: str = "en"
    ) -> dict[str, Any]:
        init_data = sign_init_data(
            {"id": telegram_id, "first_name": first_name, "language_code": language_code}
        )
        resp = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
        resp.raise_for_status()
        body = resp.json()
        return {
            "token": body["access_token"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
            "user": body["user"],
            "book": body["book"],
        }

    return _login
