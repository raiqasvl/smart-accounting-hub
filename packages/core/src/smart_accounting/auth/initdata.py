# Telegram WebApp initData HMAC verification.
#
# Per plan §1.4 (M1) and Telegram WebApp spec:
#   <https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app>
#
# Public function:
#   verify_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict
#     1. Parse `init_data` as application/x-www-form-urlencoded.
#     2. Extract and remove `hash` field.
#     3. Build the data-check-string: sorted(k=v) joined with `\n`.
#     4. secret_key = HMAC_SHA256(key=b"WebAppData", msg=bot_token.encode())
#     5. expected_hash = HMAC_SHA256(key=secret_key, msg=data_check_string).hexdigest()
#     6. constant-time compare; reject if mismatch (raise InitDataInvalid).
#     7. Reject if `auth_date` older than `max_age_seconds` (raise InitDataExpired).
#     8. Return parsed dict {user, query_id, chat, auth_date, ...}.
#
# Property-based tests in M5 with hypothesis cover: tampered hash, off-by-one bytes, expired
# auth_date, missing fields, non-UTF8 user names, ordering of fields, double `hash` keys.
