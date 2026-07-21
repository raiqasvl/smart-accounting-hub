# Bot i18n wiring: a Fluent core over packages/core's en/ru catalogues + a locale manager that
# picks ru for Russian-speaking users and en for everyone else (matches services.pick_language;
# uk falls back to en). Language switching (a DB-backed manager) lands in M2 with /lang.
from __future__ import annotations

from pathlib import Path
from typing import Any

from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentRuntimeCore
from aiogram_i18n.managers import BaseManager

import smart_accounting

# The i18n root is a pure data dir (locale subdirs only, no __init__.py) so the Fluent core's
# locale auto-discovery doesn't pick up a __pycache__.
_I18N_ROOT = Path(smart_accounting.__file__).resolve().parent / "i18n"


class TelegramLocaleManager(BaseManager):
    async def get_locale(self, *args: Any, **kwargs: Any) -> str:
        user = kwargs.get("event_from_user")
        code = getattr(user, "language_code", None)
        return "ru" if isinstance(code, str) and code.startswith("ru") else "en"

    async def set_locale(self, *args: Any, **kwargs: Any) -> None:
        return None


def build_i18n_middleware() -> I18nMiddleware:
    core = FluentRuntimeCore(path=str(_I18N_ROOT / "{locale}"))
    return I18nMiddleware(core=core, manager=TelegramLocaleManager(), default_locale="en")
