---
date: 2026-05-01
last_updated: 2026-05-04
author: Claude (Opus 4.7, 1M)
status: draft
scope: Scope B (mid) — local-dev MVP, M1-M4 in scope, M5 deferred
related:
  - ../research/2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md
  - ../research/2026-04-23-open-source-tg-finance-bot-references.md
  - ../research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md
tags: [plan, mvp, milestones, smart-accounting-hub]
---

# Smart Accounting Hub — MVP Implementation Plan

> **Scope update 2026-05-04:** local-dev MVP only. Deployment, CI/CD, production observability, and backups are **deferred to post-MVP**. This narrows the v1 ship to **M1-M4** (~8 weeks). M5 (hardening + ops + release) returns once we're ready to deploy.

## Overview

Ship the v1.0 Telegram-Mini-App-driven FX accounting tool in **~8 weeks** across **4 two-week milestones (M1–M4)**, **runnable locally**. The headline weighted-average FX rate vertical slice ships at the end of M3 (week 6). M1 establishes the monorepo and end-to-end auth path; M2 builds books + invites + roles + accounts; M3 ships transactions + the headline aggregate; M4 adds categories, charts, and EN/RU. **M5 (deployment + ops) is deferred.**

Stack is locked: Python (aiogram 3.x + aiogram-dialog + Dishka, FastAPI + Pydantic v2, SQLAlchemy 2.x async + asyncpg, Alembic) + Next.js 15 + TS + TanStack Query + shadcn/ui + Recharts. Postgres 16 + Redis 7. **Local dev**: `apps/api` and `apps/bot` run on host (uv); `apps/miniapp` runs on host (pnpm); only Postgres + Redis run in Docker via `ops/compose.yml`. Cloudflared exposes `localhost:3000` over HTTPS for Telegram WebApp loading.

## 0. Decisions locked by this plan

The 5 open §7 questions from `2026-05-01-deep-dive-finwave-and-aiogram-template-references.md` plus the 5 architecture topics from the planning brief are resolved here as **D11–D20**, extending D1–D10 from the prior design doc.

| # | Decision | Rationale |
|---|---|---|
| **D11** | **Reverse proxy = Caddy** (not Nginx). Single binary, auto-TLS via Let's Encrypt, ~5-line `Caddyfile` for our two upstreams. | Nginx is fine but we're a 1-server deploy — Caddy's auto-TLS removes a full ops surface (certbot, renewal cron, reload hooks) for zero loss. Switch to Nginx later if we hit a feature it can't do. |
| **D12** | **Mini-App auth: HS256 JWT, 30-minute lifetime**, claims `{sub: user_id, book_id, role, exp, iat, jti}`. Issued at `POST /auth/telegram` after server-side initData HMAC verification against `BOT_TOKEN`. Refreshed by Mini-App re-posting fresh `initData` on focus events; no separate refresh-token endpoint at MVP. | Telegram considers `initData` fresh up to 24h, but JWT in localStorage is high-blast-radius; 30min limits exposure. Re-validating initData on focus is cheaper than building a refresh-token system. `book_id` and `role` in claims means most API endpoints don't need to re-query `book_members`. |
| **D13** | **Backend errors are i18n-agnostic.** API returns `{error: {code: "FX_RATE_REQUIRED", params: {currency: "USD"}}, http_status: 422}`. Bot and Mini-App localise via Fluent (`aiogram-i18n` / `@fluent/bundle`). | Decouples API stability from translation churn. Codes are stable; copy is editorial. |
| **D14** | **Categories cascade-update on reparent.** When a category's `parents_tree` changes, all descendants get their `parents_tree` recomputed in the same transaction via `UPDATE categories SET parents_tree = subpath(...) WHERE parents_tree <@ old_path`. | UX-consistent: moving "Food" under "Daily" implicitly moves "Food.Lunch". Postgres `ltree` makes this cheap and atomic. |
| **D15** | **`tg_chats` shape**: `(chat_id BIGINT PK, user_id BIGINT FK NOT NULL, active_book_id BIGINT FK NULL, last_message_id BIGINT NULL, ui_mode SMALLINT NOT NULL DEFAULT 0, gpt_mode SMALLINT NOT NULL DEFAULT 0, hide_amounts BOOLEAN NOT NULL DEFAULT FALSE, created_at, updated_at)`. One row per Telegram chat. `active_book_id NULL` ⇒ user is in onboarding. `last_message_id` enables FinWave's single-rolling-message UX. | One user can have many chats (private + group), each with its own active book. Stays denormalised to keep `bot.edit_message_text` paths fast. |
| **D16** | **User-supplied FX rate is authoritative for the row.** Persisted `(amount_quote, rate, amount_base)` is the source of truth. Weighted-average query uses `SUM(amount_quote * rate) / SUM(amount_quote)` over persisted rows; system rate from `exchange_rates` is informational only and shown as a delta in the UI. | Anything else means hiding user-entered data behind a system calculation, which is an audit nightmare for a finance tool. |
| ~~**D17**~~ | **DEFERRED** (was: structlog + Sentry). At local-dev MVP we use plain stdlib `logging` at DEBUG; structlog and Sentry come back when we re-introduce deployment. | Defer rationale: no production traffic to instrument. |
| ~~**D18**~~ | **DEFERRED** (was: pg_dump cron + restic to Backblaze B2). No backups at local-dev MVP — `docker compose down -v` is the "wipe" button. Real backup story lands when we deploy. | Defer rationale: no production data to lose yet. |
| ~~**D19**~~ | **DEFERRED** (was: GitHub Actions CI + manual CD). No `.github/workflows/` exists at MVP. Quality gate is `make check` run by hand. CI returns when we're ready to enforce a green-build culture. | Defer rationale: solo dev for now; no PRs to gate. |
| **D20** | **Secrets: Docker secret for `POSTGRES_PASSWORD` (file mount, `db/password.txt`); `.env` (chmod 600, gitignored) for everything else** (`BOT_TOKEN`, `JWT_SECRET`, FX provider keys). | Pattern still applies — minus the prod-only `RESTIC_PASSWORD` and `B2_*` (deferred with D18). |

D1–D10 from `2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md` §0.3 still apply unchanged.

### 0.1 Implementation-level decisions surfaced during scaffold + grill (D21–D29)

These came out of the post-plan grill-me pass on 2026-05-04. Each is a small but downstream-shaping choice that goes into M1 code; locking them here so we don't re-litigate when filling in functions.

