# categories repository — queries only, no transaction management. Paths are ltree (D14); labels
# are the ancestor ids, so a rename never rewrites paths and a move is one UPDATE over the subtree.
from __future__ import annotations

from sqlalchemy import delete, func, select, text
from sqlalchemy_utils import Ltree

from smart_accounting.common.uow import UoW
from smart_accounting.models import Category, FxTransaction


class CategoriesRepo:
    def __init__(self, uow: UoW) -> None:
        self._session = uow.session

    async def insert(
        self, *, book_id: int, kind: int, name: str, description: str | None
    ) -> Category:
        """Insert with a placeholder path; the caller sets the real path once `id` exists
        (the path's last label IS the id, so it can't be known before the flush)."""
        category = Category(
            book_id=book_id,
            parents_tree=Ltree("0"),
            kind=kind,
            name=name,
            description=description,
        )
        self._session.add(category)
        await self._session.flush()
        return category

    async def set_path(self, category: Category, path: Ltree) -> Category:
        category.parents_tree = path
        await self._session.flush()
        return category

    async def get(self, category_id: int) -> Category | None:
        return await self._session.get(Category, category_id)

    async def list_for_book(self, book_id: int, include_archived: bool = False) -> list[Category]:
        """Ordered by path, which yields depth-first tree order (a parent's path is a prefix of
        each child's, so parents always precede their subtree)."""
        stmt = select(Category).where(Category.book_id == book_id)
        if not include_archived:
            stmt = stmt.where(Category.archived.is_(False))
        result = await self._session.execute(stmt.order_by(Category.parents_tree))
        return list(result.scalars().all())

    async def update(
        self,
        category_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        archived: bool | None = None,
    ) -> Category | None:
        category = await self._session.get(Category, category_id)
        if category is None:
            return None
        if name is not None:
            category.name = name
        if description is not None:
            category.description = description
        if archived is not None:
            category.archived = archived
        await self._session.flush()
        return category

    async def children_count(self, book_id: int, path: Ltree) -> int:
        """Descendants of `path`, excluding the node itself."""
        result = await self._session.execute(
            select(func.count())
            .select_from(Category)
            .where(
                Category.book_id == book_id,
                text("parents_tree <@ text2ltree(:path) AND parents_tree != text2ltree(:path)"),
            )
            .params(path=str(path))
        )
        return int(result.scalar_one() or 0)

    async def has_transactions(self, category_id: int) -> bool:
        result = await self._session.execute(
            select(func.count())
            .select_from(FxTransaction)
            .where(FxTransaction.category_id == category_id)
        )
        return (result.scalar_one() or 0) > 0

    async def move_subtree(
        self, book_id: int, category_id: int, old_path: Ltree, new_path: Ltree
    ) -> None:
        """D14 cascade: re-root the whole subtree. Strict descendants get their prefix swapped
        (new_path || the part below old_path); the node itself is set directly, because
        subpath(path, nlevel(path)) is an out-of-range offset in Postgres."""
        await self._session.execute(
            text(
                "UPDATE categories "
                "SET parents_tree = text2ltree(:new_path) "
                "    || subpath(parents_tree, nlevel(text2ltree(:old_path))) "
                "WHERE book_id = :book_id "
                "  AND parents_tree <@ text2ltree(:old_path) "
                "  AND parents_tree != text2ltree(:old_path)"
            ),
            {"new_path": str(new_path), "old_path": str(old_path), "book_id": book_id},
        )
        await self._session.execute(
            text("UPDATE categories SET parents_tree = text2ltree(:new_path) WHERE id = :id"),
            {"new_path": str(new_path), "id": category_id},
        )

    async def delete(self, category_id: int) -> None:
        await self._session.execute(delete(Category).where(Category.id == category_id))
