# Async SQLAlchemy engine + sessionmaker construction.
#
# Per plan §1.2 (M1, cherry-picked from research/AiogramBotTemplate/bot/database/db.py:1-9):
#
#   engine = create_async_engine(POSTGRES_DSN, pool_size=20, max_overflow=10, pool_pre_ping=True)
#   SessionFactory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False, autocommit=False)
#
# The engine is process-scoped (one per uvicorn worker, one for the bot process).
# `expire_on_commit=False` keeps ORM objects usable after commit — cheaper than re-fetching.
