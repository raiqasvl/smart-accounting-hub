# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Redis FSM storage for aiogram + aiogram-dialog.
#
# `with_destiny=True` is REQUIRED for aiogram-dialog to share storage cleanly with regular FSM.
# Redis is FSM-only at MVP — no caching, no rate limiting, no pub/sub.
from __future__ import annotations

from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage

from smart_accounting.config import get_config


def build_storage() -> RedisStorage:
    settings = get_config()
    key_builder = DefaultKeyBuilder(with_destiny=True)
    return RedisStorage.from_url(settings.REDIS_DSN, key_builder=key_builder)
