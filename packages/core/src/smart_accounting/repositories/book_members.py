# book_members repository — queries only, no transaction management.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from smart_accounting.common.uow import UoW
from smart_accounting.models import BookMember


class BookMembersRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def insert(
        self, *, book_id: int, user_id: int, role: int, accepted_at: datetime | None = None
    ) -> BookMember:
        member = BookMember(book_id=book_id, user_id=user_id, role=role, accepted_at=accepted_at)
        self._session.add(member)
        await self._session.flush()
        return member

    async def role_for(self, book_id: int, user_id: int) -> int | None:
        result = await self._session.execute(
            select(BookMember.role).where(
                BookMember.book_id == book_id, BookMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