| # | Decision | Notes |
|---|---|---|
| **D21** | **First `/start` = silent auto-create.** Bootstrap user + default book + `book_members(role=OWNER)` + `tg_chats(active_book_id=new_book.id)` in a single transaction. Default `books.name` = i18n key `default-book-name`. Default `books.kind` = 0 (personal). Default `books.base_currency_code` from `language_code` heuristic: `ru → RUB`, `uk → UAH`, `tr → TRY`, `de/fr/es/it/pl/nl → EUR`, anything else → `USD`. User can change in book settings. | Minimises time-to-first-meaningful-screen (0 s vs 30 s for a wizard). Sparse-book risk is acceptable (~200 B/row). |
| **D22** | **Q4 — bot architecture: bot calls `smart_accounting.services.*` directly.** No HTTP between `apps/bot` and `apps/api`. CI grep-guard refuses any `from smart_accounting.{models,repositories}` import inside `apps/bot/src/`. The bot is a presentation surface; rules live in services. | Saves the marshalling layer, keeps audit/RBAC/Sentry breadcrumb logic single-sourced in services, accepts that "two writers, one DB" requires the import discipline above. |
| **D23** | **Q5 — Money on the wire = string.** Pydantic `Money = Annotated[Decimal, BeforeValidator, PlainSerializer(format(v, "f"))]` lives in `packages/core/.../schemas/money.py`. Mini-App uses `big.js` for arithmetic on these strings; `Number()` coerce only for display. | Lossless across NUMERIC(20,8) ↔ wire ↔ JS. Floats lose precision after ~15 digits; cents-as-int fails on mixed-decimals reports (BTC=8 + USD=2). |
| **D24** | **Error envelope shape.** Body: `{"error": {"code": "INVITE_EXPIRED", "params": {"expires_at": "..."}}, "request_id": "req_a1b2c3"}`. HTTP status carries severity (4xx/5xx). Codes are `UPPER_SNAKE`, namespaced loosely by domain (`AUTH_*`, `BOOK_*`, `TX_*`, `FX_*`, `RBAC_*`, `RATE_*`). `request_id` is the structlog correlation id; clients log it on failure. `params` are typed values for Fluent interpolation. | Stable codes decouple API contract from copy. `request_id` makes Sentry ↔ user-report correlation a one-grep operation. |
| **D25** | **Pagination = cursor-based, no totals.** Request: `?cursor=<opaque>&page_size=50` (max 100). Response: `{"items": [...], "next_cursor": "...", "has_more": bool}`. Cursor encodes `(occurred_at DESC, id)` for `fx_transactions`; `(id)` for everything else. Server base64-encodes a small JSON `{after_id, after_at}` and verifies signature with `JWT_SECRET` to prevent forging. | Total counts are O(n) on large tables and the UI never needs them. Signed cursors are cheap forgery prevention. |
| **D26** | **Default invite role = Editor (2).** UI dropdown is pre-selected; inviter can downgrade to Viewer or upgrade to Admin. Owner cannot be assigned via invite. | Editor is the right balance for family + business co-bookkeepers. Viewer is an explicit opt-in for "look but don't touch". |
| **D27** | **JWT refresh = reactive on 401 + proactive on Telegram WebApp focus.** Mini-App's `api-client.ts` catches 401, re-runs `POST /auth/telegram` with fresh `initData`, retries the original request transparently. Additionally, `Telegram.WebApp.onEvent('viewportChanged')` triggers a pre-emptive re-auth if the cached JWT is within 5 min of `exp`. **No `refresh_token` endpoint at v1.0.** | Re-validating initData is ~50 ms server-side; cheaper to maintain than a refresh-token rotation table. Proactive refresh hides the 401 round-trip from the user. |
| **D28** | **Idempotency on `POST /transactions` via column on `fx_transactions`.** Add `idempotency_key TEXT NULL` + `UNIQUE (book_id, idempotency_key) WHERE idempotency_key IS NOT NULL`. Mini-App + bot mint a fresh UUID per "Confirm" tap in `RecordTradeDialog` / Mini-App trade form; server returns the existing row on repeat (200 OK with `Idempotent-Replayed: true` header). | Telegram update-redelivery is common (network blips); without idempotency a double-tap creates two trades. Column-level uniqueness is simpler than a separate `idempotency_keys` table; promote to standalone table in v1.1 if other endpoints need it. |
| **D29** | **Soft-delete = `archived BOOLEAN` column on most domain tables.** `books`, `accounts`, `categories`, `currencies`, `fx_transactions` all carry `archived BOOLEAN NOT NULL DEFAULT FALSE`. List endpoints filter `WHERE NOT archived` by default; admin views pass `?include_archived=true`. **Hard-delete only** for: `book_invites` (purge expired daily), `exchange_rates` (TTL 90 days), `notifications_outbox` (purge 30 days after `delivered_at`). `users.is_blocked` and `tg_chats` (no archive — just inactivity) are exceptions. | Soft-delete preserves audit trail and FK integrity (the headline weighted-avg is meaningless if old transactions can vanish). Hard-delete is reserved for tables with no downstream reference. |
| **D30** | **OpenAPI surface stays public in production.** `/docs` and `/openapi.json` accessible at `https://${DOMAIN}/`. `openapi-typescript` codegen reads it; users curious about the API are welcome. M5 security pass confirms no PII or internal-only fields leak through schema. | Small product, friendly community, no proprietary IP in endpoint shapes. Auth-gating `/docs` would be cargo-culting enterprise patterns. |
| **D31** | **Linter = oxlint, no ESLint.** Config at `.oxlintrc.json` (root). Plugins: typescript, react, react-perf, jsx-a11y, import, node, promise, unicorn, nextjs. Prettier handles formatting (with `prettier-plugin-tailwindcss`); oxlint handles correctness. | Oxlint is ~50× faster than ESLint and covers the rules we'd actually enable. Dropping `eslint-config-next` saves a peer-dep cluster; `nextjs` plugin in oxlint covers the few rules we care about. |
| **D32** | **Time in reports = compute period boundaries in user's timezone.** All DB timestamps are `TIMESTAMPTZ` (UTC). The bot/Mini-App computes "this month" / "last 30 days" against `users.timezone` (IANA), converts the resulting boundaries to UTC ISO 8601, and passes them as `from`/`to` query params. Server is timezone-agnostic on the report endpoints. | A user in Moscow asking "this month" shouldn't get a result that starts at `2026-05-01T00:00:00Z` (3 hours late). Pushing TZ logic to the client keeps the API simple and correct for all locales. |

## Current State Analysis

### Repo state
- Branch: `main`, only commit is `Create README.md` (28a1d16).
- No source code, no migrations, no CI.
- `research/` holds three OSS reference clones: `FinWave-Backend/` (Java), `FinWave-Telegram-Bot/` (Java), `AiogramBotTemplate/` (Python, MIT).
- `thoughts/shared/research/` holds three research docs: 2026-04-23 design doc, 2026-04-23 OSS shortlist, 2026-05-01 reference deep-dive.
- `CLAUDE.md`, `.env.example`, `.gitignore` exist.

### Key discoveries from research
- AiogramBotTemplate (`research/AiogramBotTemplate/`) provides 12 cherry-pick files matching our exact stack — base SQLAlchemy class with naming convention, `Annotated` field types, Dishka request-scoped UoW provider, async Alembic env, Redis FSM with `with_destiny=True`. License is MIT (Artur Boyun, 2024) — must retain copyright in `THIRD_PARTY_NOTICES.md`.
- FinWave-Backend (`research/FinWave-Backend/`) is single-tenant and lacks a historical `exchange_rates` table, weighted-average logic, and Telegram `initData` verification. Three architecturally interesting patterns to copy: hierarchical categories via PostgreSQL `ltree`, polymorphic transactions via `kind` enum + `linked_transaction_id`, and a `notifications_outbox` table drained by a 1-second worker.
- FinWave-Telegram-Bot (`research/FinWave-Telegram-Bot/`) demonstrates the single-rolling-message UX pattern (`MainScene.java:441-450`) we want to adopt. Reject its manual session-paste auth flow; replace with proper Telegram WebApp `initData` HMAC verification.

## Desired End State

After M5 (week 10):

1. **One server**, hosting `caddy` + `postgres:16` + `redis:7` + `apps/api` + `apps/bot` containers via `docker compose up -d`.
2. **A user can:**
   - Open `t.me/<our_bot>` in Telegram, send `/start`.
   - Be auto-registered, see a "Create your first book" inline button → bot dialog asks for book name + base currency + kind (personal/family/business) → book created with user as owner.
   - Open the Mini-App from a `WebAppInfo` button → Mini-App authenticates via `initData` HMAC → JWT issued → user lands on the book dashboard.
   - Generate an invite link from book settings → second user clicks the link in TG → Mini-App handles the invite token → second user joins as `editor` (default) or whatever role the inviter chose.
   - Either user records an FX trade in either surface: "Sold $1000 at ₽90.0; Bought $10000 at ₽90.3" → two `fx_transactions` rows persisted with explicit `(amount_quote, rate, amount_base, fee, fee_currency, occurred_at, note)`.
   - Open the **weighted-average rate report** in Mini-App or run `/avg` in the bot → see `USD sell weighted avg = ₽90.27` calculated from persisted rows over the requested period.
   - Browse a category tree with hierarchical paths via `ltree`, assign categories to transactions, see per-category totals.
   - Switch UI language between EN and RU at any time (Telegram locale auto-detected on first contact).
