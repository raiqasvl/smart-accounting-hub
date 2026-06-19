# Q5-locked: Decimal-as-string serialisation for ALL money fields.
#
# Why string and not float / int-cents:
#   - JSON has no native decimal; floats lose precision past ~15 digits, which we cannot
#     accept in an accounting tool with NUMERIC(20,8) on the DB side.
#   - Stripe-style int-cents fails on mixed-decimals queries (BTC=8 + USD=2 in one report).
#   - Strings round-trip the full 20,8 precision.
#
# Public type: `Money`
#
# Pattern (filled in during M1 base scaffolding before the first endpoint lands):
#
#   from decimal import Decimal
#   from typing import Annotated
#   from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema
#
#   def _validate_money(v: object) -> Decimal:
#       if isinstance(v, Decimal): return v
#       if isinstance(v, (str, int)): return Decimal(v)
#       raise ValueError("money must be a string or int")
#
#   def _serialise_money(v: Decimal) -> str:
#       # `f` format keeps trailing zeros to match the column scale; downstream callers
#       # can quantize if they need fewer digits for display.
#       return format(v, "f")
#
#   Money = Annotated[
#       Decimal,
#       BeforeValidator(_validate_money),
#       PlainSerializer(_serialise_money, return_type=str, when_used="json"),
#       WithJsonSchema({"type": "string", "pattern": r"^-?\d+(\.\d+)?$"}),
#   ]
#
# Usage in any schema:
#
#   class TransactionCreate(BaseModel):
#       amount_quote: Money
#       rate: Money
#       fee: Money = Decimal("0")
#
# Repository code keeps `Decimal` everywhere (services + queries); only the schema-layer
# touches the wire format.
