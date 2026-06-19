# Entry point — `python -m smart_accounting_bot` boots polling.
#
# Per plan §1.5 (M1):
#   1. Configure observability (structlog + Sentry) once.
#   2. Build the Dishka async container from packages/core.ioc.DepsProvider().
#   3. setup_dishka(container=container, router=dp).
#   4. dp.include_router(commands_router).
#   5. register_dialogs(dp).            # add every aiogram-dialog Dialog (M2: CreateBookDialog,
#                                       # JoinViaInviteDialog, CreateAccountDialog; M3: RecordTradeDialog,
#                                       # InternalTransferDialog (M4))
#   6. setup_dialogs(dp).
#   7. await dp.start_polling(bot, skip_updates=True)
#
# The boot sequence above is lifted verbatim from research/AiogramBotTemplate/bot/main.py:42-58
# (MIT, Artur Boyun 2024). See THIRD_PARTY_NOTICES.md.
