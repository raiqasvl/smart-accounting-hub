#!/usr/bin/env python3
"""Fail if translated text is hardcoded in the presentation layers.

All user-facing copy belongs in a catalogue:
  * bot      -> packages/core/src/smart_accounting/i18n/{en,ru}/main.ftl
  * Mini-App -> apps/miniapp/src/lib/strings.ts

This scans for characters in the Cyrillic Unicode block (U+0400-U+04FF). A byte-oriented grep
over a Cyrillic character range cannot do this reliably — it also matches typographic punctuation
such as em dashes and arrows — hence a real Unicode check.

Exemptions: the catalogues themselves, plus the bot's command menu, because Telegram's
set_my_commands takes literal per-language strings rather than a runtime translation context.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = (ROOT / "apps/bot/src", ROOT / "apps/miniapp/src")
SUFFIXES = {".py", ".ts", ".tsx"}
EXEMPT = (
    "apps/bot/src/smart_accounting_bot/menu.py",
    "apps/miniapp/src/lib/strings.ts",
    "apps/miniapp/src/lib/strings.test.ts",
)


def is_cyrillic(char: str) -> bool:
    return "Ѐ" <= char <= "ӿ"


def main() -> int:
    offenders: list[str] = []
    for directory in SCAN_DIRS:
        for path in sorted(directory.rglob("*")):
            if path.suffix not in SUFFIXES or not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in EXEMPT:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if any(is_cyrillic(ch) for ch in line):
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")

    if offenders:
        print("Hardcoded translations found outside the i18n catalogues:\n")
        for offender in offenders:
            print(f"  {offender}")
        print("\nMove the text into main.ftl (bot) or strings.ts (Mini-App).")
        return 1

    print("i18n-check: no hardcoded translations outside the catalogues")
    return 0


if __name__ == "__main__":
    sys.exit(main())
