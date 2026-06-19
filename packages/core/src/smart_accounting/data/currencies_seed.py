# System currency catalogue — seeded by `0002_seed_currencies.py` data migration.
#
# Per plan §2.4 (M2):
#   ~40 fiat currencies (ISO 4217 majors)
#   5 crypto currencies (BTC, ETH, USDT, USDC, BNB)
#
# Each entry: {code, symbol, decimals, kind}.
#   - kind 0 = fiat (decimals 2 unless JPY/KRW = 0)
#   - kind 1 = crypto (decimals 8 for BTC, 6 for ERC-20 stablecoins)
#   - kind 2 = metal (XAU/XAG, decimals 4)
#
# Idempotent seeding: data migration uses `INSERT ... ON CONFLICT (book_id, code) DO NOTHING`
# so re-running is safe and a v1.1 update can extend the list without touching existing rows.
#
# All seed rows have `book_id IS NULL` — they are the system catalogue. Per-book overrides
# get inserted with the book's id.
