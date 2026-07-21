# categories — hierarchical tagging via PostgreSQL ltree (D14). GIST(book_id, parents_tree).
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk, ltree_path


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index(
            "ix_categories_book_id_parents_tree",
            "book_id",
            "parents_tree",
            postgresql_using="gist",
        ),
    )

    id: Mapped[bigserial_pk]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    parents_tree: Mapped[ltree_path]  # materialized path e.g. 'Food.Lunch.Cafe'
    kind: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=income 1=expense 2=both
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
