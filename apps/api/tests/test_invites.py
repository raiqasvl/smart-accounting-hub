# Invites: create (book.invite-gated), accept by another user, idempotent double-accept, and the
# expired / revoked / already-member / already-used state machine (D-M2-4).
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from smart_accounting.auth.rbac import Role
from smart_accounting.models import BookInvite, BookMember


async def _mint(client: AsyncClient, owner: dict[str, Any], role: int = int(Role.EDITOR)) -> str:
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/invites",
        headers=owner["headers"],
        json={"role": role, "ttl_minutes": 60},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deep_link"].endswith(f"start=invite_{body['token']}")
    return str(body["token"])


async def test_create_then_accept_by_other(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(994000001)
    other = await login(994000002)
    token = await _mint(client, owner, role=int(Role.EDITOR))

    accepted = await client.post(f"/api/v1/invites/{token}/accept", headers=other["headers"])
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["id"] == owner["book"]["id"]
    assert body["role"] == int(Role.EDITOR)

    # They can now read the book they joined (the member gate passes).
    read = await client.get(f"/api/v1/books/{owner['book']['id']}", headers=other["headers"])
    assert read.status_code == 200


async def test_double_accept_is_idempotent(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(994000003)
    other = await login(994000004)
    token = await _mint(client, owner)

    first = await client.post(f"/api/v1/invites/{token}/accept", headers=other["headers"])
    second = await client.post(f"/api/v1/invites/{token}/accept", headers=other["headers"])
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == owner["book"]["id"]


async def test_used_token_rejects_third_party(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(994000005)
    joiner = await login(994000006)
    stranger = await login(994000007)
    token = await _mint(client, owner)

    assert (
        await client.post(f"/api/v1/invites/{token}/accept", headers=joiner["headers"])
    ).status_code == 200
    blocked = await client.post(f"/api/v1/invites/{token}/accept", headers=stranger["headers"])
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "invite_already_used"


async def test_expired_token_returns_410(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(994000008)
    other = await login(994000009)
    db.add(
        BookInvite(
            book_id=owner["book"]["id"],
            invited_by=owner["user"]["id"],
            token="expired-token-fixture",
            role=int(Role.EDITOR),
            expires_at=datetime.now(tz=UTC) - timedelta(minutes=1),
        )
    )
    await db.commit()

    resp = await client.post(
        "/api/v1/invites/expired-token-fixture/accept", headers=other["headers"]
    )
    assert resp.status_code == 410
    assert resp.json()["error"]["code"] == "invite_expired"


async def test_revoked_token_returns_404(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(994000010)
    other = await login(994000011)
    minted = await client.post(
        f"/api/v1/books/{owner['book']['id']}/invites",
        headers=owner["headers"],
        json={"role": int(Role.EDITOR)},
    )
    invite_id = minted.json()["id"]
    token = minted.json()["token"]

    revoked = await client.delete(
        f"/api/v1/books/{owner['book']['id']}/invites/{invite_id}", headers=owner["headers"]
    )
    assert revoked.status_code == 200
    assert revoked.json() == {"revoked": invite_id}

    resp = await client.post(f"/api/v1/invites/{token}/accept", headers=other["headers"])
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "invite_invalid"


async def test_existing_member_accept_returns_409(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(994000012)
    token = await _mint(client, owner)
    # The owner is already a member of their own book → 409 on a fresh invite.
    resp = await client.post(f"/api/v1/invites/{token}/accept", headers=owner["headers"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "already_member"


async def test_editor_cannot_mint_invite(
    client: AsyncClient, login: Callable[..., Any], db: AsyncSession
) -> None:
    owner = await login(994000013)
    editor = await login(994000014)
    db.add(
        BookMember(book_id=owner["book"]["id"], user_id=editor["user"]["id"], role=int(Role.EDITOR))
    )
    await db.commit()

    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/invites",
        headers=editor["headers"],
        json={"role": int(Role.VIEWER)},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


async def test_cannot_invite_as_owner(client: AsyncClient, login: Callable[..., Any]) -> None:
    owner = await login(994000015)
    resp = await client.post(
        f"/api/v1/books/{owner['book']['id']}/invites",
        headers=owner["headers"],
        json={"role": int(Role.OWNER)},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["params"]["reason"] == "owner_role_not_invitable"


async def test_pending_list_reflects_lifecycle(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    owner = await login(994000016)
    other = await login(994000017)
    token = await _mint(client, owner)

    pending = await client.get(
        f"/api/v1/books/{owner['book']['id']}/invites", headers=owner["headers"]
    )
    assert pending.status_code == 200
    assert len(pending.json()) == 1

    # Once consumed, it drops off the pending list.
    await client.post(f"/api/v1/invites/{token}/accept", headers=other["headers"])
    after = await client.get(
        f"/api/v1/books/{owner['book']['id']}/invites", headers=owner["headers"]
    )
    assert after.json() == []
