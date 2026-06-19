# Architecture

> Local-dev architecture. Deployment topology (reverse proxy, multi-replica API, etc.) is deferred — see plan §0 (M5 deferred).

## Runtime topology (local dev)

```text
        Telegram
            │
            ▼  long-poll (host, no public port)
    ┌──────────────────────┐
    │  apps/bot            │  aiogram 3 + aiogram-dialog + Dishka.
    │  uv run python -m    │  Reads + writes via smart_accounting.services.* directly (Q4).
    │  smart_accounting_bot│  Imports SQLAlchemy models from smart_accounting.
    └──────────────────────┘
                                  ┌─── api.frankfurter.dev (FX rates, hourly fetch)
                                  │
    ┌──────────────────────┐      │
    │  apps/api            │──────┘
    │  uv run uvicorn ...  │  FastAPI + Pydantic v2 + Dishka. --reload for hot iteration.
    │  smart_accounting_api│  In-process FX refresh task in lifespan.
    │  :8000               │
    └────────┬─────────────┘
             │  fetch (CORS allows localhost:3000 + the cloudflared subdomain)
             │
    ┌────────▼─────────────┐
    │  apps/miniapp        │  Next.js 15 dev server. pnpm --filter miniapp dev.
    │  :3000               │  Loads Telegram WebApp SDK, calls /auth/telegram, /me.
    └──────────────────────┘
             │
             ▲  cloudflared tunnel → public https://*.trycloudflare.com → :3000
             │
        Telegram WebView (loads the Mini-App URL set in BotFather)

    [ Postgres 16 ]  docker, :5432.   ltree + pgcrypto extensions.
    [ Redis 7 ]      docker, :6379.   FSM storage only.
```

## Why this shape

- **Apps run on host, only DB + Redis in Docker.** Hot-reload is snappy (uvicorn `--reload`, Next.js Fast Refresh, aiogram restart on file change). No image rebuild on edits.
- **Bot ↔ API: no HTTP boundary** (Q4 / D22). Bot calls `smart_accounting.services.*` directly — saves a marshalling layer; one source of truth for business rules.
- **Polling bot, no webhook.** No public port for the bot at all. The Mini-App is the only public surface, exposed via cloudflared.
- **Single Postgres for both processes.** Asyncpg pool per process is fine at MVP scale.
- **Redis is FSM-only.** No caching, no queues at MVP — adds those when we hit M3 + recurring transactions.

See `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` for the full design rationale and locked decisions D1-D32.
