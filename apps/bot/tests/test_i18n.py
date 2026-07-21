# The M1 message set resolves in both en and ru, and the locale manager picks the right one.
from __future__ import annotations

from pathlib import Path

from aiogram_i18n.cores import FluentRuntimeCore

import smart_accounting
from smart_accounting_bot.i18n import TelegramLocaleManager

_M1_KEYS = ["start-welcome", "open-app-button", "card-greeting", "error-auth"]
_I18N_ROOT = Path(smart_accounting.__file__).resolve().parent / "i18n"


def _core() -> FluentRuntimeCore:
    core = FluentRuntimeCore(path=str(_I18N_ROOT / "{locale}"), default_locale="en")
    core.locales.update(core.find_locales())  # what startup() does, but sync
    return core


def test_all_m1_keys_resolve_in_en_and_ru() -> None:
    core = _core()
    for key in _M1_KEYS:
        en = core.get(key, "en", name="Ada", book="Personal")
        ru = core.get(key, "ru", name="Ada", book="Personal")
        assert en and ru
        assert en != ru  # the two locales are genuinely different strings


def test_start_welcome_is_english_vs_russian() -> None:
    core = _core()
    assert "Welcome" in core.get("start-welcome", "en", name="Ada")
    assert "Welcome" not in core.get("start-welcome", "ru", name="Ada")


async def test_locale_manager_maps_language_code() -> None:
    manager = TelegramLocaleManager()
    ru_user = type("U", (), {"language_code": "ru"})()
    uk_user = type("U", (), {"language_code": "uk"})()
    en_user = type("U", (), {"language_code": "en"})()
    assert await manager.get_locale(event_from_user=ru_user) == "ru"
    assert await manager.get_locale(event_from_user=uk_user) == "en"  # uk -> en
    assert await manager.get_locale(event_from_user=en_user) == "en"
    assert await manager.get_locale(event_from_user=None) == "en"
