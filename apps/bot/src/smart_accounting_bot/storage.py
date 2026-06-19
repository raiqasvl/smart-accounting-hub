# Redis FSM storage for aiogram + aiogram-dialog.
#
# Per plan §4.5 / cherry-pick from research/AiogramBotTemplate/bot/misc.py:12-13:
#
#   key_builder = DefaultKeyBuilder(with_destiny=True)
#   storage = RedisStorage.from_url(str(config.REDIS_DSN), key_builder=key_builder)
#
# `with_destiny=True` is REQUIRED for aiogram-dialog to share storage cleanly with regular FSM.
# Do not change it without updating aiogram-dialog's stack/context handling.
#
# Redis is FSM-only at MVP — no caching, no rate limiting, no pub/sub.