3. **Operationally:**
   - All errors → Sentry with `book_id`, `user_id`, request id breadcrumbs.
   - JSON logs streamed to stdout, rotated by Docker.
   - Daily 04:00 UTC `pg_dump` + restic snapshot to Backblaze B2.
   - GitHub Actions runs lint + typecheck + tests + `alembic check` on every PR.
   - HTTPS via Caddy auto-TLS at `https://<our-domain>`.

### Verification

- `make check` passes (composite of `ruff check`, `ruff format --check`, `mypy`, `pytest`, `alembic check`, `pnpm -r typecheck`, `pnpm -r lint`, `pnpm -r build`).
- `make smoke` passes — runs `docker compose up -d`, waits for `/healthz`, hits the headline endpoint, tears down.
- A scripted demo at `make demo` seeds two users + one book + 5 transactions and prints the weighted-average rate result.
- Manual checklist (M5) passes end-to-end on both bot and Mini-App, in both EN and RU.

## What We're NOT Doing (v1.0 explicit out-of-scope)

- **No bank statement import** (CSV/OFX/QIF). Deferred to v1.1.
- **No FX-rate alerts** or any push notifications via WebSocket. The `notifications_outbox` table exists but is only used for in-app delivery, not push. Deferred to v1.1.
- **No recurring transactions.** No `recurring_transactions` table at v1.0. Deferred to v1.1.
- **No crypto-asset accounting** beyond what fits the plain `currencies` table (i.e. you can record BTC trades as a currency code, but no order-book-aware semantics).
- **No LLM/AI features.** No GPT mode, no NL parsing of free-text messages, no AI-suggested categorisation. The `ActionParser` Jaccard-similarity NL-lite intake from FinWave-Telegram-Bot is *deferred* to v1.1.
- **No PDF/Excel reports.** Mini-App charts + CSV export only at v1.0.
- **No multi-region / multi-server deployment.** Single VM.
- **No Prometheus, OpenTelemetry, Grafana, or APM** beyond Sentry + structured logs.
- **No `apps/worker` container.** FX rate refresh is an `asyncio` task in API lifespan; outbox drain is the same.
- **No webhook bot** — polling only at v1.0. Webhook is a 1-line config switch when traffic justifies it.
- **No two-factor auth, no email/password.** Telegram is the sole identity provider.
- **No audit log table.** Mutations log to structlog; if compliance demands an audit table later, we add it.
- **No rate limiting middleware** beyond the natural per-chat single-rolling-message back-pressure.

## Implementation Approach

**Layered, bot-first, demo-driven.** Every milestone closes with a runnable demo. We build *up* the layer cake: foundations → multi-tenant scaffolding → headline vertical slice → polish → ops. The headline weighted-average query is the **first feature shipped end-to-end** (M3 demo) — everything before M3 is plumbing in service of it.

**Cherry-pick before write.** Before writing custom code in M1, we lift the 12 files identified in the deep-dive doc §4.7 from `research/AiogramBotTemplate/` into the new monorepo. We extend rather than replace — `Base` gains our domain models, `DepsProvider` gains repositories, `migrations/env.py` is unchanged.

**Schema-first within each milestone.** Each milestone that introduces persistent state begins with a single Alembic migration committed before any service code. This keeps the team un-blocked: API and bot work proceed against the migrated schema in parallel.

**Two surfaces, one service layer.** API routers and bot handlers are presentation only. All business logic lives in `packages/core/services/`. A new feature touches `models → repositories → services → (api router | bot handler) → miniapp`. This is what makes the two-container split cheap.

**Books are book-scoped from line 1.** No "v1 single-user, v2 multi-user" — every domain table has `book_id NOT NULL` from the first migration. Even an onboarding user gets an auto-created default personal book.

---

## Phase 1 / Milestone M1 (Weeks 0–2): Foundations

### Overview
Stand up the monorepo, cherry-pick from AiogramBotTemplate, ship the first end-to-end auth path: TG user `/start` → user row created → book auto-created → JWT issued → Mini-App can call `GET /api/v1/me` and render "Hello {name}, you're in book '{book.name}'".

### Changes Required

#### 1.1 Monorepo bootstrap

**File**: top-level

```
smart-accounting-hub/
├── apps/
│   ├── api/                    # FastAPI uvicorn entrypoint
│   ├── bot/                    # aiogram polling entrypoint
│   └── miniapp/                # Next.js 15
├── packages/
│   ├── core/              # Python package: models, repos, services, FX clients, config, i18n
│   └── api-types/              # TS package: openapi-generated types + zod schemas
├── migrations/                 # Alembic, shared
├── ops/
│   ├── Caddyfile
│   ├── compose.yml
│   ├── compose.prod.yml
│   ├── compose.override.yml
│   ├── backup.sh
│   └── restic-restore-runbook.md
├── .github/workflows/
│   ├── ci.yml
│   └── codeql.yml
├── pyproject.toml              # uv workspace root
├── pnpm-workspace.yaml
├── turbo.json
├── Dockerfile                  # one image, two CMDs
├── Makefile
├── THIRD_PARTY_NOTICES.md      # AiogramBotTemplate MIT, FinWave attribution
└── README.md
```

**Commands** (run once, by hand, captured in `Makefile` `bootstrap` target):

```bash
mise use python@3.12 node@20 pnpm@9
uv init --workspace
pnpm init
pnpm add -Dw turbo @turbo/gen typescript
git init
```

#### 1.2 Cherry-pick from `research/AiogramBotTemplate/`

Copy these 12 files into the new tree, updating package names from `bot_template` → `smart_accounting`:

| Source | Destination |
|---|---|
| `bot/models/base.py` | `packages/core/src/smart_accounting/models/base.py` |
| `bot/models/fields.py` | `packages/core/src/smart_accounting/models/fields.py` |
| `bot/common/uow.py` | `packages/core/src/smart_accounting/common/uow.py` |
| `bot/database/db.py` | `packages/core/src/smart_accounting/database/engine.py` |
| `bot/ioc.py` | `packages/core/src/smart_accounting/ioc.py` |
| `migrations/env.py` | `migrations/env.py` |
| `migrations/script.py.mako` | `migrations/script.py.mako` |
| `alembic.ini` | `alembic.ini` |
| `bot/misc.py` (Redis FSM) | `apps/bot/src/smart_accounting_bot/storage.py` |
| `bot/main.py` (boot order pattern) | `apps/bot/src/smart_accounting_bot/main.py` |
| `bot/__main__.py` (entry shape) | `apps/bot/src/smart_accounting_bot/__main__.py` |
| `bot/config.py` (pydantic-settings shape) | `packages/core/src/smart_accounting/config.py` |

After copy: add MIT attribution header comment block to each lifted file:

```python
# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
```

#### 1.3 Initial Alembic migration `0001_initial.py`

**File**: `migrations/versions/2026_05_01_0001_initial.py`

Tables in order:

