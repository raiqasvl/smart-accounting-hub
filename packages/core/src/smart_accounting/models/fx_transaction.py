# fx_transactions — the headline table. Single fx trade or one leg of a multi-leg movement.
#
# Per plan §1.3 (M1) and §3 (M3 — service + API + bot dialog + Mini-App report):
#
#   id BIGSERIAL PRIMARY KEY
#   book_id BIGINT NOT NULL FK → books(id)
#   created_by_user_id BIGINT NOT NULL FK → users(id)        # audit: who recorded it
#   kind transaction_kind NOT NULL DEFAULT 'plain_cash'      # ENUM: 'plain_cash' | 'internal_transfer' | 'fx_conversion'
#   direction transaction_direction NOT NULL                 # ENUM: 'buy' | 'sell'   (relative to base)
#   base_account_id BIGINT NULL FK → accounts(id)            # debited on sell, credited on buy
#   quote_account_id BIGINT NULL FK → accounts(id)           # the other side; same currency as quote_currency_code
#   base_currency_code TEXT NOT NULL                         # the currency BEING traded
#   quote_currency_code TEXT NOT NULL                        # the currency we measure base in
#   amount_quote NUMERIC(20,8) NOT NULL                      # how much we got/paid in quote currency
#   rate NUMERIC(20,8) NOT NULL                              # quote per base; user-supplied (D16)
#   amount_base NUMERIC(20,8) NOT NULL                       # = amount_quote * rate (denormalised for fast aggregates)
#   fee NUMERIC(20,8) NOT NULL DEFAULT 0
#   fee_currency_code TEXT NULL                              # NULL ⇒ no fee
#   occurred_at TIMESTAMPTZ NOT NULL                         # when the trade actually happened (not when recorded)
#   note TEXT NULL
#   source TEXT NULL                                         # 'manual' (MVP), 'csv-import' (v1.1)
#   category_id BIGINT NULL FK → categories(id)
#   linked_transaction_id BIGINT NULL FK → fx_transactions(id)  # second leg of internal_transfer / fx_conversion
#   archived BOOLEAN NOT NULL DEFAULT FALSE
#   created_at, updated_at
#
# Indexes (for the headline query):
#   (book_id, quote_currency_code, direction, occurred_at DESC)
#   (book_id, occurred_at DESC)
#   linked_transaction_id WHERE linked_transaction_id IS NOT NULL  (partial)
#
# D16 invariant: the row's `(amount_quote, rate, amount_base)` is the source of truth.
# The weighted-average query is `SUM(amount_quote * rate) / SUM(amount_quote)` = SUM(amount_base) / SUM(amount_quote).
