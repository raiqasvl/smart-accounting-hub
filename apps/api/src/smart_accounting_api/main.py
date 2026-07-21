# FastAPI app entrypoint.
#
# `create_app(container)` builds the app and wires health (bare paths), the /api/v1 router group
# (auth + me), the request-id middleware, the D24 error-envelope handler, and Dishka. The
# module-level `app = create_app()` is what uvicorn imports; tests pass a test container.
from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from smart_accounting.config import get_config
from smart_accounting.errors import AppError
from smart_accounting.ioc import build_container
from smart_accounting.observability import configure_observability

from .routers import accounts, auth, books, currencies, health, invites, me

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
    app = FastAPI(title="smart-accounting-hub API", version="0.1.0")
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)  # bare /healthz, /readyz
    api = APIRouter(prefix="/api/v1")
    api.include_router(auth.router)
    api.include_router(me.router)
    api.include_router(books.router)
    api.include_router(invites.router)
    api.include_router(accounts.router)
    api.include_router(currencies.router)
    app.include_router(api)  # /api/v1/{auth/telegram, me, books, invites, accounts, currencies}

    app.add_exception_handler(AppError, app_error_handler)
    setup_dishka(container=container or build_container(), app=app)
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