1. `users(id BIGSERIAL PK, telegram_user_id BIGINT UNIQUE NOT NULL, telegram_username TEXT NULL, first_name TEXT NULL, last_name TEXT NULL, language TEXT NOT NULL DEFAULT 'en', timezone TEXT NOT NULL DEFAULT 'UTC', is_blocked BOOLEAN NOT NULL DEFAULT FALSE, created_at, updated_at)`
2. `tg_chats(chat_id BIGINT PK, user_id BIGINT FK→users(id), active_book_id BIGINT NULL, last_message_id BIGINT NULL, ui_mode SMALLINT NOT NULL DEFAULT 0, gpt_mode SMALLINT NOT NULL DEFAULT 0, hide_amounts BOOLEAN NOT NULL DEFAULT FALSE, created_at, updated_at)` — D15.
3. `books(id BIGSERIAL PK, owner_id BIGINT FK→users(id), name TEXT NOT NULL, kind SMALLINT NOT NULL, base_currency_code TEXT NOT NULL, default_language TEXT NOT NULL DEFAULT 'en', archived BOOLEAN NOT NULL DEFAULT FALSE, created_at, updated_at)` — `kind` enum: 0=personal, 1=family, 2=business.
4. `book_members(book_id BIGINT FK, user_id BIGINT FK, role SMALLINT NOT NULL, invited_at, accepted_at NULL, PRIMARY KEY(book_id, user_id))` — `role` enum: 0=owner, 1=admin, 2=editor, 3=viewer.
5. `book_invites(id BIGSERIAL PK, book_id BIGINT FK, invited_by BIGINT FK→users(id), token TEXT UNIQUE NOT NULL, role SMALLINT NOT NULL, expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ NULL, created_at)` — token is `secrets.token_urlsafe(24)`.
6. `currencies(id BIGSERIAL PK, book_id BIGINT NULL FK→books(id), code TEXT NOT NULL, symbol TEXT NOT NULL, decimals SMALLINT NOT NULL, kind SMALLINT NOT NULL DEFAULT 0, archived BOOLEAN NOT NULL DEFAULT FALSE, created_at, updated_at, UNIQUE(book_id, code))` — `book_id NULL` means system-catalogue row; per-book overrides allowed (FinWave pattern). `kind` enum: 0=fiat, 1=crypto, 2=metal.
7. `accounts(id BIGSERIAL PK, book_id BIGINT FK→books(id) NOT NULL, currency_code TEXT NOT NULL, name TEXT NOT NULL, kind SMALLINT NOT NULL, archived BOOLEAN NOT NULL DEFAULT FALSE, opening_balance NUMERIC(20,8) NOT NULL DEFAULT 0, created_at, updated_at)` — `kind` enum: 0=cash, 1=bank, 2=card, 3=brokerage, 4=other.
8. `categories(id BIGSERIAL PK, book_id BIGINT FK→books(id) NOT NULL, parents_tree LTREE NOT NULL, kind SMALLINT NOT NULL, name TEXT NOT NULL, description TEXT NULL, archived BOOLEAN NOT NULL DEFAULT FALSE, created_at, updated_at)` + GIST index on `(book_id, parents_tree)` — D14.
9. `exchange_rates(id BIGSERIAL PK, base_currency_code TEXT NOT NULL, quote_currency_code TEXT NOT NULL, rate NUMERIC(20,8) NOT NULL, source TEXT NOT NULL, fetched_at TIMESTAMPTZ NOT NULL, UNIQUE(base_currency_code, quote_currency_code, source, fetched_at))` + index `(base_currency_code, quote_currency_code, fetched_at DESC)`.
10. `fx_transactions(id BIGSERIAL PK, book_id BIGINT FK→books(id) NOT NULL, created_by_user_id BIGINT FK→users(id) NOT NULL, kind transaction_kind NOT NULL DEFAULT 'plain_cash', direction transaction_direction NOT NULL, base_account_id BIGINT FK→accounts(id) NULL, quote_account_id BIGINT FK→accounts(id) NULL, base_currency_code TEXT NOT NULL, quote_currency_code TEXT NOT NULL, amount_quote NUMERIC(20,8) NOT NULL, rate NUMERIC(20,8) NOT NULL, amount_base NUMERIC(20,8) NOT NULL, fee NUMERIC(20,8) NOT NULL DEFAULT 0, fee_currency_code TEXT NULL, occurred_at TIMESTAMPTZ NOT NULL, note TEXT NULL, source TEXT NULL, category_id BIGINT FK→categories(id) NULL, linked_transaction_id BIGINT FK→fx_transactions(id) NULL, created_at, updated_at)` + indexes per design doc §4. — Headline table.
11. `notifications_outbox(id BIGSERIAL PK, user_id BIGINT FK→users(id) NOT NULL, book_id BIGINT FK→books(id) NULL, kind TEXT NOT NULL, payload JSONB NOT NULL, delivered_at TIMESTAMPTZ NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), attempts SMALLINT NOT NULL DEFAULT 0)` + partial index on `(created_at) WHERE delivered_at IS NULL`.

Postgres extensions in the migration `upgrade()` head: `CREATE EXTENSION IF NOT EXISTS ltree;` and `CREATE EXTENSION IF NOT EXISTS pgcrypto;` for `gen_random_uuid()`.

Enum types created via `op.execute("CREATE TYPE transaction_kind AS ENUM ('plain_cash', 'internal_transfer', 'fx_conversion')")` and `transaction_direction AS ENUM ('buy', 'sell')`.

#### 1.4 FastAPI app skeleton

**File**: `apps/api/src/smart_accounting_api/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dishka.integrations.fastapi import setup_dishka
from smart_accounting.config import get_config
from smart_accounting.ioc import make_container
from .routers import auth, health, me

@asynccontextmanager
async def lifespan(app: FastAPI):
    # FX rate refresh task (M3 will add the actual fetcher)
    yield

app = FastAPI(title="Smart Accounting Hub API", lifespan=lifespan, version="0.1.0")
container = make_container()
setup_dishka(container=container, app=app)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(me.router)
```

**File**: `apps/api/src/smart_accounting_api/routers/health.py`

```python
from fastapi import APIRouter
router = APIRouter()
@router.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

**File**: `apps/api/src/smart_accounting_api/routers/auth.py`
- `POST /auth/telegram` — accepts `{init_data: str}`, validates HMAC against `BOT_TOKEN`, upserts user + auto-creates default personal book if user is new, mints JWT with claims `{sub, book_id, role, exp, iat, jti}`. Returns `{access_token, expires_in: 1800, user, book}`.

**File**: `apps/api/src/smart_accounting_api/routers/me.py`
- `GET /me` — JWT-authenticated, returns current user + active book.

**File**: `packages/core/src/smart_accounting/auth/initdata.py`
- `def verify_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict` — implements the HMAC-SHA256 check per Telegram WebApp docs.

**File**: `packages/core/src/smart_accounting/auth/jwt.py`
- `def issue_token(*, user_id, book_id, role, secret, lifetime_seconds=1800) -> str`
- `def decode_token(token: str, secret: str) -> Claims`

#### 1.5 aiogram bot skeleton

**File**: `apps/bot/src/smart_accounting_bot/__main__.py`

Boot order copied from AiogramBotTemplate `bot/main.py:42-58`:

```python
import asyncio
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka
from aiogram_dialog import setup_dialogs
from .main import dp, bot
from .ioc import DepsProvider
from .handlers import commands_router
from .dialogs import register_dialogs

async def start_polling() -> None:
    container = make_async_container(DepsProvider())
    setup_dishka(container=container, router=dp)
    dp.include_router(commands_router)
    register_dialogs(dp)
    setup_dialogs(dp)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(start_polling())
```

**File**: `apps/bot/src/smart_accounting_bot/handlers/commands.py`
- `/start` handler — upserts user + tg_chat row, creates default book if user is new, sends "👋 Welcome to Smart Accounting Hub. Open the Mini-App ⬇️" with a `WebAppInfo` button. No multi-step dialog yet — that lands in M2.

#### 1.6 Next.js Mini-App skeleton

**File**: `apps/miniapp/`

`pnpm create next-app@latest --typescript --tailwind --app --src-dir --import-alias "@/*"`. Add:
- `@tanstack/react-query@5`
- `@telegram-apps/sdk-react@2`
- `recharts@2`
- shadcn/ui: `npx shadcn@latest init` then `npx shadcn@latest add button card input label dialog`
- `openapi-typescript` (devDep) + a `pnpm types:gen` script that runs `openapi-typescript http://localhost:8000/openapi.json -o packages/api-types/src/api.d.ts`.

