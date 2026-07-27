# Report DTOs. The headline weighted-average result (D16): SUM(amount_base) / SUM(amount_quote) over
# persisted fx_transactions for a (quote_currency, direction) within an optional period.
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .money import Money


class WeightedAvgReportOut(BaseModel):
    book_id: int
    quote_currency_code: str
    direction: str  # buy | sell
    weighted_avg_rate: Money | None  # None when no matching trades
    sample_count: int
    sum_amount_quote: Money
    period_from: datetime | None
    period_to: datetime | None


class FxRateOut(BaseModel):
    # Informational rate hint (D16): base units per one quote unit, or None if unknown.
    base: str
    quote: str
    rate: Money | None
    source: str = "frankfurter"
