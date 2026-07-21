# Shared pytest fixtures for the bot test suite.
#
# The command router and the aiogram-dialog Dialog objects are module-level singletons, so a given
# instance can only be attached to one Dispatcher at a time. Any test that builds its own
# Dispatcher (the end-to-end dispatch tests) leaves them attached; this autouse fixture detaches
# them afterwards so the next test can re-include them into a fresh Dispatcher.
from __future__ import annotations

from collections.abc import Iterator

import pytest

from smart_accounting_bot.dialogs import all_dialogs
from smart_accounting_bot.handlers import commands


@pytest.fixture(autouse=True)
def _detach_singleton_routers() -> Iterator[None]:
    yield
    for router in (commands.router, *all_dialogs()):
        router._parent_router = None
