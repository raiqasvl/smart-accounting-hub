# The Money wire type: decimal string in/out with full precision, string in JSON schema.
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from smart_accounting.schemas.money import Money


class _M(BaseModel):
    amount: Money


def test_round_trip_preserves_trailing_zeros() -> None:
    m = _M(amount="90.27000000")
    assert m.amount == Decimal("90.27000000")
    assert m.model_dump(mode="json")["amount"] == "90.27000000"


def test_accepts_int_and_decimal() -> None:
    assert _M(amount=5).amount == Decimal("5")
    assert _M(amount=Decimal("1.5")).amount == Decimal("1.5")


def test_rejects_non_numeric() -> None:
    with pytest.raises(ValidationError):
        _M(amount="not-a-number")


def test_json_schema_is_string() -> None:
    prop = _M.model_json_schema()["properties"]["amount"]
    assert prop["type"] == "string"
