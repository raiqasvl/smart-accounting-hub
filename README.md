# smart-accounting-hub

Telegram-Mini-App-driven personal/family/business **FX accounting** tool. Headline feature: **weighted-average exchange-rate** queries across stored FX transactions.

> "Sold $1,000 at ₽90.0; sold $10,000 at ₽90.3 — what's my average sell rate?" → **₽90.27.**

## Status

🚧 **In implementation. Local-dev focus only at MVP.** Deployment + CI/CD deferred to post-MVP.
v1.0 plan: `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` (M1→M4 in scope; M5 deferred).

## Stack

- **Backend**: Python 3.12 · aiogram 3.x + aiogram-dialog · FastAPI + Pydantic v2 · SQLAlchemy 2.x async + asyncpg · Alembic · Dishka · uv
- **Database**: PostgreSQL 16 (with `ltree` extension) · Redis 7 (FSM only)
- **Frontend (Mini-App)**: Next.js 15 + TypeScript · TanStack Query · shadcn/ui · Tailwind · Recharts
- **Type sharing**: OpenAPI 3.1 (FastAPI) → `openapi-typescript` → typed TS clients in the Mini-App

## Quickstart (local dev)

> **Bot-side credentials first.** Before anything boots, you need a `BOT_TOKEN` from `@BotFather` and a Mini-App URL.
> The full guide is at [docs/bot-setup.md](docs/bot-setup.md). ~15 minutes.

```bash
# One-time setup
make bootstrap                       # uv sync --all-packages + pnpm install
cp .env.example .env                 # fill in BOT_TOKEN, JWT_SECRET, DOMAIN — see docs/bot-setup.md
mkdir -p db && python3 -c "import secrets; print(secrets.token_urlsafe(24))" > db/password.txt && chmod 600 db/password.txt

# Daily dev — three terminals
make up                              # postgres + redis in docker
make migrate                         # alembic upgrade head
make dev-api                         # terminal A: uvicorn --reload on :8000
make dev-bot                         # terminal B: aiogram polling
make dev-miniapp                     # terminal C: next dev on :3000
make tunnel                          # terminal D: cloudflared → public HTTPS for Telegram
```

## Layout

```text
apps/        api · bot · miniapp           Two Python processes + one Next.js app, all run on host in dev.
packages/    core · api-types          Shared domain code (Py) + generated API types (TS).
migrations/  Alembic                        Single shared migration history.
ops/         compose.yml                    db + redis containers (only).
docs/        architecture · onboarding · bot-setup
research/    OSS reference clones (gitignored)
thoughts/    plans · research                Long-form design docs.
```

## Development

See [docs/onboarding.md](docs/onboarding.md).

## Licence

Source-available; licence TBD. Third-party attributions in `THIRD_PARTY_NOTICES.md`.