The M1 Mini-App is a single page: `app/page.tsx` reads `Telegram.WebApp.initData` via the SDK, posts it to `/api/v1/auth/telegram`, stores the JWT in memory + sessionStorage, calls `/api/v1/me`, renders `<Card>Hello {name}, book "{book.name}"</Card>`.

#### 1.7 Docker + Caddy

**File**: `Dockerfile` (lifted from AiogramBotTemplate, generalised for two CMDs):

```dockerfile
ARG PYTHON_VERSION=3.12.3
FROM python:${PYTHON_VERSION}-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"
# CMD set per-service in compose
```

**File**: `ops/compose.yml`

```yaml
services:
  api:
    build: ..
    command: ["uvicorn", "smart_accounting_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
    env_file: ../.env
    depends_on: { db: {condition: service_healthy}, redis: {condition: service_healthy} }
    healthcheck: { test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"], interval: 10s, retries: 5 }
  bot:
    build: ..
    command: ["python", "-m", "smart_accounting_bot"]
    env_file: ../.env
    depends_on: { db: {condition: service_healthy}, redis: {condition: service_healthy}, api: {condition: service_healthy} }
  db:
    image: postgres:16
    user: postgres
    secrets: [db-password]
    environment:
      POSTGRES_DB: smart_accounting
      POSTGRES_USER: smart_accounting
      POSTGRES_PASSWORD_FILE: /run/secrets/db-password
    volumes: ["db-data:/var/lib/postgresql/data"]
    healthcheck: { test: ["CMD", "pg_isready"], interval: 5s, retries: 10 }
  redis:
    image: redis:7
    volumes: ["redis-data:/data"]
    healthcheck: { test: ["CMD", "redis-cli", "ping"], interval: 5s, retries: 10 }
  caddy:
    image: caddy:2-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - "./Caddyfile:/etc/caddy/Caddyfile:ro"
      - "caddy-data:/data"
      - "caddy-config:/config"
    depends_on: [api]
volumes: { db-data: {}, redis-data: {}, caddy-data: {}, caddy-config: {} }
secrets: { db-password: { file: ../db/password.txt } }
```

**File**: `ops/Caddyfile`

```
{$DOMAIN} {
    encode gzip
    @api path /api/* /openapi.json /healthz
    handle @api { reverse_proxy api:8000 }
    handle { reverse_proxy api:8000 }   # miniapp is served from Next.js standalone build; route to a separate "miniapp" service in M4
}
```

#### 1.8 CI

**File**: `.github/workflows/ci.yml`

Matrix:
- python-lint: `uv run ruff check && uv run ruff format --check`
- python-typecheck: `uv run mypy packages/core apps/api apps/bot`
- python-tests: `uv run pytest`
- python-migrate-check: spin up postgres in service container, run `alembic upgrade head` then `alembic check`
- ts-lint: `pnpm -r lint`
- ts-typecheck: `pnpm -r typecheck`
- ts-build: `pnpm -r build`

#### 1.9 Sentry + structlog wiring

**File**: `packages/core/src/smart_accounting/observability.py`

```python
import logging, sys
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

def configure_observability(*, sentry_dsn: str | None, environment: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
        )
```

#### 1.10 Makefile

```makefile
.PHONY: bootstrap up down migrate test check smoke demo
bootstrap:; uv sync && pnpm install
up:;        docker compose -f ops/compose.yml up -d --build
down:;      docker compose -f ops/compose.yml down
migrate:;   docker compose -f ops/compose.yml exec api alembic upgrade head
test:;      uv run pytest && pnpm -r test
check:;     uv run ruff check && uv run ruff format --check && uv run mypy . && uv run pytest && uv run alembic check && pnpm -r typecheck && pnpm -r lint
smoke:;     bash ops/smoke.sh
demo:;      bash ops/demo.sh
```

### Success Criteria

#### Automated Verification:
- [ ] `make bootstrap` succeeds on a clean clone.
- [ ] `make up` brings up 5 healthy containers within 60s.
- [ ] `make migrate` applies `0001_initial.py` cleanly to a fresh DB; `alembic check` reports no diff.
- [ ] `make check` passes (ruff + mypy + pytest + alembic + tsc + eslint + build).
- [ ] `curl https://localhost/healthz` returns `{"status":"ok"}` (with `-k` for self-signed Caddy local cert).
- [ ] `pnpm -F miniapp build` produces a `.next` standalone artifact.
- [ ] CI green on a hand-pushed branch with no source changes (template smoke).

#### Manual Verification:
- [ ] `/start` to the dev bot creates a `users` row, a `tg_chats` row, and an auto-created `books` row of kind=personal with the user as owner.
- [ ] Pressing the WebApp button in Telegram opens the Mini-App, which authenticates via initData and shows "Hello {first_name}, book '{book.name}'".
- [ ] Tampering the JWT (changing one character) makes `/api/v1/me` return 401.
- [ ] Tampering `init_data` (changing one byte) makes `/api/v1/auth/telegram` return 403.
- [ ] Sentry receives a deliberate `raise RuntimeError("smoke")` from a `/api/v1/__sentry-test__` route in dev.
- [ ] Logs from `apps/api` and `apps/bot` are JSON-formatted in `docker logs`.

**Implementation Note**: After M1, pause for manual confirmation. M2 cannot start until the auth path works end-to-end on a real Telegram account.

---

## Phase 2 / Milestone M2 (Weeks 2–4): Books, invites, accounts, currencies

### Overview
Layer multi-tenant primitives on top of the M1 skeleton: book CRUD, invite flow with magic-link deep-link, role-based authorization, currencies seed (system catalogue), per-book accounts. Bot grows two aiogram-dialog flows (create-book, join-via-invite). Mini-App grows a book picker.

### Changes Required

#### 2.1 RBAC enforcement layer

**File**: `packages/core/src/smart_accounting/auth/rbac.py`

```python
from enum import IntEnum
class Role(IntEnum):
    OWNER = 0; ADMIN = 1; EDITOR = 2; VIEWER = 3

PERMISSIONS = {
    Role.OWNER: {"book.delete", "book.invite", "book.role.change", "book.read", "tx.write", "tx.read", "category.write", "account.write"},
    Role.ADMIN: {"book.invite", "book.role.change", "book.read", "tx.write", "tx.read", "category.write", "account.write"},
    Role.EDITOR: {"book.read", "tx.write", "tx.read", "category.write", "account.write"},
    Role.VIEWER: {"book.read", "tx.read"},
}

def require(permission: str):
    def decorator(handler): ...  # FastAPI dependency that reads JWT claims and asserts permission
```

Bot handlers gate via the same enum: every dialog window queries the current `tg_chats.active_book_id` → `book_members.role` → permission set.

#### 2.2 Book CRUD (API + bot)

API:
- `POST /books` — create. Body: `{name, kind, base_currency_code, default_language}`. Caller becomes `OWNER`.
- `GET /books` — list books the user is a member of.
- `GET /books/{book_id}` — book detail.
- `PATCH /books/{book_id}` — rename/archive (admin+).
- `POST /books/{book_id}/switch` — sets `tg_chats.active_book_id` for the calling user across all their chats; re-mints JWT with new `book_id` claim.

Bot:
- aiogram-dialog `CreateBookDialog` (states: `Name → Kind → BaseCurrency → Confirm → Done`). Persists via `BookService.create()`. On success, `bot.edit_message_text` updates the rolling main message to show the new book.
- `/books` command opens a select dialog of the user's books.

#### 2.3 Invites

API:
- `POST /books/{book_id}/invites` (admin+) — body `{role, ttl_minutes=1440}`. Returns `{token, deep_link: "https://t.me/<bot>?start=invite_{token}"}`.
- `POST /invites/{token}/accept` — accepts. Idempotent. Body empty (caller identity from JWT). On success, creates `book_members` row, returns the joined book.
- `DELETE /books/{book_id}/invites/{invite_id}` — revoke.

