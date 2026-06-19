# Async-aware Alembic env.
#
# Per plan §1.2 (M1, cherry-picked verbatim from research/AiogramBotTemplate/migrations/env.py):
#   - Imports every model module from smart_accounting.models.* so that Base.metadata sees
#     all tables. THIS IS THE EXTENSION POINT — every new model gets one import line here.
#   - target_metadata = Base.metadata
#   - Reads DSN at runtime from smart_accounting.config.get_config().POSTGRES_DSN.
#   - run_migrations_online() uses asyncio.run(run_async_migrations()).
#   - run_async_migrations uses async_engine_from_config(... poolclass=NullPool).
#
# Offline mode is supported but unused at MVP — we always migrate against a live DB.
