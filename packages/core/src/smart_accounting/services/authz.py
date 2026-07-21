# Shared authorization helper used by every book-scoped service: resolve the actor's role for a
# book (raising NotAMember if they aren't one), so the service can then require_permission.
from __future__ import annotations

from smart_accounting.errors import NotAMember
from smart_accounting.repositories.book_members import BookMembersRepo


async def resolve_role(members: BookMembersRepo, book_id: int, user_id: int) -> int:
    role = await members.role_for(book_id, user_id)
    if role is None:
        raise NotAMember({"book_id": book_id})
    return role
