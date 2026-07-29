# The EN and RU Fluent catalogues must stay key-for-key identical, so a user on either locale never
# falls through to a raw message id.
from __future__ import annotations

import re
from pathlib import Path

import smart_accounting

_I18N_ROOT = Path(smart_accounting.__file__).resolve().parent / "i18n"
_MESSAGE = re.compile(r"^([a-zA-Z][\w-]*)\s*=", re.MULTILINE)


def _keys(locale: str) -> set[str]:
    text = (_I18N_ROOT / locale / "main.ftl").read_text(encoding="utf-8")
    return set(_MESSAGE.findall(text))


def test_en_and_ru_have_identical_key_sets() -> None:
    en, ru = _keys("en"), _keys("ru")
    assert en, "the English catalogue should not be empty"
    assert en - ru == set(), f"missing Russian translations: {sorted(en - ru)}"
    assert ru - en == set(), f"Russian keys with no English source: {sorted(ru - en)}"


def test_no_placeholder_ftl_values() -> None:
    for locale in ("en", "ru"):
        text = (_I18N_ROOT / locale / "main.ftl").read_text(encoding="utf-8")
        for line in text.splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                value = line.split("=", 1)[1].strip()
                assert value, f"{locale}: empty value on line: {line!r}"
                assert "TODO" not in value, f"{locale}: untranslated placeholder: {line!r}"
