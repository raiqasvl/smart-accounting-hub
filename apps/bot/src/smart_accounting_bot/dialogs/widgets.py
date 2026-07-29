# Reusable dialog pieces shared by more than one flow.
from __future__ import annotations

from typing import Any

from aiogram_dialog import DialogManager

from smart_accounting.services import AccountService, CategoryService

from .common import resolve_actor, service


async def category_options(manager: DialogManager) -> list[tuple[str, str]]:
    """(id, indented label) for every active category in the chat's book, in tree order."""
    actor = await resolve_actor(manager)
    if actor is None:
        return []
    categories = await service(manager, CategoryService)
    rows = await categories.list_for_book(actor.book_id, actor.user_id)
    return [(str(c.id), f"{'· ' * (c.depth - 1)}{c.name}") for c in rows]


async def account_options(
    manager: DialogManager, *, currency_code: str | None = None, exclude_id: int | None = None
) -> list[tuple[str, str]]:
    """(id, "Name (CUR)") for the book's active accounts, optionally narrowed to one currency."""
    actor = await resolve_actor(manager)
    if actor is None:
        return []
    accounts = await service(manager, AccountService)
    rows = await accounts.list_for_book(actor.book_id, actor.user_id, archived=False)
    return [
        (str(a.id), f"{a.name} ({a.currency_code})")
        for a in rows
        if (currency_code is None or a.currency_code == currency_code) and a.id != exclude_id
    ]


async def account_by_id(manager: DialogManager, account_id: int) -> Any:
    actor = await resolve_actor(manager)
    if actor is None:
        return None
    accounts = await service(manager, AccountService)
    rows = await accounts.list_for_book(actor.book_id, actor.user_id, archived=False)
    return next((a for a in rows if a.id == account_id), None)
