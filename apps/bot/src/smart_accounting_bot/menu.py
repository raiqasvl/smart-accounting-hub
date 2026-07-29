# The bot command menu (the "/" list in Telegram clients). Registered once at startup via
# set_my_commands so commands are discoverable — closes the M2 "commands are hidden" gap.
from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

_COMMANDS_EN: list[BotCommand] = [
    BotCommand(command="start", description="Open the app"),
    BotCommand(command="trade", description="Record an FX trade"),
    BotCommand(command="avg", description="Weighted-average rate"),
    BotCommand(command="transfer", description="Move money between accounts"),
    BotCommand(command="books", description="Switch book"),
    BotCommand(command="newbook", description="Create a book"),
    BotCommand(command="newaccount", description="Create an account"),
]

_COMMANDS_RU: list[BotCommand] = [
    BotCommand(command="start", description="Открыть приложение"),
    BotCommand(command="trade", description="Записать валютную сделку"),
    BotCommand(command="avg", description="Средневзвешенный курс"),
    BotCommand(command="transfer", description="Перевод между счетами"),
    BotCommand(command="books", description="Сменить книгу"),
    BotCommand(command="newbook", description="Создать книгу"),
    BotCommand(command="newaccount", description="Создать счёт"),
]


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(_COMMANDS_EN, scope=BotCommandScopeDefault())
    await bot.set_my_commands(_COMMANDS_RU, scope=BotCommandScopeDefault(), language_code="ru")
