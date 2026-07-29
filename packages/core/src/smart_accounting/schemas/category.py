# Category DTOs. `parents_tree` is the materialized ltree path rendered as a string (D14); its
# labels are the ancestor ids ending with the node's own id, so renames never touch paths.
# `depth` is the label count (1 = root), which the UI uses to indent the tree.
from __future__ import annotations

from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    book_id: int
    parents_tree: str
    depth: int
    kind: int  # 0=income 1=expense 2=both
    name: str
    description: str | None
    archived: bool


class CategoryCreateIn(BaseModel):
    name: str
    kind: int = 1
    parent_id: int | None = None
    description: str | None = None


class CategoryPatchIn(BaseModel):
    name: str | None = None
    description: str | None = None
    archived: bool | None = None


class CategoryMoveIn(BaseModel):
    # null re-parents to the root. Move is its own endpoint so "no parent" is unambiguous.
    parent_id: int | None = None
