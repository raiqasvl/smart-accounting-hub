# Aggregator import for Alembic autogenerate.
#
# Every model MUST be imported here so `Base.metadata` sees it — Alembic's autogenerate scans
# `Base.metadata.tables`, and un-imported models are silently invisible.
from .account import Account
from .base import Base
from .book import Book
from .book_invite import BookInvite
from .book_member import BookMember
from .category import Category
from .currency import Currency
from .exchange_rate import ExchangeRate
from .fx_transaction import FxTransaction, TransactionDirection, TransactionKind
from .notifications_outbox import NotificationOutbox
from .tg_chat import TgChat
from .user import User

__all__ = [
    "Account",
    "Base",
    "Book",
    "BookInvite",
    "BookMember",
    "Category",
    "Currency",
    "ExchangeRate",
    "FxTransaction",
    "NotificationOutbox",
    "TgChat",
    "TransactionDirection",
    "TransactionKind",
    "User",
]
