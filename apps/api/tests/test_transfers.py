# Account-to-account movements: transfers (same currency, rate 1, excluded from the weighted
# average) and FX conversions (real trade, counted). Each is one row touching both accounts.
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from httpx import AsyncClient


async def _account(
    client: AsyncClient, owner: dict[str, Any], name: str, currency: str
) -> dict[str, Any]:
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/accounts",
        headers=owner["headers"],
        json={"currency_code": currency, "name": name, "kind": 0, "opening_balance": "1000"},
    )
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


async def test_transfer_touches_both_accounts(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000001)
    book_id = owner["book"]["id"]
    cash = await _account(client, owner, "Cash", "USD")
    bank = await _account(client, owner, "Bank", "USD")

    resp = await client.post(
        f"/api/v1/books/{book_id}/transfers",
        headers=owner["headers"],
        json={"from_account_id": cash["id"], "to_account_id": bank["id"], "amount": "250"},
    )
    assert resp.status_code == 201, resp.text
    tx = resp.json()
    assert tx["kind"] == "internal_transfer"
    assert tx["quote_account_id"] == cash["id"]  # money out
    assert tx["base_account_id"] == bank["id"]  # money in
    assert tx["rate"] == "1.00000000"
    assert tx["amount_quote"] == tx["amount_base"] == "250.00000000"


async def test_transfer_is_excluded_from_weighted_avg(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000002)
    book_id = owner["book"]["id"]
    cash = await _account(client, owner, "Cash", "USD")
    bank = await _account(client, owner, "Bank", "USD")

    # One real trade at 90, plus a transfer that carries a synthetic rate of 1.
    await client.post(
        f"/api/v1/books/{book_id}/transactions",
        headers=owner["headers"],
        json={
            "direction": "sell",
            "base_currency_code": "RUB",
            "quote_currency_code": "USD",
            "amount_quote": "1000",
            "rate": "90.0",
        },
    )
    await client.post(
        f"/api/v1/books/{book_id}/transfers",
        headers=owner["headers"],
        json={"from_account_id": cash["id"], "to_account_id": bank["id"], "amount": "500"},
    )

    report = await client.get(
        f"/api/v1/books/{book_id}/reports/weighted-avg-rate",
        params={"quote": "USD", "direction": "sell"},
        headers=owner["headers"],
    )
    body = report.json()
    assert body["sample_count"] == 1  # the transfer is not a trade
    assert body["weighted_avg_rate"].startswith("90.0")


async def test_fx_conversion_counts_toward_weighted_avg(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000003)
    book_id = owner["book"]["id"]
    usd = await _account(client, owner, "USD cash", "USD")
    eur = await _account(client, owner, "EUR cash", "EUR")

    resp = await client.post(
        f"/api/v1/books/{book_id}/fx-conversions",
        headers=owner["headers"],
        json={
            "from_account_id": usd["id"],
            "to_account_id": eur["id"],
            "amount": "1000",
            "rate": "0.92",
        },
    )
    assert resp.status_code == 201, resp.text
    tx = resp.json()
    assert tx["kind"] == "fx_conversion"
    assert tx["quote_currency_code"] == "USD"
    assert tx["base_currency_code"] == "EUR"
    assert tx["amount_base"] == "920.00000000"  # 1000 * 0.92

    report = await client.get(
        f"/api/v1/books/{book_id}/reports/weighted-avg-rate",
        params={"quote": "USD", "direction": "sell"},
        headers=owner["headers"],
    )
    assert report.json()["sample_count"] == 1


async def test_transfer_currency_mismatch_is_422(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000004)
    book_id = owner["book"]["id"]
    usd = await _account(client, owner, "USD", "USD")
    eur = await _account(client, owner, "EUR", "EUR")

    resp = await client.post(
        f"/api/v1/books/{book_id}/transfers",
        headers=owner["headers"],
        json={"from_account_id": usd["id"], "to_account_id": eur["id"], "amount": "10"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "account_currency_mismatch"


async def test_same_account_transfer_is_422(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(998000005)
    book_id = owner["book"]["id"]
    cash = await _account(client, owner, "Cash", "USD")

    resp = await client.post(
        f"/api/v1/books/{book_id}/transfers",
        headers=owner["headers"],
        json={"from_account_id": cash["id"], "to_account_id": cash["id"], "amount": "10"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_transfer"


async def test_conversion_same_currency_is_422(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000006)
    book_id = owner["book"]["id"]
    cash = await _account(client, owner, "Cash", "USD")
    bank = await _account(client, owner, "Bank", "USD")

    resp = await client.post(
        f"/api/v1/books/{book_id}/fx-conversions",
        headers=owner["headers"],
        json={
            "from_account_id": cash["id"],
            "to_account_id": bank["id"],
            "amount": "10",
            "rate": "1",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_transfer"


async def test_transfer_from_another_book_is_422(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000007)
    other = await login(998000008)
    mine = await _account(client, owner, "Mine", "USD")
    theirs = await _account(client, other, "Theirs", "USD")

    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/transfers",
        headers=owner["headers"],
        json={"from_account_id": mine["id"], "to_account_id": theirs["id"], "amount": "10"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "account_not_in_book"


async def test_account_balance_series_tracks_movements(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000012)
    book_id = owner["book"]["id"]
    cash = await _account(client, owner, "Cash", "USD")  # opening 1000
    bank = await _account(client, owner, "Bank", "USD")

    await client.post(
        f"/api/v1/books/{book_id}/transfers",
        headers=owner["headers"],
        json={"from_account_id": cash["id"], "to_account_id": bank["id"], "amount": "250"},
    )

    out = await client.get(
        f"/api/v1/books/{book_id}/reports/account-balance",
        params={"account_id": cash["id"]},
        headers=owner["headers"],
    )
    assert out.status_code == 200, out.text
    body = out.json()
    assert body["opening_balance"] == "1000.00000000"
    assert body["points"][-1]["balance"] == "750.00000000"  # paid 250 out

    incoming = await client.get(
        f"/api/v1/books/{book_id}/reports/account-balance",
        params={"account_id": bank["id"]},
        headers=owner["headers"],
    )
    assert incoming.json()["points"][-1]["balance"] == "1250.00000000"  # received 250


async def test_trade_can_carry_a_category(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(998000009)
    book_id = owner["book"]["id"]
    category = await client.post(
        f"/api/v1/books/{book_id}/categories",
        headers=owner["headers"],
        json={"name": "Salary", "kind": 0},
    )
    category_id = category.json()["id"]

    resp = await client.post(
        f"/api/v1/books/{book_id}/transactions",
        headers=owner["headers"],
        json={
            "direction": "sell",
            "base_currency_code": "RUB",
            "quote_currency_code": "USD",
            "amount_quote": "100",
            "rate": "90",
            "category_id": category_id,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["category_id"] == category_id


async def test_trade_with_foreign_category_is_404(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(998000010)
    other = await login(998000011)
    foreign = await client.post(
        f"/api/v1/books/{other['book']['id']}/categories",
        headers=other["headers"],
        json={"name": "Theirs", "kind": 1},
    )

    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/transactions",
        headers=owner["headers"],
        json={
            "direction": "sell",
            "base_currency_code": "RUB",
            "quote_currency_code": "USD",
            "amount_quote": "100",
            "rate": "90",
            "category_id": foreign.json()["id"],
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "category_not_found"
