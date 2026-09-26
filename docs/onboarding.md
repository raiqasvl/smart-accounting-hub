# Onboarding (local dev, target: <30 min from clone to running stack)

## Prereqs

- macOS or Linux.
- **Python 3.12+** (uv will auto-provision if missing).
- **Node 20+** (Node 22 also fine) and **pnpm 9+**.
- **Docker** + Compose v2 (just for Postgres and Redis containers).
- **uv** ([install](https://docs.astral.sh/uv/getting-started/installation/)).
- A Telegram account. Register a bot via `@BotFather` — see [bot-setup.md](bot-setup.md).
- **cloudflared** (or ngrok) to expose `http://localhost:3000` over HTTPS — Telegram requires HTTPS for the Mini-App URL.

## One-time setup

```bash
git clone <repo-url>
cd smart-accounting-hub

make bootstrap                       # uv sync --all-packages + pnpm install

# Register the bot via @BotFather (see docs/bot-setup.md). Gives you BOT_TOKEN + BOT_USERNAME.

cp .env.example .env                 # then edit and fill in BOT_TOKEN, BOT_USERNAME, JWT_SECRET, DOMAIN
mkdir -p db
python3 -c "import secrets; print(secrets.token_urlsafe(24))" > db/password.txt
chmod 600 db/password.txt

# Make sure POSTGRES_DSN's password matches db/password.txt (they're consumed by different processes).
```

## Daily dev (four terminals)

```bash
# Terminal A — postgres + redis
make up                              # detached; tail with `make logs` if needed

# Terminal B — alembic + api
make migrate                         # apply migrations
make dev-api                         # uvicorn --reload on http://localhost:8000

# Terminal C — bot
make dev-bot                         # aiogram long-polling

# Terminal D — Mini-App
make dev-miniapp                     # next dev on http://localhost:3000

# Terminal E (when you need Telegram to reach the Mini-App)
make tunnel                          # cloudflared --url http://localhost:3000
# Copy the printed https://*.trycloudflare.com URL into BotFather: /myapps → Edit Web App URL.
# Update DOMAIN in .env to match (the bot builds the Mini-App button from it). Restart the bot.
```

## Quality gates

```bash
make lint                            # ruff + oxlint
make format                          # ruff format + prettier --write
make typecheck                       # mypy + tsc
make test                            # pytest + vitest
make check                           # all of the above (pre-commit gate)
```

## Where to look first

- `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` — what we're building (M1-M4 in scope; M5 deferred).
- `docs/architecture.md` — how the pieces fit together.
- `apps/api/src/smart_accounting_api/main.py` — API entrypoint.
- `apps/bot/src/smart_accounting_bot/__main__.py` — bot entrypoint.
- `packages/core/src/smart_accounting/models/` — domain models.
- `migrations/versions/` — schema history.

## Stopping for the day

```bash
make down                            # stops postgres + redis
# Ctrl-C the dev-api, dev-bot, dev-miniapp, and tunnel terminals.
```

Volumes (`db-data`, `redis-data`) persist between `down` and the next `up` — your data stays.
To wipe completely: `docker compose -f ops/compose.yml down -v`.
