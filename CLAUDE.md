# CLAUDE.md — agent context for smart-accounting-hub

This file is loaded by Claude Code in every session. Keep it short.

## What this project is

Telegram-Mini-App-driven FX accounting tool with weighted-average rate as the headline feature.
Full background and locked decisions D1–D20 are in:

- `thoughts/shared/research/2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md` (D1–D10)
- `thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md` (cherry-pick list)
- `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` (D11–D20, milestones M1–M5)

## Stack (locked)

Python 3.12 (uv workspace) + aiogram 3.x + FastAPI + SQLAlchemy 2.x async + Postgres 16 + Redis 7 + Alembic + Dishka.
Next.js 15 + TS + TanStack Query + shadcn/ui + Tailwind + Recharts (pnpm + Turborepo workspace).
Single Dockerfile, two CMDs (`apps/api` + `apps/bot`), single-VM deploy via Caddy.

## Workflow rules

- **Do not use Linear MCP.** No tickets fetched, no statuses moved.
- Plans in `thoughts/shared/plans/`, research in `thoughts/shared/research/`, naming `YYYY-MM-DD-description.md`.
- For multi-repo or multi-file research, dispatch sub-agents (codebase-analyzer / Explore) in parallel.
- All money is `NUMERIC(20,8)` in Postgres + `Decimal` in Python + **string in JSON** (Q5; see `packages/core/.../schemas/money.py`).
- All tables `book_id`-scoped. All errors return `{code, params}`; i18n in bot/Mini-App layer.
- **`apps/bot` calls `smart_accounting.services.*` directly** (Q4). Never imports from `smart_accounting.{models,repositories}`. CI grep-guard enforces this.

## Tooling

- Python: ruff (lint+format) + mypy (strict) + pytest. Configured in root `pyproject.toml`.
- TS/TSX: **oxlint** (no ESLint) + Prettier. Configs at `.oxlintrc.json` and `.prettierrc`. Run `pnpm lint` from root.

## Where things live

| What | Where |
|---|---|
| Domain models, repos, services | `packages/core/src/smart_accounting/` |
| FastAPI routers | `apps/api/src/smart_accounting_api/routers/` |
| Bot handlers + dialogs | `apps/bot/src/smart_accounting_bot/` |
| Mini-App | `apps/miniapp/src/` |
| Migrations | `migrations/versions/` |
| Compose + Caddyfile + scripts | `ops/` |
| OSS reference clones | `research/` (gitignored) |
