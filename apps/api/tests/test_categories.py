# Categories: ltree paths built from ids, D14 cascade on move, delete guards (children / in-use),
# invalid-parent validation, and RBAC gates.
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


async def _make(
    client: AsyncClient, owner: dict[str, Any], name: str, parent_id: int | None = None
) -> dict[str, Any]:
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/categories",
        headers=owner["headers"],
        json={"name": name, "kind": 1, "parent_id": parent_id},
    )
    assert resp.status_code == 201, resp.text
    return dict(resp.json())


async def test_paths_are_built_from_ids(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(997000001)
    food = await _make(client, owner, "Food")
    lunch = await _make(client, owner, "Lunch", parent_id=food["id"])

    assert food["parents_tree"] == str(food["id"])
    assert food["depth"] == 1
    assert lunch["parents_tree"] == f"{food['id']}.{lunch['id']}"
    assert lunch["depth"] == 2


async def test_rename_keeps_paths(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(997000002)
    food = await _make(client, owner, "Food")
    lunch = await _make(client, owner, "Lunch", parent_id=food["id"])

    renamed = await client.patch(
        f"/api/v1/categories/{food['id']}", headers=owner["headers"], json={"name": "Daily"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Daily"
    assert renamed.json()["parents_tree"] == str(food["id"])

    listed = await client.get(
        f"/api/v1/books/{owner['book']['id']}/categories", headers=owner["headers"]
    )
    paths = {c["id"]: c["parents_tree"] for c in listed.json()}
    assert paths[lunch["id"]] == f"{food['id']}.{lunch['id']}"  # descendant untouched


async def test_move_cascades_to_descendants(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(997000003)
    food = await _make(client, owner, "Food")
    lunch = await _make(client, owner, "Lunch", parent_id=food["id"])
    cafe = await _make(client, owner, "Cafe", parent_id=lunch["id"])
    daily = await _make(client, owner, "Daily")

    moved = await client.post(
        f"/api/v1/categories/{food['id']}/move",
        headers=owner["headers"],
        json={"parent_id": daily["id"]},
    )
    assert moved.status_code == 200, moved.text

    listed = await client.get(
        f"/api/v1/books/{owner['book']['id']}/categories", headers=owner["headers"]
    )
    paths = {c["id"]: c["parents_tree"] for c in listed.json()}
    assert paths[food["id"]] == f"{daily['id']}.{food['id']}"
    assert paths[lunch["id"]] == f"{daily['id']}.{food['id']}.{lunch['id']}"
    assert paths[cafe["id"]] == f"{daily['id']}.{food['id']}.{lunch['id']}.{cafe['id']}"


async def test_move_to_root(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(997000004)
    food = await _make(client, owner, "Food")
    lunch = await _make(client, owner, "Lunch", parent_id=food["id"])

    moved = await client.post(
        f"/api/v1/categories/{lunch['id']}/move", headers=owner["headers"], json={"parent_id": None}
    )
    assert moved.status_code == 200
    assert moved.json()["parents_tree"] == str(lunch["id"])
    assert moved.json()["depth"] == 1


async def test_move_under_own_descendant_is_422(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(997000005)
    food = await _make(client, owner, "Food")
    lunch = await _make(client, owner, "Lunch", parent_id=food["id"])

    resp = await client.post(
        f"/api/v1/categories/{food['id']}/move",
        headers=owner["headers"],
        json={"parent_id": lunch["id"]},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_category_parent"


async def test_delete_blocked_by_children(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(997000006)
    food = await _make(client, owner, "Food")
    await _make(client, owner, "Lunch", parent_id=food["id"])

    resp = await client.delete(f"/api/v1/categories/{food['id']}", headers=owner["headers"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "category_has_children"


async def test_delete_blocked_by_transaction(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(997000007)
    food = await _make(client, owner, "Food")
    db.add(
        FxTransaction(
            book_id=owner["book"]["id"],
            created_by_user_id=owner["user"]["id"],
            direction=TransactionDirection.sell,
            base_currency_code="RUB",
            quote_currency_code="USD",
            amount_quote=Decimal("100"),
            rate=Decimal("90"),
            amount_base=Decimal("9000"),
            occurred_at=datetime.now(tz=UTC),
            category_id=food["id"],
        )
    )
    await db.commit()

    resp = await client.delete(f"/api/v1/categories/{food['id']}", headers=owner["headers"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "category_in_use"


async def test_leaf_delete_and_archive_filter(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(997000008)
    book_id = owner["book"]["id"]
    keep = await _make(client, owner, "Keep")
    gone = await _make(client, owner, "Gone")

    deleted = await client.delete(f"/api/v1/categories/{gone['id']}", headers=owner["headers"])
    assert deleted.status_code == 200

    archived = await client.patch(
        f"/api/v1/categories/{keep['id']}", headers=owner["headers"], json={"archived": True}
    )
    assert archived.status_code == 200

    active = await client.get(f"/api/v1/books/{book_id}/categories", headers=owner["headers"])
    assert active.json() == []

    everything = await client.get(
        f"/api/v1/books/{book_id}/categories",
        params={"include_archived": "true"},
        headers=owner["headers"],
    )
    assert [c["id"] for c in everything.json()] == [keep["id"]]


async def test_viewer_cannot_create(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(997000009)
    viewer = await login(997000010)
    book_id = owner["book"]["id"]
    db.add(BookMember(book_id=book_id, user_id=viewer["user"]["id"], role=int(Role.VIEWER)))
    await db.commit()

    resp = await client.post(
        f"/api/v1/books/{book_id}/categories",
        headers=viewer["headers"],
        json={"name": "Nope", "kind": 1},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
