# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Entry point — `python -m smart_accounting_bot` boots polling.
from __future__ import annotations

import asyncio

from dishka.integrations.aiogram import setup_dishka

from smart_accounting.config import get_config
from smart_accounting.ioc import build_container
from smart_accounting.observability import configure_observability

from .main import build_bot, build_dispatcher, setup_dispatcher


async def _run() -> None:
    settings = get_config()
    configure_observability(
        sentry_dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
    )
    bot = build_bot()
    dp = build_dispatcher()
    setup_dispatcher(dp)
    setup_dishka(container=build_container(), router=dp)
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
