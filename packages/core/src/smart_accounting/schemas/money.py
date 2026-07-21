# Q5/D23: money is a decimal STRING on the wire, Decimal in Python, NUMERIC(20,8) in the DB.
# The `Money` Annotated type is used by every money-shaped schema field. Repositories/services
# keep Decimal everywhere; only the schema layer touches the wire string format.
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema


def _parse_money(v: object) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (str, int)):
        try:
            return Decimal(v)
        except InvalidOperation as exc:
            raise ValueError("money must be a decimal string") from exc
    raise ValueError("money must be a decimal string or int")


def _serialize_money(v: Decimal) -> str:
    # `f` keeps the column scale's trailing zeros; callers quantize for display.
    return format(v, "f")


Money = Annotated[
    Decimal,
    BeforeValidator(_parse_money),
    PlainSerializer(_serialize_money, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "pattern": r"^-?\d+(\.\d+)?$"}),
]
