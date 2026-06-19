# Bot + Dispatcher singletons + dispatcher setup helpers.
#
# Per plan §1.5 (M1):
#   - Construct `bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))`.
#   - Construct `dp = Dispatcher(storage=storage)` where `storage` comes from `storage.py`
#     (Redis FSM with `with_destiny=True` for aiogram-dialog co-existence).
#   - Expose `setup_dispatcher(dp)` which wires Dishka middleware, includes routers,
#     registers dialogs, and calls aiogram-dialog's `setup_dialogs(dp)`.
#   - Expose `register_global_error_handler(dp)` that resets the dialog stack to a known
#     home state on any unhandled exception (pattern from AiogramBotTemplate bot/main.py:32-39).
#
# Singletons are imported by FastAPI's webhook route in M-future when we switch from polling.
