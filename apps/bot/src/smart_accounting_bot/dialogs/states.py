# aiogram-dialog state groups for the M2 bot flows. One StatesGroup per dialog.
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CreateBook(StatesGroup):
    name = State()
    kind = State()
    currency = State()
    confirm = State()
    done = State()


class CreateAccount(StatesGroup):
    currency = State()
    kind = State()
    name = State()
    opening = State()
    confirm = State()
    done = State()


class JoinInvite(StatesGroup):
    confirm = State()
    done = State()


class BooksMenu(StatesGroup):
    choose = State()
    done = State()


class RecordTrade(StatesGroup):
    direction = State()
    quote = State()
    amount = State()
    rate = State()
    confirm = State()
    done = State()


class AvgReport(StatesGroup):
    direction = State()
    quote = State()
    period = State()
    result = State()
