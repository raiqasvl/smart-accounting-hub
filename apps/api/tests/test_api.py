# API integration tests: the golden auth path + both negatives, against the app over httpx.
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator
from urllib.parse import urlencode

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


def sign_init_data(user: dict[str, object], bot_token: str = TEST_BOT_TOKEN) -> str:
    fields = {"auth_date": str(int(time.time())), "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    base = get_config()
    engine = create_async_engine(base.POSTGRES_DSN)
    conn = await engine.connect()
    trans = await conn.begin()

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
    if trans.is_active:
        await trans.rollback()
    await conn.close()
    await engine.dispose()


async def test_healthz(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readyz(client: AsyncClient) -> None:
    resp = await client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_golden_auth_then_me(client: AsyncClient) -> None:
    init_data = sign_init_data({"id": 991000001, "first_name": "Grace", "language_code": "en"})
    auth = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    assert auth.status_code == 200, auth.text
    body = auth.json()
    assert body["expires_in"] == 1800
    assert body["user"]["telegram_user_id"] == 991000001
    assert body["book"]["base_currency_code"] == "USD"
    token = body["access_token"]

    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    me_body = me.json()
    assert me_body["user"]["first_name"] == "Grace"
    assert me_body["active_book"]["name"] == "Personal"
    assert len(me_body["books"]) == 1


async def test_tampered_jwt_returns_401(client: AsyncClient) -> None:
    init_data = sign_init_data({"id": 991000002, "first_name": "Hal", "language_code": "en"})
    token = (await client.post("/api/v1/auth/telegram", json={"init_data": init_data})).json()[
        "access_token"
    ]
    head, _, sig = token.rpartition(".")
    tampered = (
        f"{head}.{'X' if sig[0] != 'X' else 'Y'}{sig[1:]}"  # first sig char always changes bytes
    )
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "jwt_invalid"
    assert body["request_id"].startswith("req_")


async def test_tampered_init_data_returns_403(client: AsyncClient) -> None:
    signed = sign_init_data({"id": 991000003, "first_name": "Ivy", "language_code": "en"})
    forged = signed.replace("Ivy", "Ivx")
    resp = await client.post("/api/v1/auth/telegram", json={"init_data": forged})
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "init_data_invalid"
    assert body["request_id"].startswith("req_")


async def test_openapi_lists_endpoints(client: AsyncClient) -> None:
    spec = (await client.get("/openapi.json")).json()
    assert "/api/v1/auth/telegram" in spec["paths"]
    assert "/api/v1/me" in spec["paths"]
