# Accounts: money round-trips as a decimal string, unknown currency is rejected, the archived
# filter works, editors can write but only owners hard-delete, and delete is FK-protected.
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from smart_accounting.auth.rbac import Role
from smart_accounting.models import BookMember, FxTransaction
from smart_accounting.models.fx_transaction import TransactionDirection


async def _make_account(
    client: AsyncClient, owner: dict[str, Any], **overrides: Any
) -> dict[str, Any]:
    payload = {"currency_code": "USD", "name": "Cash", "kind": 0, "opening_balance": "500"}
    payload.update(overrides)
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/accounts", headers=owner["headers"], json=payload
    )
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


async def test_create_account_money_roundtrips(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(995000001)
    account = await _make_account(client, owner, opening_balance="500")
    assert account["currency_code"] == "USD"
    assert account["opening_balance"] == "500.00000000"

    listed = await client.get(
        f"/api/v1/books/{owner['book']['id']}/accounts", headers=owner["headers"]
    )
    balances = {a["id"]: a["opening_balance"] for a in listed.json()}
    # Byte-identical between the create response and a fresh read.
    assert balances[account["id"]] == "500.00000000"


async def test_unknown_currency_is_422(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(995000002)
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/accounts",
        headers=owner["headers"],
        json={"currency_code": "ZZZ", "name": "Bogus", "kind": 0},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "currency_unknown"


async def test_list_filters_archived(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(995000003)
    active = await _make_account(client, owner, name="Active")
    stale = await _make_account(client, owner, name="Stale")

    archived = await client.patch(
        f"/api/v1/accounts/{stale['id']}", headers=owner["headers"], json={"archived": True}
    )
    assert archived.status_code == 200
    assert archived.json()["archived"] is True

    book_id = owner["book"]["id"]
    only_active = await client.get(
        f"/api/v1/books/{book_id}/accounts", params={"archived": "false"}, headers=owner["headers"]
    )
    assert [a["id"] for a in only_active.json()] == [active["id"]]

    only_archived = await client.get(
        f"/api/v1/books/{book_id}/accounts", params={"archived": "true"}, headers=owner["headers"]
    )
    assert [a["id"] for a in only_archived.json()] == [stale["id"]]

    everything = await client.get(f"/api/v1/books/{book_id}/accounts", headers=owner["headers"])
    assert {a["id"] for a in everything.json()} == {active["id"], stale["id"]}


async def test_owner_can_delete_account(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(995000004)
    account = await _make_account(client, owner)
    resp = await client.delete(f"/api/v1/accounts/{account['id']}", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json() == {"deleted": account["id"]}

    listed = await client.get(
        f"/api/v1/books/{owner['book']['id']}/accounts", headers=owner["headers"]
    )
    assert account["id"] not in {a["id"] for a in listed.json()}


async def test_delete_blocked_when_referenced_by_transaction(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(995000005)
    account = await _make_account(client, owner)
    db.add(
        FxTransaction(
            book_id=owner["book"]["id"],
            created_by_user_id=owner["user"]["id"],
            direction=TransactionDirection.buy,
            base_account_id=account["id"],
            base_currency_code="USD",
            quote_currency_code="EUR",
            amount_quote=Decimal("100"),
            rate=Decimal("1.1"),
            amount_base=Decimal("110"),
            occurred_at=datetime.now(tz=UTC),
        )
    )
    await db.commit()

    resp = await client.delete(f"/api/v1/accounts/{account['id']}", headers=owner["headers"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "account_in_use"


async def test_editor_can_create_but_not_delete(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(995000006)
    editor = await login(995000007)
    book_id = owner["book"]["id"]
    db.add(BookMember(book_id=book_id, user_id=editor["user"]["id"], role=int(Role.EDITOR)))
    await db.commit()

    created = await client.post(
        f"/api/v1/books/{book_id}/accounts",
        headers=editor["headers"],
        json={"currency_code": "USD", "name": "Editor's", "kind": 1},
    )
    assert created.status_code == 200, created.text

    blocked = await client.delete(
        f"/api/v1/accounts/{created.json()['id']}", headers=editor["headers"]
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "forbidden"


async def test_non_member_cannot_create(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(995000008)
    outsider = await login(995000009)
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/accounts",
        headers=outsider["headers"],
        json={"currency_code": "USD", "name": "Sneaky", "kind": 0},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "not_a_member"
