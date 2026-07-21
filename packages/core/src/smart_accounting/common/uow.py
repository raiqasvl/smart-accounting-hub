# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Unit-of-Work wrapper around a single AsyncSession.
#
# The Dishka provider in ioc.py owns the session lifecycle (open + close). UoW owns the
# transaction boundary: `async with uow:` commits on success, rolls back on exception.
# Repositories accept a UoW and never manage transactions themselves; services compose
# multiple repository calls inside one UoW block.
from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession


class UoW:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def close(self) -> None:
        await self.session.close()

    async def __aenter__(self) -> UoW:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Close is owned by the Dishka provider, not here.
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
