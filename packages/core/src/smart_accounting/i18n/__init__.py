# Bot-side Fluent translations + helpers.
# (Mini-App has its own copy under apps/miniapp/src/i18n.)
#
# Per plan §4.4 (M4):
#   - aiogram-i18n middleware reads users.language and selects between en/ and ru/ bundles.
#   - Public helper: get_bundle(lang: str) -> FluentBundle.
#   - CI step asserts en and ru main.ftl have identical key sets (no missing translations).
