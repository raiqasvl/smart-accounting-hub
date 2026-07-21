# Auth request/response DTOs.
from __future__ import annotations

from pydantic import BaseModel

from .book import BookOut
from .user import UserOut


class AuthTelegramIn(BaseModel):
    init_data: str


class TokenOut(BaseModel):
    access_token: str
    expires_in: int
    user: UserOut
    book: BookOut


class MeOut(BaseModel):
    user: UserOut
    active_book: BookOut
    role: int
    books: list[BookOut]
