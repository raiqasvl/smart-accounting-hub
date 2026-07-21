# Liveness + readiness probes (bare paths, no /api/v1 prefix, no JWT).
# No `from __future__ import annotations` here: FastAPI must see `JSONResponse` as a concrete
# Response subclass (not a string) to skip building a response model from it.
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

router = APIRouter(tags=["health"], route_class=DishkaRoute)


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(engine: FromDishka[AsyncEngine]) -> JSONResponse:
    # The API depends on Postgres; Redis is the bot's concern (FSM only), so it's not probed here.
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})
