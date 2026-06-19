# Authentication surface — Mini-App auth flow (D12).
#
# Per plan §1.4 (M1):
#   - POST /auth/telegram
#       body: {init_data: str}            (raw initData string from Telegram WebApp SDK)
#       1. smart_accounting.auth.initdata.verify_init_data(init_data, BOT_TOKEN)
#          - validates the HMAC-SHA256 against BOT_TOKEN per Telegram WebApp spec
#          - rejects when auth_date older than 24h
#       2. Upsert users row keyed by telegram_user_id; capture first_name, last_name, username, language.
#       3. If new user: auto-create a default personal book (kind=0, base_currency_code=user's locale → ₽/$/€ heuristic).
#       4. Issue a 30-min HS256 JWT with claims {sub, book_id, role, exp, iat, jti}.
#       5. Return {access_token, expires_in: 1800, user, book}.
#
# Refresh model: Mini-App re-posts fresh initData on focus events (no separate refresh-token endpoint).
#
# Bot uses a different auth path — `/start invite_<token>` deep-links call POST /invites/<token>/accept
# and the bot itself authenticates by Telegram update payload, not JWT. See apps/bot/handlers/.
