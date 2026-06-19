# accounts — places where money sits. Cash, bank, card, brokerage.
# Each account is denominated in exactly one currency (fx happens between accounts).
#
# Per plan §1.3 (M1) and §2.5 (M2):
#   id BIGSERIAL PRIMARY KEY
#   book_id BIGINT NOT NULL FK → books(id)
#   currency_code TEXT NOT NULL                      # not a FK to currencies(code) because per-book overrides
#                                                    # complicate the constraint; service-layer validates instead
#   name TEXT NOT NULL
#   kind SMALLINT NOT NULL                           # 0=cash, 1=bank, 2=card, 3=brokerage, 4=other
#   archived BOOLEAN NOT NULL DEFAULT FALSE
#   opening_balance NUMERIC(20,8) NOT NULL DEFAULT 0  # D5 precision contract
#   created_at, updated_at
#
# Computed balance = opening_balance + signed sum of FxTransaction deltas where
# this account appears as base_account_id (debit/credit per direction) or quote_account_id.
# Computed on the fly in M3; cached only if profiling demands it.