Bot:
- `/start invite_{token}` deep-link handler in `commands.py`: validates the token, prompts the user to accept ("Join 'Family Budget' as Editor?"), on accept calls `InviteService.accept(token, user_id)`, switches active book.

Mini-App:
- Book settings tab: `Invites` section with current pending invites + "Invite member" form (role dropdown + copy link button).

#### 2.4 Currencies seed

**File**: `packages/core/src/smart_accounting/data/currencies_seed.py` — list of ~40 fiat (ISO 4217 majors) + 5 crypto (BTC, ETH, USDT, USDC, BNB). Seeded by an idempotent Alembic data migration `0002_seed_currencies.py`.

API:
- `GET /currencies` — returns system catalogue + active book's overrides (FinWave's `WHERE book_id IS NULL OR book_id = $1` pattern).
- `POST /books/{book_id}/currencies` — admin+ adds a per-book custom currency.

#### 2.5 Accounts CRUD

API:
- `POST /books/{book_id}/accounts` — body `{currency_code, name, kind, opening_balance}`.
- `GET /books/{book_id}/accounts` — list (filterable by `archived`).
- `PATCH /accounts/{id}` / `DELETE /accounts/{id}` — admin+ for hide/archive; only owner can hard-delete (FK semantics enforce: can only delete if no transactions reference it; otherwise forbidden, suggest archive).

Bot:
- aiogram-dialog `CreateAccountDialog` (states: `CurrencyPicker → KindPicker → Name → OpeningBalance → Confirm → Done`).

Mini-App:
- Accounts tab: list view with shadcn `Card` per account, badge for currency, `Plus` button opens Drawer with form.

### Success Criteria

#### Automated Verification:
- [ ] All M1 checks pass.
- [ ] Migration `0002_seed_currencies.py` applies; `SELECT count(*) FROM currencies WHERE book_id IS NULL` returns 45+.
- [ ] `pytest tests/api/test_books.py` covers: create, list, switch (JWT re-mint), permission denial for non-member, archive.
- [ ] `pytest tests/api/test_invites.py` covers: create, accept by another user, double-accept idempotent, expired token, revoked token, already-member.
- [ ] `pytest tests/api/test_accounts.py` covers: create, list, archive, FK protect on delete with transactions.
- [ ] `pytest tests/services/test_rbac.py` covers permission matrix for all 4 roles × all 8 permissions.

#### Manual Verification:
- [ ] User A creates a book "Family Budget" (kind=family, base RUB).
- [ ] User A generates an invite link with role=Editor.
- [ ] User B opens the link in Telegram, accepts, lands in the same book.
- [ ] User B (Editor) cannot delete the book (UI hides delete; API returns 403).
- [ ] User A switches to a different book via `/books`; the bot's rolling main message updates to show the new book name; the JWT in the Mini-App is re-issued.
- [ ] User A creates a USD account "Cash" with opening balance 500.

**Implementation Note**: After M2, pause for manual confirmation. The headline vertical slice (M3) requires accounts to land in.

---

## Phase 3 / Milestone M3 (Weeks 4–6): FX transactions + weighted-average headline

### Overview
**The product's headline ships at the end of this milestone.** Build `fx_transactions` write/read paths in API + bot, the weighted-average aggregate query, and the Mini-App report card. FX rates are fetched from Frankfurter (free, ECB-backed, no API key) by an `asyncio` task in the API lifespan.

### Changes Required

#### 3.1 FX rate fetcher

**File**: `packages/core/src/smart_accounting/fx/clients.py`

Single client at MVP: `FrankfurterClient` (`https://api.frankfurter.dev/v1/latest?base=USD`). Returns dict `{quote_code: rate}`. Other clients (CoinGecko, ECB direct) deferred.

**File**: `packages/core/src/smart_accounting/fx/refresh.py`

```python
async def refresh_loop(*, sessionmaker, http, interval_seconds: int = 3600) -> None:
    while True:
        try:
            rates = await FrankfurterClient(http).fetch_latest(base="USD")
            async with sessionmaker() as s:
                for code, rate in rates.items():
                    await s.execute(insert(ExchangeRate).values(
                        base_currency_code="USD",
                        quote_currency_code=code,
                        rate=Decimal(str(rate)),
                        source="frankfurter",
                        fetched_at=now(),
                    ))
                await s.commit()
        except Exception:
            log.exception("fx_refresh_failed")
        await asyncio.sleep(interval_seconds)
```

Wired into API lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(refresh_loop(sessionmaker=container.get(AsyncSessionMaker), http=container.get(httpx.AsyncClient)))
    yield
    task.cancel()
```

#### 3.2 Transaction service (D16-aware)

**File**: `packages/core/src/smart_accounting/services/transactions.py`

```python
class TransactionService:
    async def record(self, *, book_id, user_id, kind, direction,
                     base_account_id, quote_account_id,
                     base_currency_code, quote_currency_code,
                     amount_quote: Decimal, rate: Decimal,
                     fee: Decimal, fee_currency_code, occurred_at, note,
                     category_id) -> FxTransaction:
        # D16: user-supplied `rate` is authoritative; we persist exactly what the user gave.
        # `amount_base` is computed: amount_base = amount_quote * rate
        # We DO NOT consult exchange_rates here — that table is informational only.
        ...

    async def record_fx_conversion(self, *, ...) -> tuple[FxTransaction, FxTransaction]:
        # Two-leg transaction. Both rows persist with kind='fx_conversion' and
        # linked_transaction_id pointing at each other (set in second pass).
        ...
```

#### 3.3 Weighted-average aggregate query

**File**: `packages/core/src/smart_accounting/repositories/reports.py`

```python
async def weighted_avg_rate(
    session: AsyncSession,
    *,
    book_id: int,
    quote_currency_code: str,
    direction: TransactionDirection,
    occurred_after: datetime | None = None,
    occurred_before: datetime | None = None,
) -> Decimal | None:
    stmt = (
        select(
            func.sum(FxTransaction.amount_quote * FxTransaction.rate)
            / func.sum(FxTransaction.amount_quote)
        )
        .where(
            FxTransaction.book_id == book_id,
            FxTransaction.quote_currency_code == quote_currency_code,
            FxTransaction.direction == direction,
        )
    )
    if occurred_after:  stmt = stmt.where(FxTransaction.occurred_at >= occurred_after)
    if occurred_before: stmt = stmt.where(FxTransaction.occurred_at <  occurred_before)
    return (await session.execute(stmt)).scalar_one_or_none()
