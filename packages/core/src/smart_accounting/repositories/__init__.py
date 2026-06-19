# Repository layer — async SQLAlchemy queries grouped by aggregate root.
#
# Per plan layering:
#   models   ← repositories ← services ← (api router | bot handler) ← UI
#
# One file per aggregate. Repositories are stateless beyond the AsyncSession they hold;
# they DON'T own transactions (that's UoW's job). They DON'T enforce permissions
# (that's services + RBAC's job). They just shape SQL.
#
# Files added across milestones:
#   M1: users.py, tg_chats.py, books.py
#   M2: book_members.py, book_invites.py, currencies.py, accounts.py
#   M3: fx_transactions.py, exchange_rates.py, reports.py
#   M4: categories.py
#   M5: (no new repos — security/ops pass only)
