# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Dishka providers — the DI graph shared by the api and bot processes.
#
# APP scope: Settings, AsyncEngine, sessionmaker (one per process).
# REQUEST scope: UoW (one session per request/update), plus repositories + services
# (registered in later phases as they are written).
#
# Consumed by api via dishka.integrations.fastapi.setup_dishka and by bot via
# dishka.integrations.aiogram.setup_dishka — see apps/*/main.py.
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.common.uow import UoW
from smart_accounting.config import Settings, get_config
from smart_accounting.database.engine import build_engine, build_session_factory
from smart_accounting.fx.clients import FrankfurterClient
from smart_accounting.repositories.accounts import AccountsRepo
from smart_accounting.repositories.book_invites import BookInvitesRepo
from smart_accounting.repositories.book_members import BookMembersRepo
from smart_accounting.repositories.books import BooksRepo
from smart_accounting.repositories.categories import CategoriesRepo
from smart_accounting.repositories.currencies import CurrenciesRepo
from smart_accounting.repositories.exchange_rates import ExchangeRatesRepo
from smart_accounting.repositories.reports import ReportsRepo
from smart_accounting.repositories.tg_chats import TgChatsRepo
from smart_accounting.repositories.transactions import TransactionsRepo
from smart_accounting.repositories.users import UsersRepo
from smart_accounting.services.account_service import AccountService
from smart_accounting.services.auth_service import AuthService
from smart_accounting.services.book_service import BookService
from smart_accounting.services.category_service import CategoryService
from smart_accounting.services.currency_service import CurrencyService
from smart_accounting.services.fx_service import FxService
from smart_accounting.services.invite_service import InviteService
from smart_accounting.services.report_service import ReportService
from smart_accounting.services.tg_chat_service import TgChatService
from smart_accounting.services.transaction_service import TransactionService
from smart_accounting.services.user_service import UserService


class DepsProvider(Provider):
    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        return get_config()

    @provide(scope=Scope.APP)
    def get_engine(self, settings: Settings) -> AsyncEngine:
        return build_engine(settings.POSTGRES_DSN)

    @provide(scope=Scope.APP)
    def get_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return build_session_factory(engine)

    @provide(scope=Scope.APP)
    def get_jwt_codec(self, settings: Settings) -> JwtCodec:
        return JwtCodec(settings.JWT_SECRET, settings.JWT_LIFETIME_SECONDS)

    @provide(scope=Scope.APP)
    async def get_http_client(self) -> AsyncIterator[httpx.AsyncClient]:
        # Shared pool for FX fetches; closed when the container tears down (app shutdown).
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield client

    @provide(scope=Scope.APP)
    def get_fx_client(self, http: httpx.AsyncClient, settings: Settings) -> FrankfurterClient:
        return FrankfurterClient(http, settings.FRANKFURTER_BASE_URL)

    @provide(scope=Scope.REQUEST)
    async def get_uow(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterator[UoW]:
        async with session_factory() as session:
            yield UoW(session)

    # Repositories + services (REQUEST scope; Dishka wires their constructor deps by type).
    users_repo = provide(UsersRepo, scope=Scope.REQUEST)
    books_repo = provide(BooksRepo, scope=Scope.REQUEST)
    members_repo = provide(BookMembersRepo, scope=Scope.REQUEST)
    invites_repo = provide(BookInvitesRepo, scope=Scope.REQUEST)
    accounts_repo = provide(AccountsRepo, scope=Scope.REQUEST)
    tg_chats_repo = provide(TgChatsRepo, scope=Scope.REQUEST)
    currencies_repo = provide(CurrenciesRepo, scope=Scope.REQUEST)
    categories_repo = provide(CategoriesRepo, scope=Scope.REQUEST)
    transactions_repo = provide(TransactionsRepo, scope=Scope.REQUEST)
    exchange_rates_repo = provide(ExchangeRatesRepo, scope=Scope.REQUEST)
    reports_repo = provide(ReportsRepo, scope=Scope.REQUEST)
    user_service = provide(UserService, scope=Scope.REQUEST)
    auth_service = provide(AuthService, scope=Scope.REQUEST)
    tg_chat_service = provide(TgChatService, scope=Scope.REQUEST)
    currency_service = provide(CurrencyService, scope=Scope.REQUEST)
    book_service = provide(BookService, scope=Scope.REQUEST)
    invite_service = provide(InviteService, scope=Scope.REQUEST)
    account_service = provide(AccountService, scope=Scope.REQUEST)
    transaction_service = provide(TransactionService, scope=Scope.REQUEST)
    report_service = provide(ReportService, scope=Scope.REQUEST)
    fx_service = provide(FxService, scope=Scope.REQUEST)
    category_service = provide(CategoryService, scope=Scope.REQUEST)


def build_container() -> AsyncContainer:
    """Build the process-wide async DI container from DepsProvider."""
    return make_async_container(DepsProvider())
