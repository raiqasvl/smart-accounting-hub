# External FX rate provider clients. D16: these feed exchange_rates (informational rate hints),
# never the weighted-average (which reads persisted fx_transactions).
#
# MVP: FrankfurterClient only (free, ECB-backed, no API key, ~30 fiat quote codes). v1.1+ may add
# CoinGecko (crypto), OpenExchangeRates (paid), ECB-direct (fallback). All clients accept a shared
# httpx.AsyncClient (Dishka APP scope) so the connection pool is reused across fetches.
from __future__ import annotations

from decimal import Decimal
from typing import Protocol

import httpx


class FxClient(Protocol):
    async def fetch_latest(self, base: str) -> dict[str, Decimal]:
        """Return {quote_code: rate} where rate is quote units per one `base` unit."""
        ...


class FrankfurterClient:
    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")

    async def fetch_latest(self, base: str) -> dict[str, Decimal]:
        resp = await self._http.get(f"{self._base_url}/latest", params={"base": base})
        resp.raise_for_status()
        payload = resp.json()
        rates: dict[str, object] = payload.get("rates", {})
        return {code: Decimal(str(value)) for code, value in rates.items()}
