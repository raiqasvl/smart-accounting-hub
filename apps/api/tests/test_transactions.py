# FX transactions + weighted-average API: record (amount_base = amount_quote*rate, D16), idempotent
# replay (D28), list, patch recompute, archive, the weighted-avg report, the FX hint, and RBAC gates.
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from smart_accounting.auth.rbac import Role
from smart_accounting.models import BookMember


def _sell(**over: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "direction": "sell",
        "base_currency_code": "RUB",
        "quote_currency_code": "USD",
        "amount_quote": "1000",
        "rate": "90.0",
    }
    payload.update(over)
    return payload


async def test_record_computes_amount_base(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(996000001)
    book_id = owner["book"]["id"]
    resp = await client.post(
        f"/api/v1/books/{book_id}/transactions", headers=owner["headers"], json=_sell()
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["amount_base"] == "90000.00000000"  # 1000 * 90.0
    assert body["kind"] == "plain_cash"
    assert body["direction"] == "sell"


async def test_idempotent_replay(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(996000002)
    book_id = owner["book"]["id"]
    payload = _sell(idempotency_key="dup-1")

    first = await client.post(
        f"/api/v1/books/{book_id}/transactions", headers=owner["headers"], json=payload
    )
    assert first.status_code == 201
    second = await client.post(
        f"/api/v1/books/{book_id}/transactions", headers=owner["headers"], json=payload
    )
    assert second.status_code == 200
    assert second.headers.get("Idempotent-Replayed") == "true"
    assert second.json()["id"] == first.json()["id"]


async def test_list_and_patch_recompute(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(996000003)
    book_id = owner["book"]["id"]
    created = await client.post(
        f"/api/v1/books/{book_id}/transactions", headers=owner["headers"], json=_sell()
    )
    tx_id = created.json()["id"]

    listed = await client.get(
        f"/api/v1/books/{book_id}/transactions", headers=owner["headers"]
    )
    assert listed.status_code == 200
    page = listed.json()
    assert page["has_more"] is False
    assert tx_id in {t["id"] for t in page["items"]}

    patched = await client.patch(
        f"/api/v1/transactions/{tx_id}", headers=owner["headers"], json={"rate": "91.0"}
    )
    assert patched.status_code == 200
    assert patched.json()["amount_base"] == "91000.00000000"  # 1000 * 91.0

    archived = await client.delete(
        f"/api/v1/transactions/{tx_id}", headers=owner["headers"]
    )
    assert archived.status_code == 200
    assert archived.json() == {"archived": tx_id}


async def test_weighted_avg_endpoint(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(996000004)
    book_id = owner["book"]["id"]
    for amount, rate in (("1000", "90.0"), ("10000", "90.3")):
        r = await client.post(
            f"/api/v1/books/{book_id}/transactions",
            headers=owner["headers"],
            json=_sell(amount_quote=amount, rate=rate),
        )
        assert r.status_code == 201

    report = await client.get(
        f"/api/v1/books/{book_id}/reports/weighted-avg-rate",
        params={"quote": "USD", "direction": "sell"},
        headers=owner["headers"],
    )
    assert report.status_code == 200
    body = report.json()
    assert body["sample_count"] == 2
    assert body["sum_amount_quote"] == "11000.00000000"
    assert body["weighted_avg_rate"].startswith("90.2727")


async def test_fx_latest_hint_is_null_without_rates(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(996000005)
    book_id = owner["book"]["id"]
    resp = await client.get(
        f"/api/v1/books/{book_id}/fx/latest",
        params={"base": "RUB", "quote": "USD"},
        headers=owner["headers"],
    )
    assert resp.status_code == 200
    assert resp.json() == {"base": "RUB", "quote": "USD", "rate": None, "source": "frankfurter"}


async def test_csv_export_has_stable_columns(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(996000010)
    book_id = owner["book"]["id"]
    category = await client.post(
        f"/api/v1/books/{book_id}/categories",
        headers=owner["headers"],
        json={"name": "Trading", "kind": 2},
    )
    await client.post(
        f"/api/v1/books/{book_id}/transactions",
        headers=owner["headers"],
        json=_sell(category_id=category.json()["id"]),
    )

    resp = await client.get(
        f"/api/v1/books/{book_id}/transactions/export.csv", headers=owner["headers"]
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    lines = resp.text.strip().splitlines()
    assert lines[0] == (
        "id,occurred_at,kind,direction,base_currency_code,quote_currency_code,"
        "amount_quote,rate,amount_base,fee,fee_currency_code,base_account,"
        "quote_account,category,note"
    )
    assert len(lines) == 2
    row = lines[1].split(",")
    assert row[2] == "plain_cash"
    assert row[3] == "sell"
    assert row[6] == "1000.00000000"  # money keeps its decimal-string form
    assert row[13] == "Trading"  # category resolved to its name


async def test_viewer_can_export(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(996000011)
    viewer = await login(996000012)
    book_id = owner["book"]["id"]
    db.add(BookMember(book_id=book_id, user_id=viewer["user"]["id"], role=int(Role.VIEWER)))
    await db.commit()

    resp = await client.get(
        f"/api/v1/books/{book_id}/transactions/export.csv", headers=viewer["headers"]
    )
    assert resp.status_code == 200  # D-M4-6: export is read-only, so tx.read is enough


async def test_non_member_cannot_list(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(996000006)
    outsider = await login(996000007)
    resp = await client.get(
        f"/api/v1/books/{owner['book']['id']}/transactions", headers=outsider["headers"]
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "not_a_member"


async def test_viewer_cannot_record(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(996000008)
    viewer = await login(996000009)
    book_id = owner["book"]["id"]
    db.add(BookMember(book_id=book_id, user_id=viewer["user"]["id"], role=int(Role.VIEWER)))
    await db.commit()

    resp = await client.post(
        f"/api/v1/books/{book_id}/transactions", headers=viewer["headers"], json=_sell()
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
