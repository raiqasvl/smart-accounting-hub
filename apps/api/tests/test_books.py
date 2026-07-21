# Books: create (caller becomes OWNER), member-gated reads, the rename/archive authz split
# (D-M2-2), and switch (re-mints the JWT + repoints the user's chats at the new book).
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_accounting.auth.rbac import Role
from smart_accounting.models import BookMember, TgChat


async def _seed_member(db: AsyncSession, *, book_id: int, user_id: int, role: Role) -> None:
    db.add(BookMember(book_id=book_id, user_id=user_id, role=int(role)))
    await db.commit()


async def test_create_makes_caller_owner_and_lists(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(993000001)
    created = await client.post(
        "/api/v1/books",
        headers=owner["headers"],
        json={"name": "Business", "kind": 2, "base_currency_code": "EUR"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["role"] == int(Role.OWNER)
    assert body["name"] == "Business"

    listed = await client.get("/api/v1/books", headers=owner["headers"])
    ids = {b["id"] for b in listed.json()}
    assert body["id"] in ids
    # The default personal book from onboarding is there too.
    assert owner["book"]["id"] in ids


async def test_non_member_read_is_forbidden(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(993000002)
    outsider = await login(993000003)
    resp = await client.get(f"/api/v1/books/{owner['book']['id']}", headers=outsider["headers"])
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "not_a_member"


async def test_editor_cannot_rename_or_archive(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(993000004)
    editor = await login(993000005)
    book_id = owner["book"]["id"]
    await _seed_member(db, book_id=book_id, user_id=editor["user"]["id"], role=Role.EDITOR)

    rename = await client.patch(
        f"/api/v1/books/{book_id}", headers=editor["headers"], json={"name": "Nope"}
    )
    assert rename.status_code == 403
    assert rename.json()["error"]["code"] == "forbidden"

    archive = await client.patch(
        f"/api/v1/books/{book_id}", headers=editor["headers"], json={"archived": True}
    )
    assert archive.status_code == 403


async def test_admin_can_rename_but_not_archive(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(993000006)
    admin = await login(993000007)
    book_id = owner["book"]["id"]
    await _seed_member(db, book_id=book_id, user_id=admin["user"]["id"], role=Role.ADMIN)

    rename = await client.patch(
        f"/api/v1/books/{book_id}", headers=admin["headers"], json={"name": "Renamed"}
    )
    assert rename.status_code == 200, rename.text
    assert rename.json()["name"] == "Renamed"

    archive = await client.patch(
        f"/api/v1/books/{book_id}", headers=admin["headers"], json={"archived": True}
    )
    assert archive.status_code == 403


async def test_owner_can_rename_and_archive(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(993000008)
    book_id = owner["book"]["id"]
    resp = await client.patch(
        f"/api/v1/books/{book_id}",
        headers=owner["headers"],
        json={"name": "Archived Co", "archived": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Archived Co"


async def test_switch_remints_jwt_and_updates_chats(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(993000009)
    user_id = owner["user"]["id"]
    home_book = owner["book"]["id"]

    created = await client.post(
        "/api/v1/books",
        headers=owner["headers"],
        json={"name": "Second", "kind": 0, "base_currency_code": "USD"},
    )
    second_book = created.json()["id"]

    # A chat currently pointing at the home book (the bot creates these; seed one directly).
    db.add(TgChat(chat_id=7770001, user_id=user_id, active_book_id=home_book))
    await db.commit()

    switched = await client.post(f"/api/v1/books/{second_book}/switch", headers=owner["headers"])
    assert switched.status_code == 200, switched.text
    token_body = switched.json()
    assert token_body["book"]["id"] == second_book

    # The fresh JWT carries book_id=second_book: GET /me resolves the active book from the claim.
    new_headers = {"Authorization": f"Bearer {token_body['access_token']}"}
    me = await client.get("/api/v1/me", headers=new_headers)
    assert me.status_code == 200, me.text
    assert me.json()["active_book"]["id"] == second_book

    # The user's chat was repointed at the switched-to book.
    db.expire_all()
    active = (
        await db.execute(select(TgChat.active_book_id).where(TgChat.chat_id == 7770001))
    ).scalar_one()
    assert active == second_book


async def test_non_member_cannot_switch(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(993000010)
    outsider = await login(993000011)
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/switch", headers=outsider["headers"]
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "not_a_member"
