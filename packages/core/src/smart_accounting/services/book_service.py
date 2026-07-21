# BookService — book CRUD + book switching (re-mints the JWT). One transaction per method (UoW).
# Authorization is enforced here: resolve the actor's role for the *path* book_id via book_members
# (raising NotAMember), then require_permission. rename = admin+ ; archive = owner (D-M2-2).
from __future__ import annotations

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.auth.rbac import Role, require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.config import Settings
from smart_accounting.errors import BookNotFound, JwtInvalid
from smart_accounting.models import Book
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.books import BooksRepo
from smart_accounting.repositories.tg_chats import TgChatsRepo
from smart_accounting.repositories.users import UsersRepo
from smart_accounting.schemas import BookCreateIn, BookOut, BookPatchIn, TokenOut, UserOut
from smart_accounting.services.authz import resolve_role


def _book_dto(book: Book, role: int) -> BookOut:
    return BookOut(
        id=book.id,
        name=book.name,
        kind=book.kind,
        base_currency_code=book.base_currency_code,
        role=role,
    )


class BookService:
    def __init__(
        self,
        uow: UoW,
        books: BooksRepo,
        members: BookMembersRepo,
        tg_chats: TgChatsRepo,
        users: UsersRepo,
        jwt: JwtCodec,
        settings: Settings,
    ) -> None:
        self._uow = uow
        self._books = books
        self._members = members
        self._tg_chats = tg_chats
        self._users = users
        self._jwt = jwt
        self._settings = settings

    async def create(self, user_id: int, dto: BookCreateIn) -> BookOut:
        """New book + OWNER membership for the creator, in one transaction."""
        async with self._uow:
            book = await self._books.insert(
                owner_id=user_id,
                name=dto.name,
                kind=dto.kind,
                base_currency_code=dto.base_currency_code,
                default_language=dto.default_language,
            )
            await self._members.insert(book_id=book.id, user_id=user_id, role=Role.OWNER)
            return _book_dto(book, int(Role.OWNER))

    async def list_for_user(self, user_id: int) -> list[BookOut]:
        async with self._uow:
            out: list[BookOut] = []
            for book in await self._books.list_for_user(user_id):
                role = await self._members.role_for(book.id, user_id)
                if role is not None:
                    out.append(_book_dto(book, role))
            return out

    async def get(self, book_id: int, user_id: int) -> BookOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)  # raises NotAMember (403)
            book = await self._books.get(book_id)
            if book is None:
                raise BookNotFound({"book_id": book_id})
            return _book_dto(book, role)

    async def update(self, book_id: int, user_id: int, dto: BookPatchIn) -> BookOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            # rename is an administrative op (admin+); archive is destructive (owner only).
            if dto.name is not None:
                require_permission(role, "book.role.change")
            if dto.archived is not None:
                require_permission(role, "book.delete")
            book = await self._books.update(book_id, name=dto.name, archived=dto.archived)
            if book is None:
                raise BookNotFound({"book_id": book_id})
            return _book_dto(book, role)

    async def switch(self, user_id: int, book_id: int) -> TokenOut:
        """Verify membership, point all the user's chats at this book, and re-mint a JWT whose
        book_id + role claims reflect the switch (the Mini-App replaces its stored token)."""
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            book = await self._books.get(book_id)
            if book is None:
                raise BookNotFound({"book_id": book_id})
            user = await self._users.get(user_id)
            if user is None:
                raise JwtInvalid({"reason": "stale_token"})
            await self._tg_chats.set_active_book_for_user(user_id, book_id)
            token = self._jwt.issue(user_id=user_id, book_id=book_id, role=role)
            return TokenOut(
                access_token=token,
                expires_in=self._settings.JWT_LIFETIME_SECONDS,
                user=UserOut.model_validate(user),
                book=_book_dto(book, role),
            )
