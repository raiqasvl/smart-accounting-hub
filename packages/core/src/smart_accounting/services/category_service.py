# CategoryService — hierarchical categories (D14). One transaction per method (UoW).
#
# Path convention (D-M4-1): a category's ltree path is its ancestors' ids followed by its own id
# (root "5", child "5.9"). Labels never change on rename, and a move is a single subtree UPDATE.
from __future__ import annotations

from sqlalchemy_utils import Ltree

from smart_accounting.auth.rbac import require_permission
from smart_accounting.common.uow import UoW
from smart_accounting.errors import (
    CategoryHasChildren,
    CategoryInUse,
    CategoryNotFound,
    InvalidCategoryParent,
)
from smart_accounting.models import Category
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.categories import CategoriesRepo
from smart_accounting.schemas import (
    CategoryCreateIn,
    CategoryMoveIn,
    CategoryOut,
    CategoryPatchIn,
)
from smart_accounting.services.authz import resolve_role


def _dto(row: Category) -> CategoryOut:
    path = str(row.parents_tree)
    return CategoryOut(
        id=row.id,
        book_id=row.book_id,
        parents_tree=path,
        depth=len(path.split(".")),
        kind=row.kind,
        name=row.name,
        description=row.description,
        archived=row.archived,
    )


class CategoryService:
    def __init__(self, uow: UoW, categories: CategoriesRepo, members: BookMembersRepo) -> None:
        self._uow = uow
        self._categories = categories
        self._members = members

    async def create(self, book_id: int, user_id: int, dto: CategoryCreateIn) -> CategoryOut:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "category.write")
            parent_path: Ltree | None = None
            if dto.parent_id is not None:
                parent = await self._categories.get(dto.parent_id)
                if parent is None or parent.book_id != book_id:
                    raise InvalidCategoryParent({"parent_id": dto.parent_id})
                parent_path = parent.parents_tree
            category = await self._categories.insert(
                book_id=book_id, kind=dto.kind, name=dto.name, description=dto.description
            )
            own = Ltree(str(category.id))
            path = own if parent_path is None else parent_path + own
            await self._categories.set_path(category, path)
            return _dto(category)

    async def list_for_book(
        self, book_id: int, user_id: int, include_archived: bool = False
    ) -> list[CategoryOut]:
        async with self._uow:
            role = await resolve_role(self._members, book_id, user_id)
            require_permission(role, "book.read")
            rows = await self._categories.list_for_book(book_id, include_archived)
            return [_dto(row) for row in rows]

    async def patch(self, category_id: int, user_id: int, dto: CategoryPatchIn) -> CategoryOut:
        async with self._uow:
            await self._load(category_id, user_id, "category.write")
            updated = await self._categories.update(
                category_id, name=dto.name, description=dto.description, archived=dto.archived
            )
            assert updated is not None  # loaded above, same transaction
            return _dto(updated)

    async def move(self, category_id: int, user_id: int, dto: CategoryMoveIn) -> CategoryOut:
        async with self._uow:
            category = await self._load(category_id, user_id, "category.write")
            old_path = category.parents_tree
            own = Ltree(str(category.id))

            if dto.parent_id is None:
                new_path = own
            else:
                if dto.parent_id == category_id:
                    raise InvalidCategoryParent({"parent_id": dto.parent_id})
                parent = await self._categories.get(dto.parent_id)
                if parent is None or parent.book_id != category.book_id:
                    raise InvalidCategoryParent({"parent_id": dto.parent_id})
                # Re-parenting under your own descendant would detach the subtree from the root.
                if str(parent.parents_tree).startswith(f"{old_path}."):
                    raise InvalidCategoryParent(
                        {"parent_id": dto.parent_id, "reason": "descendant"}
                    )
                new_path = parent.parents_tree + own

            if str(new_path) != str(old_path):
                await self._categories.move_subtree(
                    category.book_id, category.id, old_path, new_path
                )
                await self._uow.session.refresh(category)
            return _dto(category)

    async def delete(self, category_id: int, user_id: int) -> None:
        """Hard delete, guarded: a category with descendants or referencing transactions must be
        archived instead (D29) so history stays intact."""
        async with self._uow:
            category = await self._load(category_id, user_id, "category.write")
            if await self._categories.children_count(category.book_id, category.parents_tree):
                raise CategoryHasChildren({"category_id": category_id})
            if await self._categories.has_transactions(category_id):
                raise CategoryInUse({"category_id": category_id})
            await self._categories.delete(category_id)

    async def _load(self, category_id: int, user_id: int, permission: str) -> Category:
        """Bare /categories/{id} routes carry no book_id: load the row, then authorize for its book."""
        category = await self._categories.get(category_id)
        if category is None:
            raise CategoryNotFound({"category_id": category_id})
        role = await resolve_role(self._members, category.book_id, user_id)
        require_permission(role, permission)
        return category
