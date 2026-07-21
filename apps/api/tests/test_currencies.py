# Currencies: system catalogue visibility, per-book overrides, isolation, duplicate conflict.
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from httpx import AsyncClient


async def test_list_returns_system_catalogue(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    session = await login(992000001)
    book_id = session["book"]["id"]
    resp = await client.get(
        "/api/v1/currencies", params={"book_id": book_id}, headers=session["headers"]
    )
    assert resp.status_code == 200, resp.text
    codes = {c["code"] for c in resp.json()}
    assert {"USD", "EUR", "BTC", "XAU"} <= codes
    assert len(resp.json()) >= 45


async def test_book_override_is_isolated(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(992000002)
    book_a = owner["book"]["id"]
    created = await client.post(
        f"/api/v1/books/{book_a}/currencies",
        headers=owner["headers"],
        json={"code": "XTS", "symbol": "T", "decimals": 2, "kind": 0},
    )
    assert created.status_code == 200, created.text
    assert created.json()["book_id"] == book_a

    a_list = await client.get(
        "/api/v1/currencies", params={"book_id": book_a}, headers=owner["headers"]
    )
    assert "XTS" in {c["code"] for c in a_list.json()}

    other = await login(992000003)
    book_b = other["book"]["id"]
    b_list = await client.get(
        "/api/v1/currencies", params={"book_id": book_b}, headers=other["headers"]
    )
    assert "XTS" not in {c["code"] for c in b_list.json()}


async def test_duplicate_override_conflicts(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(992000004)
    book = owner["book"]["id"]
    payload = {"code": "XTS", "symbol": "T", "decimals": 2, "kind": 0}
    assert (
        await client.post(
            f"/api/v1/books/{book}/currencies", headers=owner["headers"], json=payload
        )
    ).status_code == 200
    dup = await client.post(
        f"/api/v1/books/{book}/currencies", headers=owner["headers"], json=payload
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "currency_exists"
