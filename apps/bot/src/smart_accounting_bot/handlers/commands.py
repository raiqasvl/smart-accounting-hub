# Top-level command + deep-link handlers.
#
# Per plan §1.5 (M1) and §2.3 / §3.5 (M2/M3 additions):
#
# M1:
#   - /start           Upserts users + tg_chats rows. If a default book doesn't exist, auto-create one
#                      (kind=personal, base_currency=user's locale heuristic). Sends rolling main message
#                      with a WebAppInfo button to launch the Mini-App.
#   - /start invite_<token>
#                      Deep-link from a book invite. Validates token via smart_accounting.services.invites,
#                      prompts the user to accept the role, then accepts and switches active book.
#
# M2:
#   - /books           Opens BookPickerDialog — user selects active book; tg_chats.active_book_id updated;
#                      bot's rolling main message re-renders to show the new book's dashboard.
#   - /lang            Opens LanguagePickerDialog — sets users.language (en/ru); UI re-renders in new locale.
#
# M3:
#   - /avg             Opens an aiogram-dialog quick-flow: Direction → QuoteCurrency → DateRange.
#                      Calls smart_accounting.repositories.reports.weighted_avg_rate() and shows the result inline.
#   - /trade           Shortcut to RecordTradeDialog (defined in dialogs/record_trade.py).
#
# All handlers gate on book-membership role via the RBAC dep from smart_accounting.auth.rbac.
# All user-visible strings load from i18n/{en,ru}/main.ftl via the Fluent middleware.
