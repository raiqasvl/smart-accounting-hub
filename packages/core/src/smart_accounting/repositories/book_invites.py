# book_invites repository — queries only, no transaction management. Single-use magic links.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update

from smart_accounting.common.uow import UoW
from smart_accounting.models import BookInvite


class BookInvitesRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def insert(
        self, *, book_id: int, invited_by: int, token: str, role: int, expires_at: datetime
    ) -> BookInvite:
        invite = BookInvite(
            book_id=book_id,
            invited_by=invited_by,
            token=token,
            role=role,
            expires_at=expires_at,
        )
        self._session.add(invite)
        await self._session.flush()
        return invite

    async def get(self, invite_id: int) -> BookInvite | None:
        return await self._session.get(BookInvite, invite_id)

    async def get_by_token(self, token: str) -> BookInvite | None:
        result = await self._session.execute(select(BookInvite).where(BookInvite.token == token))
        return result.scalar_one_or_none()

    async def list_pending(self, book_id: int, now: datetime) -> list[BookInvite]:
        result = await self._session.execute(
            select(BookInvite)
            .where(
                BookInvite.book_id == book_id,
                BookInvite.used_at.is_(None),
                BookInvite.expires_at > now,
            )
            .order_by(BookInvite.id)
        )
        return list(result.scalars().all())

    async def mark_used(self, invite_id: int, used_at: datetime) -> None:
        await self._session.execute(
            update(BookInvite).where(BookInvite.id == invite_id).values(used_at=used_at)
        )

    async def delete(self, invite_id: int) -> None:
        await self._session.execute(delete(BookInvite).where(BookInvite.id == invite_id))
