# InviteService — magic-link invitations: an admin mints a single-use token, another user accepts
# it via the Mini-App or the bot's /start deep-link. One transaction per method (UoW).
#
# Accept state machine (D-M2-4, single-use tokens):
#   - unknown token            -> InviteInvalid (404)
#   - past expires_at          -> InviteExpired (410)
#   - used & caller is member  -> idempotent no-op (200) — the caller is who consumed it
#   - used & caller not member  -> InviteAlreadyUsed (409) — someone else consumed it
#   - fresh & caller is member  -> AlreadyMember (409)
#   - fresh & caller not member -> join at the minted role, mark the token used
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from smart_accounting.auth.rbac import Role, require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.config import Settings
from smart_accounting.errors import (
    AlreadyMember,
    BookNotFound,
    Forbidden,
    InviteAlreadyUsed,
    InviteExpired,
    InviteInvalid,
)
from smart_accounting.models import Book, BookInvite
from smart_accounting.repositories.book_invites import BookInvitesRepo
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.books import BooksRepo
from smart_accounting.schemas import BookOut, InviteCreateIn, InviteOut
from smart_accounting.services.authz import resolve_role


def _book_dto(book: Book, role: int) -> BookOut:
    return BookOut(
        id=book.id,
        name=book.name,
        kind=book.kind,
        base_currency_code=book.base_currency_code,
        role=role,
    )


class InviteService:
    def __init__(
        self,
        uow: UoW,
        invites: BookInvitesRepo,
        members: BookMembersRepo,
        books: BooksRepo,
        settings: Settings,
    ) -> None:
        self._uow = uow
        self._invites = invites
        self._members = members
        self._books = books
        self._settings = settings

    def _deep_link(self, token: str) -> str:
        return f"https://t.me/{self._settings.BOT_USERNAME}?start=invite_{token}"

    def _to_dto(self, invite: BookInvite) -> InviteOut:
        return InviteOut(
            id=invite.id,
            book_id=invite.book_id,
            role=invite.role,
            token=invite.token,
            deep_link=self._deep_link(invite.token),
            expires_at=invite.expires_at,
            used_at=invite.used_at,
        )

    async def create(self, book_id: int, user_id: int, dto: InviteCreateIn) -> InviteOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "book.invite")
            if dto.role == int(Role.OWNER):
                raise Forbidden({"reason": "owner_role_not_invitable"})
            now = datetime.now(tz=UTC)
            invite = await self._invites.insert(
                book_id=book_id,
                invited_by=user_id,
                token=secrets.token_urlsafe(24),
                role=dto.role,
                expires_at=now + timedelta(minutes=dto.ttl_minutes),
            )
            return self._to_dto(invite)

    async def list_pending(self, book_id: int, user_id: int) -> list[InviteOut]:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "book.invite")
            now = datetime.now(tz=UTC)
            return [self._to_dto(i) for i in await self._invites.list_pending(book_id, now)]

    async def revoke(self, book_id: int, invite_id: int, user_id: int) -> None:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "book.invite")
            invite = await self._invites.get(invite_id)
            if invite is None or invite.book_id != book_id:
                raise InviteInvalid({"invite_id": invite_id})
            await self._invites.delete(invite_id)

    async def accept(self, token: str, user_id: int) -> BookOut:
        async with self._uow:
            invite = await self._invites.get_by_token(token)
            if invite is None:
                raise InviteInvalid({"token": token})
            now = datetime.now(tz=UTC)
            if invite.expires_at <= now:
                raise InviteExpired({"token": token})

            existing_role = await self._members.role_for(invite.book_id, user_id)
            if invite.used_at is not None:
                # Consumed already: a no-op for the member who used it, a conflict for anyone else.
                if existing_role is not None:
                    return await self._joined_book(invite.book_id, existing_role)
                raise InviteAlreadyUsed({"token": token})
            if existing_role is not None:
                raise AlreadyMember({"book_id": invite.book_id})

            await self._members.insert(
                book_id=invite.book_id, user_id=user_id, role=invite.role, accepted_at=now
            )
            await self._invites.mark_used(invite.id, now)
            return await self._joined_book(invite.book_id, invite.role)

    async def _joined_book(self, book_id: int, role: int) -> BookOut:
        book = await self._books.get(book_id)
        if book is None:
            raise BookNotFound({"book_id": book_id})
        return _book_dto(book, role)
