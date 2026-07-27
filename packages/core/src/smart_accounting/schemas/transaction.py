# FX transaction DTOs. Money-shaped fields cross as decimal strings (D23). D16: the user-supplied
# `rate` is authoritative; `amount_base = amount_quote * rate` is computed server-side. Positivity is
# validated in the service (→ InvalidAmount / D24), keeping these wire schemas thin.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .money import Money


class TransactionCreateIn(BaseModel):
    direction: Literal["buy", "sell"]
    base_currency_code: str
    quote_currency_code: str
    amount_quote: Money
    rate: Money
    base_account_id: int | None = None
    quote_account_id: int | None = None
    fee: Money = Decimal("0")
    fee_currency_code: str | None = None
    occurred_at: datetime | None = None
    note: str | None = None
    idempotency_key: str | None = None


class TransactionPatchIn(BaseModel):
    amount_quote: Money | None = None
    rate: Money | None = None
    note: str | None = None
    occurred_at: datetime | None = None
    archived: bool | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    created_by_user_id: int
    kind: str  # plain_cash | internal_transfer | fx_conversion
    direction: str  # buy | sell
    base_currency_code: str
    quote_currency_code: str
    amount_quote: Money
    rate: Money
    amount_base: Money
    fee: Money
    fee_currency_code: str | None
    base_account_id: int | None
    quote_account_id: int | None
    occurred_at: datetime
    note: str | None
    archived: bool


class TransactionPage(BaseModel):
    # Cursor page (D25): opaque next_cursor over (occurred_at DESC, id DESC).
    items: list[TransactionOut]
    next_cursor: str | None
    has_more: bool
