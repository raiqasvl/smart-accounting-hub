# Pydantic-settings shape — single source of truth for runtime config.
# Read once via @lru_cache get_config(); both api and bot processes consume it.
#
# Per plan §1.4 / §1.10 / §4.5 — env var list mirrors `.env.example`:
#   DOMAIN, ENVIRONMENT, DEBUG
#   BOT_TOKEN, BOT_USERNAME
#   JWT_SECRET, JWT_LIFETIME_SECONDS                          (D12: 1800 default)
#   POSTGRES_DSN
#   REDIS_DSN
#   SENTRY_DSN, LOG_LEVEL                                     (D17)
#   FRANKFURTER_BASE_URL, FX_REFRESH_INTERVAL_SECONDS         (M3)
#   RESTIC_REPOSITORY, RESTIC_PASSWORD, B2_ACCOUNT_ID, B2_ACCOUNT_KEY  (D18)
#   NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_BOT_USERNAME        (Mini-App; read by Next.js, not Python)
#
# Pattern lifted from research/AiogramBotTemplate/bot/config.py (MIT, Artur Boyun 2024).
