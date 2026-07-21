# books repository — queries only, no transaction management.
from __future__ import annotations

from sqlalchemy import select

from smart_accounting.common.uow import UoW
from smart_accounting.models import Book, BookMember


class BooksRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def insert(self, *, owner_id: int, name: str, kind: int, base_currency_code: str) -> Book:
        book = Book(owner_id=owner_id, name=name, kind=kind, base_currency_code=base_currency_code)
        self._session.add(book)
        await self._session.flush()
        return book

    async def get(self, book_id: int) -> Book | None:
        return await self._session.get(Book, book_id)

    async def primary_for(self, user_id: int) -> Book:
        """The user's default book — the lowest-id book they own (M1 creates exactly one)."""
        result = await self._session.execute(
            select(Book).where(Book.owner_id == user_id).order_by(Book.id).limit(1)
        )
        return result.scalar_one()

    async def list_for_user(self, user_id: int) -> list[Book]:
        result = await self._session.execute(
            select(Book)
            .join(BookMember, BookMember.book_id == Book.id)
            .where(BookMember.user_id == user_id)
            .order_by(Book.id)
        )
        return list(result.scalars().all())
