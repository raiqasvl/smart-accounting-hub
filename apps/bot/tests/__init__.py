# Tests for the bot. Per plan Testing Strategy:
#   - aiogram has a test utility (Bot.session.middleware) we use to simulate updates.
#   - Coverage targets: /start, /avg, dialog happy paths, deep-link invite acceptance,
#     RBAC denial paths, single-rolling-message edit semantics.
