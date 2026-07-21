# UserService — the shared onboarding core (D21). Called by both the API auth path and the bot
# /start handler. Returns Pydantic DTOs, never ORM entities (so the bot never touches models).
from __future__ import annotations

from smart_accounting.auth.rbac import Role
from smart_accounting.common.uow import UoW
from smart_accounting.errors import JwtInvalid
from smart_accounting.models import Book, User
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.books import BooksRepo
from smart_accounting.repositories.users import UsersRepo
from smart_accounting.schemas import BookOut, MeOut, UserOut
from smart_accounting.services.identity import TgIdentity

# language_code -> base currency (D21 heuristic).
_CURRENCY_BY_LANG = {
    "ru": "RUB",
    "uk": "UAH",
    "tr": "TRY",
    "de": "EUR",
    "fr": "EUR",
    "es": "EUR",
    "it": "EUR",
    "pl": "EUR",
    "nl": "EUR",
}


def pick_language(language_code: str | None) -> str:
    """Supported UI languages are en + ru; everything else (incl. uk) falls back to en."""
    return "ru" if language_code and language_code.startswith("ru") else "en"


def pick_currency(language_code: str | None) -> str:
    prefix = (language_code or "").split("-")[0].lower()
    return _CURRENCY_BY_LANG.get(prefix, "USD")


def default_book_name(language: str) -> str:
    return "Личный" if language == "ru" else "Personal"


def _user_to_dto(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        telegram_user_id=user.telegram_user_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.telegram_username,
        language=user.language,
        timezone=user.timezone,
    )


def _book_to_dto(book: Book, role: int) -> BookOut:
    return BookOut(
        id=book.id,
        name=book.name,
        kind=book.kind,
        base_currency_code=book.base_currency_code,
        role=role,
    )


class UserService:
    def __init__(
        self, uow: UoW, users: UsersRepo, books: BooksRepo, members: BookMembersRepo
    ) -> None:
        self._uow = uow
        self._users = users
        self._books = books
        self._members = members

    async def ensure_user_and_default_book(self, ident: TgIdentity) -> tuple[UserOut, BookOut]:
        """First-touch onboarding: create user + default personal book + OWNER membership in a
        single transaction (idempotent on telegram_user_id). Returns (user, active book) DTOs.

        The UoW commits on clean exit of the `async with` block (rolls back on exception)."""
        async with self._uow:
            user = await self._users.get_by_telegram_id(ident.telegram_user_id)
            if user is None:
                language = pick_language(ident.language_code)
                user = await self._users.insert(
                    telegram_user_id=ident.telegram_user_id,
                    username=ident.username,
                    first_name=ident.first_name,
                    last_name=ident.last_name,
                    language=language,
                )
                book = await self._books.insert(
                    owner_id=user.id,
                    name=default_book_name(language),
                    kind=0,  # personal
                    base_currency_code=pick_currency(ident.language_code),
                )
                await self._members.insert(book_id=book.id, user_id=user.id, role=Role.OWNER)
                role = int(Role.OWNER)
            else:
                book = await self._books.primary_for(user.id)
                existing_role = await self._members.role_for(book.id, user.id)
                role = int(Role.OWNER) if existing_role is None else existing_role
        return _user_to_dto(user), _book_to_dto(book, role)

    async def load_me(self, *, user_id: int, book_id: int) -> MeOut:
        """Read path for GET /me: the user, their active book (+role), and all their books."""
        async with self._uow:
            user = await self._users.get(user_id)
            active_book = await self._books.get(book_id)
            if user is None or active_book is None:
                raise JwtInvalid({"reason": "stale_token"})
            active_role = await self._members.role_for(book_id, user_id)
            role = int(Role.VIEWER) if active_role is None else active_role
            book_dtos: list[BookOut] = []
            for book in await self._books.list_for_user(user_id):
                member_role = await self._members.role_for(book.id, user_id)
                book_dtos.append(
                    _book_to_dto(book, int(Role.VIEWER) if member_role is None else member_role)
                )
            me = MeOut(
                user=_user_to_dto(user),
                active_book=_book_to_dto(active_book, role),
                role=role,
                books=book_dtos,
            )
        return me
