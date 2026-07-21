# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Async SQLAlchemy engine + sessionmaker construction.
#
# The engine is process-scoped (one per uvicorn worker, one for the bot process); the Dishka
# APP-scope provider in ioc.py holds the single instance. `expire_on_commit=False` keeps ORM
# objects usable after commit — cheaper than re-fetching.
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(dsn: str) -> AsyncEngine:
    return create_async_engine(
        dsn,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )
