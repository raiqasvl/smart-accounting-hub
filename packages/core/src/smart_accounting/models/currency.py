# currencies — ISO 4217 fiat + crypto + metals catalogue, with per-book overrides.
#
# Per plan §1.3 (M1) and §2.4 (M2 seed):
#   id BIGSERIAL PRIMARY KEY
#   book_id BIGINT NULL FK → books(id)               # NULL ⇒ system-catalogue row; non-NULL ⇒ book override
#   code TEXT NOT NULL                               # 'USD', 'EUR', 'BTC', 'XAU' (ISO 4217 + crypto)
#   symbol TEXT NOT NULL                             # '$', '€', '₿', 'Au'
#   decimals SMALLINT NOT NULL                       # 2 for fiat, 8 for crypto, 4 for metals
#   kind SMALLINT NOT NULL DEFAULT 0                 # 0=fiat, 1=crypto, 2=metal
#   archived BOOLEAN NOT NULL DEFAULT FALSE
#   created_at, updated_at
#   UNIQUE (book_id, code)                           # one row per (book, code); system has book_id IS NULL
#
# Read pattern: WHERE book_id IS NULL OR book_id = $book_id  (FinWave's pattern adapted to books).
# Seeded by data migration `0002_seed_currencies.py` from data/currencies_seed.py.
