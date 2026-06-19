# Aggregator import for Alembic autogenerate.
#
# Per plan §1.5 / migrations/env.py: every new model file MUST be imported here so that
# `Base.metadata` sees it. Alembic's autogenerate scans `Base.metadata.tables` — un-imported
# models are silently invisible and would produce empty migrations.
#
# Eleven models in v1.0 base migration:
#   from .user import User
#   from .tg_chat import TgChat
#   from .book import Book
#   from .book_member import BookMember
#   from .book_invite import BookInvite
#   from .currency import Currency
#   from .account import Account
#   from .category import Category
#   from .exchange_rate import ExchangeRate
#   from .fx_transaction import FxTransaction
#   from .notifications_outbox import NotificationOutbox
