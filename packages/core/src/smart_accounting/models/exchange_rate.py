# exchange_rates — historical FX rates fetched from external providers.
#
# Per plan §1.3 (M1) and §3.1 (M3 fetcher):
#   id BIGSERIAL PRIMARY KEY
#   base_currency_code TEXT NOT NULL                 # e.g. 'USD'
#   quote_currency_code TEXT NOT NULL                # e.g. 'RUB'
#   rate NUMERIC(20,8) NOT NULL                      # 1 base = `rate` quote
#   source TEXT NOT NULL                             # 'frankfurter' at MVP; 'coingecko'/'ecb-direct' later
#   fetched_at TIMESTAMPTZ NOT NULL                  # when WE got the rate, not the upstream's "as of" time
#
# Constraints:
#   UNIQUE (base_currency_code, quote_currency_code, source, fetched_at)
# Indexes:
#   (base_currency_code, quote_currency_code, fetched_at DESC)
#                                                    # for "give me the latest rate for USD→RUB"
#
# D16: this table is INFORMATIONAL ONLY. The weighted-avg query reads from fx_transactions,
# not from here. exchange_rates seeds the bot's "current rate hint" in RecordTradeDialog.
