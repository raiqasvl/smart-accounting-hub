# English Fluent translations for the Mini-App.
#
# Per plan §4.4 (M4):
#   - One Fluent .ftl file per locale, namespaced by surface (common, books, trades, reports, ...).
#   - Keys must match between en/ and ru/ — CI step `pytest tests/i18n/test_fluent_keys.py` enforces.
#   - Every string introduced in M1-M4 lands here in EN; RU lands as part of M4.
#
# Example shape (filled in during M1+):
#   greeting = Hello, { $name }
#   book-card-empty = You're not in any book yet.
