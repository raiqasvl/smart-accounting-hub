# FastAPI app entrypoint.
#
# `create_app(container)` builds the app and wires health (bare paths), the /api/v1 router group
# (auth + me), the request-id middleware, the D24 error-envelope handler, and Dishka. The
# module-level `app = create_app()` is what uvicorn imports; tests pass a test container.
from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from smart_accounting.config import Settings, get_config
from smart_accounting.errors import AppError
from smart_accounting.fx.clients import FrankfurterClient
from smart_accounting.fx.refresh import refresh_loop
from smart_accounting.ioc import build_container
from smart_accounting.observability import configure_observability

from .routers import (
    accounts,
    auth,
    books,
    categories,
    currencies,
    fx,
    health,
    invites,
    me,
    reports,
    transactions,
    transfers,
)

_settings = get_config()
configure_observability(
    sentry_dsn=_settings.SENTRY_DSN,
    environment=_settings.ENVIRONMENT,
    log_level=_settings.LOG_LEVEL,
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = f"req_{secrets.token_hex(8)}"
        return await call_next(request)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render domain errors as the D24 envelope: {error:{code,params}, request_id}."""
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": {"code": exc.code, "params": exc.params},
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


def create_app(container: AsyncContainer | None = None) -> FastAPI:
    container = container or build_container()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # FX rate refresh runs as a lifespan task (no worker container at MVP). Gated by a settings
        # flag so tests / offline runs don't reach the network.
        settings = await container.get(Settings)
        task: asyncio.Task[None] | None = None
        if settings.FX_REFRESH_ENABLED:
            sessionmaker = await container.get(async_sessionmaker[AsyncSession])
            client = await container.get(FrankfurterClient)
            task = asyncio.create_task(
                refresh_loop(
                    sessionmaker=sessionmaker,
                    client=client,
                    interval_seconds=settings.FX_REFRESH_INTERVAL_SECONDS,
                )
            )
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="smart-accounting-hub API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)  # bare /healthz, /readyz
    api = APIRouter(prefix="/api/v1")
    api.include_router(auth.router)
    api.include_router(me.router)
    api.include_router(books.router)
    api.include_router(invites.router)
    api.include_router(accounts.router)
    api.include_router(currencies.router)
    api.include_router(fx.router)
    api.include_router(transactions.router)
    api.include_router(reports.router)
    api.include_router(categories.router)
    api.include_router(transfers.router)
    # /api/v1/{auth, me, books, invites, accounts, currencies, fx, tx, reports}
    app.include_router(api)

    app.add_exception_handler(AppError, app_error_handler)
    setup_dishka(container=container, app=app)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    configure_observability(
        sentry_dsn=_settings.SENTRY_DSN,
        environment=_settings.ENVIRONMENT,
        log_level=_settings.LOG_LEVEL,
    )
    uvicorn.run("smart_accounting_api.main:app", host="0.0.0.0", port=8000)
