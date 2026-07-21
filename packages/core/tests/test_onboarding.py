# Integration tests for the D21 onboarding transaction + the API auth service.
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_accounting.auth.jwt import JwtCodec, decode_token
from smart_accounting.common.uow import UoW
from smart_accounting.config import Settings
from smart_accounting.models import Book, BookMember, User
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.books import BooksRepo
from smart_accounting.repositories.users import UsersRepo
from smart_accounting.services.auth_service import AuthService
from smart_accounting.services.identity import TgIdentity
from smart_accounting.services.user_service import UserService

TEST_BOT_TOKEN = "123456:integration-test-bot-token"


def _make_user_service(session: AsyncSession) -> UserService:
    uow = UoW(session)
    return UserService(uow, UsersRepo(uow), BooksRepo(uow), BookMembersRepo(uow))


async def _count(session: AsyncSession, model: type, **filters: object) -> int:
    stmt = select(func.count()).select_from(model)
    for col, val in filters.items():
        stmt = stmt.where(getattr(model, col) == val)
    return (await session.execute(stmt)).scalar_one()


async def test_new_identity_creates_user_book_owner(db_session: AsyncSession) -> None:
    svc = _make_user_service(db_session)
    ident = TgIdentity(
        telegram_user_id=990000001,
        first_name="Ada",
        last_name=None,
        username="ada",
        language_code="en",
    )
    user, book = await svc.ensure_user_and_default_book(ident)

    assert user.telegram_user_id == 990000001
    assert user.language == "en"
    assert book.kind == 0
    assert book.base_currency_code == "USD"
    assert book.name == "Personal"
    assert book.role == 0  # OWNER

    assert await _count(db_session, User, telegram_user_id=990000001) == 1
    assert await _count(db_session, Book, owner_id=user.id) == 1
    assert await _count(db_session, BookMember, book_id=book.id, user_id=user.id) == 1


async def test_repeat_call_is_idempotent(db_session: AsyncSession) -> None:
    svc = _make_user_service(db_session)
    ident = TgIdentity(
        telegram_user_id=990000002,
        first_name="Bo",
        last_name=None,
        username=None,
        language_code="en",
    )
    u1, b1 = await svc.ensure_user_and_default_book(ident)
    u2, b2 = await svc.ensure_user_and_default_book(ident)

    assert u1.id == u2.id
    assert b1.id == b2.id
    assert await _count(db_session, User, telegram_user_id=990000002) == 1
    assert await _count(db_session, Book, owner_id=u1.id) == 1


async def test_ru_defaults(db_session: AsyncSession) -> None:
    _, book = await _make_user_service(db_session).ensure_user_and_default_book(
        TgIdentity(990000003, "Ivan", None, "ivan", "ru")
    )
    assert book.base_currency_code == "RUB"
    assert book.name == "Личный"


async def test_uk_language_falls_back_to_en_currency_uah(db_session: AsyncSession) -> None:
    user, book = await _make_user_service(db_session).ensure_user_and_default_book(
        TgIdentity(990000004, "Taras", None, None, "uk")
    )
    assert user.language == "en"  # uk -> en (residual assert)
    assert book.base_currency_code == "UAH"  # but currency stays UAH


def _sign_init_data(user: dict[str, object], bot_token: str) -> str:
    fields = {"auth_date": str(int(time.time())), "user": json.dumps(user)}
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


async def test_auth_service_issues_valid_jwt(db_session: AsyncSession) -> None:
    settings = Settings(
        BOT_TOKEN=TEST_BOT_TOKEN,
        JWT_SECRET="test-jwt-secret-at-least-32-bytes-long!!",
    )
    codec = JwtCodec(settings.JWT_SECRET, settings.JWT_LIFETIME_SECONDS)
    auth = AuthService(_make_user_service(db_session), codec, settings)

    init_data = _sign_init_data(
        {"id": 990000005, "first_name": "Cy", "language_code": "en"}, TEST_BOT_TOKEN
    )
    token_out = await auth.authenticate(init_data)

    assert token_out.expires_in == settings.JWT_LIFETIME_SECONDS
    assert token_out.user.telegram_user_id == 990000005
    claims = decode_token(token_out.access_token, settings.JWT_SECRET)
    assert claims.user_id == token_out.user.id
    assert claims.book_id == token_out.book.id
    assert claims.role == token_out.book.role
