# External FX rate provider clients.
#
# Per plan §3.1 (M3):
#   - FxClient (Protocol)               base class: fetch_latest(base: str) -> dict[str, Decimal]
#   - FrankfurterClient                 https://api.frankfurter.dev/v1/latest?base=USD
#                                       Free, ECB-backed, no API key, ~150 quote codes.
#                                       Single client at MVP — this is enough.
#
# v1.1+ additions (NOT v1.0):
#   - CoinGeckoClient                   for crypto rates
#   - OpenExchangeRatesClient           paid, more granular (1-min cadence)
#   - EcbDirectClient                   official ECB XML endpoint as a fallback
#
# All clients accept an httpx.AsyncClient via constructor — Dishka provides one shared client
# from APP scope so connection pooling is reused across many fetches.
