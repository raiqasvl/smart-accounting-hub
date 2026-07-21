# BookOut — the book DTO. `role` is the calling user's role in this book (from book_members),
# supplied by the service; it is not a column on the books table.
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: int
    base_currency_code: str
    role: int
