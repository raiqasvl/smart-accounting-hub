# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Bot + Dispatcher construction. Factory functions (not import-time singletons) so importing
# this module never touches the network or requires a valid BOT_TOKEN.
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from smart_accounting.config import get_config

from .handlers import commands
from .i18n import build_i18n_middleware
from .storage import build_storage


def build_bot() -> Bot:
    settings = get_config()
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher() -> Dispatcher:
    return Dispatcher(storage=build_storage())


def setup_dispatcher(dp: Dispatcher) -> None:
    """Include routers and the Fluent i18n middleware. (aiogram-dialog scenes land in M2.)"""
    dp.include_router(commands.router)
    build_i18n_middleware().setup(dispatcher=dp)
