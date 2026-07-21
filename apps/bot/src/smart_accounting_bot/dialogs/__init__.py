# aiogram-dialog Dialog registrations (M2 flows built; M3-M4 flows land later).
#
#   - create_book_dialog      (M2) Name → Kind → BaseCurrency → Confirm → Done
#   - create_account_dialog   (M2) Currency → Kind → Name → OpeningBalance → Confirm → Done
#   - join_invite_dialog      (M2) AcceptRole → Done
#   - books_menu_dialog       (M2) Select from the user's books → switch
#
# `all_dialogs()` returns the Dialog routers to include on the dispatcher. `setup_dialogs(dp)`
# (from aiogram_dialog) must ALSO be called once — see main.setup_dispatcher.
from __future__ import annotations

from aiogram_dialog import Dialog

from .books_menu import books_menu_dialog
from .create_account import create_account_dialog
from .create_book import create_book_dialog
from .join_invite import join_invite_dialog


def all_dialogs() -> list[Dialog]:
    return [
        create_book_dialog,
        create_account_dialog,
        join_invite_dialog,
        books_menu_dialog,
    ]


__all__ = ["all_dialogs"]