```

#### 3.4 API endpoints

- `POST /books/{book_id}/transactions` — body matches the service `.record()` signature; returns the persisted row.
- `GET /books/{book_id}/transactions` — list + filter (date range, currency, account, category, direction, kind). Pagination cursor-based.
- `PATCH /transactions/{id}` — editor+ only; updating `rate` recomputes `amount_base`.
- `DELETE /transactions/{id}` — editor+; soft-archive only at MVP (we add `archived BOOLEAN`). Cascades to `linked_transaction_id` partner.
- `GET /books/{book_id}/reports/weighted-avg-rate?quote=USD&direction=sell&from=...&to=...` — returns `{book_id, quote, direction, weighted_avg_rate, sample_count, sum_amount_quote, period}`.

#### 3.5 Bot dialog

aiogram-dialog `RecordTradeDialog` with states:
- `Direction` (buy/sell) → `BaseCurrency` (auto-suggest book.base_currency) → `QuoteCurrency` → `BaseAccount` (filtered by base_currency) → `QuoteAccount` (filtered by quote_currency) → `AmountQuote` → `Rate` (with current Frankfurter rate as a hint) → `OccurredAt` (default: now) → `Note` (optional, skip-able) → `Confirm` → done.

`/avg` command opens a quick aiogram-dialog: `Direction → QuoteCurrency → DateRange (last 30d / this month / all time / custom)` → renders the result inline.

#### 3.6 Mini-App: Trades + Report card

- New tab `Trades` with TanStack Query–backed table (sortable, filterable). shadcn `DataTable`.
- New tab `Reports` with the headline card:
  - Direction toggle (Buy/Sell)
  - Currency picker (defaults to most-traded from a sample query)
  - Date range picker (preset: last 30d / this month / YTD / custom)
  - Result: large number with `Decimal` formatting, sample count, sum traded, period
  - Below: a `<Recharts>` line chart of `rate` over `occurred_at` for the same filter — visualises individual trades vs the avg.

#### 3.7 Translation strings (deferred to M4)

All new strings keyed but only English populated. Russian lands in M4.

### Success Criteria

#### Automated Verification:
- [ ] Migration applied; `fx_transactions` has 12 columns and 4 indexes.
- [ ] `pytest tests/services/test_transactions.py` covers: plain_cash record, internal_transfer (two linked rows), fx_conversion (two linked rows), edit recomputes `amount_base`, role gates.
- [ ] `pytest tests/repositories/test_reports.py::test_weighted_avg` — given a fixture of `[(1000, 90.0), (10000, 90.3)]` returns `90.272727...` (within ε).
- [ ] `pytest tests/api/test_transactions.py` covers: create → list → patch → archive → 403 paths.
- [ ] `pytest tests/api/test_reports.py::test_weighted_avg_rate_endpoint` end-to-end against test DB.
- [ ] `pytest tests/fx/test_frankfurter.py` covers the client (with respx-mocked HTTP).
- [ ] FX refresh task seeds `exchange_rates` rows on first lifespan startup (integration test).

#### Manual Verification:
- [ ] User A records two trades in the bot: sell 1000 USD @ 90.0, sell 10000 USD @ 90.3.
- [ ] `/avg sell USD all` in the bot prints `Weighted avg sell USD: ₽90.272727 (2 trades, $11,000)`.
- [ ] Mini-App `Reports` tab shows the same number.
- [ ] Recharts shows two dots at 90.0 and 90.3 with a horizontal line at the weighted avg.
- [ ] User B (Editor) can also record trades; both users see consistent results.
- [ ] FX-rate refresh has populated at least 30 rows in `exchange_rates` after 1h uptime.

**Implementation Note**: This is the **demo milestone**. Schedule a recorded walkthrough at the end of M3.

---

## Phase 4 / Milestone M4 (Weeks 6–8): Categories, charts, EN/RU, polish

### Overview
Round out the user-facing surface: hierarchical categories with `ltree`, additional Mini-App charts (account balances over time, P&L by currency), full EN/RU translation pass, internal-transfer flow, CSV export.

### Changes Required

#### 4.1 Category service

**File**: `packages/core/src/smart_accounting/services/categories.py`

- `create(book_id, parent_id?, kind, name)` — computes `parents_tree` from parent.
- `move(category_id, new_parent_id)` — D14 cascade: `UPDATE categories SET parents_tree = subpath_replace(parents_tree, $old, $new) WHERE parents_tree <@ $old` in single transaction.
- `delete(category_id)` — refuses if any descendants or any `fx_transactions.category_id = ...` exists; offer archive.

API:
- `POST /books/{book_id}/categories`, `GET /books/{book_id}/categories` (returns flat list ordered by `parents_tree`), `PATCH /categories/{id}` (rename, move), `DELETE /categories/{id}` (archive).

Bot:
- aiogram-dialog category picker as a reusable widget — paginated tree view, max 8 buttons per page.

Mini-App:
- Categories settings page with a tree view (recursive `<TreeNode>` from shadcn-extension or hand-rolled).

#### 4.2 Internal transfer flow

Bot dialog `InternalTransferDialog`: `FromAccount → ToAccount → Amount → Note → Confirm` — creates two linked `fx_transactions` rows with `kind='internal_transfer'` (same currency on both legs).

API: `POST /books/{book_id}/transfers` — convenience wrapper around the two-row creation.

#### 4.3 Mini-App charts

- `AccountBalanceChart`: line chart of computed running balance per account over selected date range. Computed from `fx_transactions` joined to `accounts` — opening_balance + running sum of signed deltas.
- `PnLByCurrencyChart`: bar chart per quote currency, summing `(rate - book_avg_rate) * amount_quote` over closed positions. (Stretch: defer to v1.1 if it bloats M4.)

#### 4.4 i18n

- Fluent files at `packages/core/src/smart_accounting/i18n/{en,ru}/main.ftl` for bot strings.
- `@fluent/bundle` + `@fluent/react` for Mini-App at `apps/miniapp/src/i18n/{en,ru}/*.ftl`.
- aiogram middleware reads `users.language` (default from `effective_user.language_code` on first message), injects a `FluentLocalization` into handlers.
- Mini-App reads `Telegram.WebApp.initDataUnsafe.user.language_code`, falls back to `'en'`.
- Manual EN/RU translation pass on every string introduced in M1–M4. CI grep step `! grep -rE 'Const\("[А-Яа-я]' apps/bot/src/` to forbid hardcoded Russian.

#### 4.5 CSV export

API: `GET /books/{book_id}/transactions/export.csv?from=...&to=...` — streams CSV with all transaction columns. Editor+ permission.

Mini-App: button on Trades tab.

### Success Criteria

#### Automated Verification:
- [ ] All prior checks pass.
- [ ] `pytest tests/services/test_categories.py` covers: create, move with cascade, ltree subpath integrity, delete-blocked-by-descendant, delete-blocked-by-transactions.
- [ ] `pytest tests/api/test_internal_transfers.py` covers two-leg creation + linkage.
- [ ] `pytest tests/i18n/test_fluent_keys.py` asserts EN and RU files have identical key sets (no missing translations).
- [ ] CI grep step blocks any PR containing hardcoded Russian outside `**/i18n/ru/**`.
- [ ] CSV export produces a valid file with stable column order; tested via fixture.

#### Manual Verification:
- [ ] Create a category tree: "Food" → "Lunch" / "Groceries"; assign a transaction to "Lunch"; rename "Food" to "Daily" — the descendant's `parents_tree` is now `Daily.Lunch`.
- [ ] Switch bot language to RU via `/lang` command — all dialogs render in Russian.
- [ ] Mini-App detects user's TG language; switches automatically.
- [ ] AccountBalanceChart renders a sensible curve for an account with 5+ transactions.
- [ ] CSV export opens cleanly in Excel and Google Sheets.

**Implementation Note**: M4 ends with the product feeling like a real v1. Schedule a 30-minute UX review with a real prospective user.

---

## Phase 5 / Milestone M5 — DEFERRED (was: Hardening, ops, release)

> **Status: deferred (2026-05-04).** Local-dev MVP excludes deployment, CI/CD, backups, and production observability. M5 returns as the post-MVP "ship-it" milestone. The body below is preserved for when we resume — none of it applies until then.

### Overview (deferred)

No new features. Pen-test the auth surface, set up backups + monitoring, write the runbook, dry-run a deploy on a clean VM, tag v1.0.

### Changes Required

#### 5.1 Security pass
- [ ] Re-audit `verify_init_data()` against fresh Telegram WebApp docs; add property-based tests using `hypothesis` for HMAC tampering.
- [ ] Confirm JWT decoding rejects: expired, wrong-signature, none-alg, mismatched `book_id` (reuse from another book), revoked `jti` (basic in-memory blocklist for compromised tokens).
- [ ] Verify all routers have `require(permission)` dependencies; add a meta-test that iterates over `app.routes` and asserts every non-`/health` non-`/auth` route has a Dishka-injected RBAC dep.
- [ ] Run `bandit` on Python codebase, `pnpm audit` on TS, address criticals.
- [ ] Add `secure: true; HttpOnly: true; SameSite: lax` cookie semantics if we ever set a cookie (we don't at MVP — JWT is in `Authorization: Bearer`).
- [ ] Confirm Caddy serves `Strict-Transport-Security` and `X-Frame-Options: deny`.

#### 5.2 Backups
- [ ] `ops/backup.sh` runs `pg_dump -Fc smart_accounting > /tmp/dump.pgc && restic backup /tmp/dump.pgc`.
- [ ] Cron in compose.prod.yml (or systemd timer on host) runs `0 4 * * *` UTC.
- [ ] `ops/restic-restore-runbook.md` — step-by-step restore procedure.
- [ ] **Restore drill in M5:** spin up a second VM, restore latest snapshot, verify row counts match production.

#### 5.3 Production deploy

- [ ] `ops/compose.prod.yml` — sets `DEBUG=False`, removes `compose.override.yml`'s exposed ports, wires Caddy to the real `DOMAIN`.
- [ ] DNS A record points to server.
- [ ] `ops/deploy-runbook.md`:
  ```
  ssh deploy@server
  cd /srv/smart-accounting-hub
  git pull
  docker compose -f ops/compose.yml -f ops/compose.prod.yml up -d --build
  docker compose exec api alembic upgrade head
  docker compose exec api curl -f localhost:8000/healthz
  ```

#### 5.4 Smoke + demo automation
- [ ] `ops/smoke.sh`: brings up compose, polls `/healthz`, hits `POST /auth/telegram` with a stubbed valid initData, hits `GET /me`, tears down. Used by CI nightly.
- [ ] `ops/demo.sh`: seeds 2 users, 1 book, 5 transactions, prints `weighted_avg_rate` from a direct API call. Used in the M5 demo and onboarding.

#### 5.5 Documentation
- [ ] `README.md` — quickstart, prereqs, `make` targets.
- [ ] `docs/architecture.md` — link to research docs + 1-page ascii diagram of the runtime topology.
- [ ] `docs/onboarding.md` — getting a fresh dev set up in <30 min.
- [ ] `THIRD_PARTY_NOTICES.md` — finalised with all attributions.

#### 5.6 Release
- [ ] Tag `v1.0.0` on `main`.
- [ ] Cut a GitHub release with the changelog.
- [ ] Production deploy from the tag.
- [ ] Send the bot link to the first 5 prospective users with a short feedback form.

### Success Criteria

#### Automated Verification:
- [ ] `make smoke` passes on a clean VM.
- [ ] `make demo` produces the expected weighted-avg result.
- [ ] `bandit` returns 0 high-severity findings.
- [ ] `pnpm audit --prod` returns 0 highs.
- [ ] CI nightly smoke is green for 7 consecutive nights.
- [ ] Restic restore script verified on a second VM.

#### Manual Verification:
- [ ] Production URL serves Mini-App over HTTPS with auto-TLS.
- [ ] First 5 users complete the full onboarding flow without intervention.
- [ ] No Sentry events with severity ≥ error in the first 24h post-launch.
- [ ] Weekly backup snapshot is present in B2.
- [ ] Deploy runbook executable by a second person who has not seen the codebase.

---

## Testing Strategy

### Unit tests
- **Pure logic in `packages/core/services/`**: no DB, no HTTP, fast. Aim ≥80% coverage on services and repositories.
- **`verify_init_data` and `decode_token`**: property-based with `hypothesis` — adversarial inputs.
- **RBAC matrix**: parametrised over (role, permission) pairs.
- **Weighted-avg arithmetic**: `Decimal` precision, divide-by-zero (no rows), single-row case.

### Integration tests
- **API**: `pytest-asyncio` + `httpx.AsyncClient` against a real Postgres (testcontainers or compose-spun-up). Per-test transaction rolled back.
- **Bot**: aiogram has a test utility (`Bot.session.middleware`) — covered for `/start`, `/avg`, dialog happy paths, deep-link invite acceptance.
- **DB**: `alembic upgrade head` then `alembic check` runs in CI — guards against drifting migrations.

### Manual testing checklist (M5)
1. Fresh user `/start` → onboarded with default book.
2. Create a family book; invite a second user; second user accepts.
3. Both users record 3 trades each; each sees the other's trades.
4. Editor edits a trade; viewer cannot.
5. Owner archives the book; editor sees a friendly message; viewer sees nothing.
6. Switch bot to Russian; dialogs render in Russian.
7. Open Mini-App; charts render; CSV export downloads.
8. Pull plug on `redis` for 30s; bot stops accepting commands gracefully; resumes when restored.
9. Pull plug on `db` for 30s; both surfaces return user-friendly errors; resume cleanly.

### Performance considerations
- **Weighted-avg query** is a single GROUP BY over an indexed `(book_id, quote_currency_code, direction, occurred_at DESC)` — should be <10ms for 100k rows. Benchmark in M3.
- **FX-rate refresh** runs hourly, fetches ~150 rows from Frankfurter, inserts them — negligible.
- **Notifications outbox** (unused at MVP for push) is queried via `WHERE delivered_at IS NULL` with a partial index; remains <1k rows in steady state.
- Connection pool: asyncpg pool size = 20 per process; api gets 2 uvicorn workers in prod = 40 concurrent connections per service. Postgres `max_connections = 200` is plenty.

## Migration notes

- v1.0 is a greenfield deploy — no data migration concerns.
- All Alembic migrations run forward-only at v1.0 — no autogenerated downgrade beyond what Alembic produces by default.
- Expect to ship 2–3 hot-fix migrations in v1.0.x; reserve `0099_*` and below for v1.0.

## Risks and mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Frankfurter API changes shape | Low | Medium | Single client behind `FxClient` protocol; swap in another source in <1 day. |
| aiogram-dialog 2.x has rough edges | Medium | Medium | Cherry-picked template uses 2.2.0; spike a multi-step dialog in M1 before committing M2 to it; fallback to plain aiogram FSM if blocked. |
| `ltree` reparent cascade subtlety | Medium | Low | Property-based test with `hypothesis` over random tree structures in M4. |
| Telegram Mini App SDK API drift | Medium | Medium | Pin `@telegram-apps/sdk-react` exact version; smoke test on iOS + Android + Desktop in M5. |
| Single-VM deploy means single point of failure | High | Medium | Daily B2 backups (D18); document restore drill; defer HA to v1.2. |
| Scope creep on M3 (the demo milestone) | High | High | Explicit out-of-scope list in §"What We're NOT Doing"; M4 has slack to absorb 2-3 day overruns. |
| Sentry dropped events | Low | Low | Sentry self-hosted is overkill at MVP; accept SaaS Sentry's free-tier rate limits. |
| User picks Russian → forgotten string falls back to EN | Medium | Low | CI grep + `pytest tests/i18n/test_fluent_keys.py`. |

## References

- Research: `thoughts/shared/research/2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md` (D1–D10, base schema)
- Research: `thoughts/shared/research/2026-04-23-open-source-tg-finance-bot-references.md` (22-repo OSS shortlist)
- Research: `thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md` (cherry-pick list, schema additions, gap analysis)
- Cherry-pick source: `research/AiogramBotTemplate/` (MIT, Artur Boyun 2024)
- Architectural reference: `research/FinWave-Backend/` (Apache 2.0)
- UX reference: `research/FinWave-Telegram-Bot/` (Apache 2.0)
- Telegram WebApp initData spec: <https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app>
- aiogram 3 docs: <https://docs.aiogram.dev/en/v3.13.1/>
- aiogram-dialog: <https://aiogram-dialog.readthedocs.io/>
- Dishka: <https://dishka.readthedocs.io/>
- Frankfurter: <https://www.frankfurter.dev/>

## Appendix: timeline at a glance

```text
Week  1   2   3   4   5   6   7   8        ~deferred~
      |---M1---|---M2---|---M3---|---M4---|--(M5)--
M1: foundations, auth path E2E
M2: books + invites + accounts + currencies
M3: ★ FX transactions + weighted-avg headline ★
M4: categories + charts + EN/RU + transfers + CSV
M5: harden + ops + release      ← DEFERRED (post-MVP)
```

★ = headline demo milestone.
