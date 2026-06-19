# FastAPI app entrypoint.
#
# Per plan §1.4 (M1) — this module:
#   - Constructs the FastAPI() instance with title, version, and the lifespan context manager.
#   - Builds the Dishka container from packages/core/ioc.py and registers it via
#     dishka.integrations.fastapi.setup_dishka(). The same container shape is reused by the bot.
#   - Mounts routers: health, auth, me. (M2 adds: books, invites, accounts, currencies.
#     M3 adds: transactions, reports. M4 adds: categories, transfers, export.)
#   - Adds CORS middleware allowing the Mini-App's Telegram-served origin.
#   - In the lifespan context: starts the FX-rate refresh asyncio task (M3, see fx/refresh.py)
#     and cancels it cleanly on shutdown.
#
# The `run()` function is exposed as a script entry point (see pyproject.toml [project.scripts]).
# In production, ops/compose.yml invokes uvicorn directly with --workers 2.
