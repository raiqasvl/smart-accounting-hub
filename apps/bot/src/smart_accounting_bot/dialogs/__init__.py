# aiogram-dialog Dialog registrations.
#
# Per plan §2.2/§2.5/§3.5/§4.1 (M2-M4):
#   - create_book_dialog        (M2) Name → Kind → BaseCurrency → Confirm
#   - join_via_invite_dialog    (M2) AcceptRole → Done
#   - create_account_dialog     (M2) CurrencyPicker → KindPicker → Name → OpeningBalance → Confirm
#   - book_picker_dialog        (M2) Select from user's books
#   - record_trade_dialog       (M3) Direction → BaseCurrency → QuoteCurrency → BaseAccount → QuoteAccount
#                                    → AmountQuote → Rate → OccurredAt → Note → Confirm
#   - internal_transfer_dialog  (M4) FromAccount → ToAccount → Amount → Note → Confirm
#   - language_picker_dialog    (M2) en | ru
#
# Public function: `register_dialogs(dp: Dispatcher)` includes every Dialog on the Dispatcher.
