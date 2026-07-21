# Pydantic v2 schemas — the wire-format contracts that cross the service boundary and travel
# over HTTP. Distinct from `models/` (SQLAlchemy ORM). Money-shaped fields use `Money` (money.py).
from .auth import AuthTelegramIn, MeOut, TokenOut
from .book import BookOut
from .errors import ErrorDetail, ErrorOut
from .user import UserOut

__all__ = [
    "AuthTelegramIn",
    "BookOut",
    "ErrorDetail",
    "ErrorOut",
    "MeOut",
    "TokenOut",
    "UserOut",
]
