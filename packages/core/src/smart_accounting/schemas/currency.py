# Currency DTOs. book_id NULL = system-catalogue row; non-NULL = per-book override.
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CurrencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int | None
    code: str
    symbol: str
    decimals: int
    kind: int  # 0=fiat 1=crypto 2=metal
    archived: bool


class CurrencyCreateIn(BaseModel):
    code: str
    symbol: str
    decimals: int
    kind: int = 0
