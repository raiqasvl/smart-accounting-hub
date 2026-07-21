# System currency catalogue (book_id IS NULL), seeded idempotently by 0002_seed_currencies.
# Each entry: code, symbol, decimals, kind (0=fiat, 1=crypto, 2=metal).
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrencySeed:
    code: str
    symbol: str
    decimals: int
    kind: int


_FIAT: list[CurrencySeed] = [
    CurrencySeed("USD", "$", 2, 0),
    CurrencySeed("EUR", "€", 2, 0),
    CurrencySeed("GBP", "£", 2, 0),
    CurrencySeed("JPY", "¥", 0, 0),
    CurrencySeed("CHF", "Fr", 2, 0),
    CurrencySeed("CAD", "$", 2, 0),
    CurrencySeed("AUD", "$", 2, 0),
    CurrencySeed("NZD", "$", 2, 0),
    CurrencySeed("CNY", "¥", 2, 0),
    CurrencySeed("HKD", "$", 2, 0),
    CurrencySeed("SGD", "$", 2, 0),
    CurrencySeed("SEK", "kr", 2, 0),
    CurrencySeed("NOK", "kr", 2, 0),
    CurrencySeed("DKK", "kr", 2, 0),
    CurrencySeed("PLN", "zł", 2, 0),
    CurrencySeed("CZK", "Kč", 2, 0),
    CurrencySeed("HUF", "Ft", 2, 0),
    CurrencySeed("RON", "lei", 2, 0),
    CurrencySeed("BGN", "лв", 2, 0),
    CurrencySeed("TRY", "₺", 2, 0),
    CurrencySeed("RUB", "₽", 2, 0),
    CurrencySeed("UAH", "₴", 2, 0),
    CurrencySeed("KZT", "₸", 2, 0),
    CurrencySeed("GEL", "₾", 2, 0),
    CurrencySeed("AMD", "֏", 2, 0),
    CurrencySeed("AZN", "₼", 2, 0),
    CurrencySeed("INR", "₹", 2, 0),
    CurrencySeed("IDR", "Rp", 2, 0),
    CurrencySeed("KRW", "₩", 0, 0),
    CurrencySeed("THB", "฿", 2, 0),
    CurrencySeed("MYR", "RM", 2, 0),
    CurrencySeed("PHP", "₱", 2, 0),
    CurrencySeed("VND", "₫", 0, 0),
    CurrencySeed("ZAR", "R", 2, 0),
    CurrencySeed("BRL", "R$", 2, 0),
    CurrencySeed("MXN", "$", 2, 0),
    CurrencySeed("AED", "AED", 2, 0),
    CurrencySeed("SAR", "SAR", 2, 0),
    CurrencySeed("ILS", "₪", 2, 0),
    CurrencySeed("NGN", "₦", 2, 0),
]

_METALS: list[CurrencySeed] = [
    CurrencySeed("XAU", "Au", 4, 2),
    CurrencySeed("XAG", "Ag", 4, 2),
]

_CRYPTO: list[CurrencySeed] = [
    CurrencySeed("BTC", "₿", 8, 1),
    CurrencySeed("ETH", "Ξ", 8, 1),
    CurrencySeed("USDT", "₮", 6, 1),
    CurrencySeed("USDC", "$", 6, 1),
    CurrencySeed("BNB", "BNB", 8, 1),
]

# 40 fiat + 2 metals + 5 crypto = 47 system currencies.
SEED_CURRENCIES: list[CurrencySeed] = [*_FIAT, *_METALS, *_CRYPTO]
