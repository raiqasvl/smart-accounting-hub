# Account DTOs. opening_balance is the product's first money-shaped field (decimal string wire).
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .money import Money


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    currency_code: str
    name: str
    kind: int  # 0=cash 1=bank 2=card 3=brokerage 4=other
    archived: bool
    opening_balance: Money


class AccountCreateIn(BaseModel):
    currency_code: str
    name: str
    kind: int
    opening_balance: Money = Decimal("0")


class AccountPatchIn(BaseModel):
    name: str | None = None
    archived: bool | None = None
