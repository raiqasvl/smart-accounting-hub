---
date: 2026-06-10T17:51:45+07:00
researcher: i.gorvier
git_commit: 28a1d1686c7065c1bfa6538603a070efb60a0e35
branch: main
repository: smart-accounting-hub
topic: "Current implementation state of smart-accounting-hub vs. documented architecture"
tags: [research, codebase, scaffolding, mvp, m1, monorepo, fastapi, aiogram, nextjs]
status: complete
last_updated: 2026-06-10
last_updated_by: i.gorvier
---

# Research: Current Implementation State of smart-accounting-hub

**Date**: 2026-06-10T17:51:45+07:00
**Researcher**: i.gorvier
**Git Commit**: 28a1d1686c7065c1bfa6538603a070efb60a0e35
**Branch**: main
**Repository**: smart-accounting-hub

## Research Question

Document the current implementation state of the codebase — what actually exists in code, how it is structured, and how it compares to the architecture described in `CLAUDE.md` / `STRUCTURE.md` — to establish a factual baseline before any enhancement work.

## Summary

The repository is a **fully laid-out but entirely unimplemented scaffold**. The directory structure, package boundaries, dependency manifests, tooling, and developer docs that the architecture describes all exist and are real. The application logic does not.

Key verified facts:

- **All 59 `.py` files in `packages/`, `apps/`, and `migrations/` are comment-only.** A line-level scan (`grep -vE '^\s*#'` then strip blanks) returns **zero executable lines across all 59 files**. Every model, schema, service, repository, router, handler, dialog, middleware, auth helper, FX client, and Alembic env exists only as prose `#` comments describing intended behavior.
- **The TypeScript/JSX source is the same story.** Every `.tsx`/`.ts` module under `apps/miniapp/src/` and `packages/shared_ts/src/` is comment-only, except `packages/shared_ts/src/api.d.ts`, which holds real `export` statements that intentionally resolve to empty types (`Record<string, never>`).
- **Real, working content exists only in configuration and documentation**: every `pyproject.toml` / `package.json`, the workspace/tooling configs (`turbo.json`, `pnpm-workspace.yaml`, `.oxlintrc.json`, `.prettierrc`, ruff/mypy/pytest in root `pyproject.toml`), `alembic.ini`, `migrations/script.py.mako`, `ops/compose.yml`, the `Makefile`, `.env.example`, and the three `docs/*.md` files.
- **Nothing is committed.** Git contains a single commit (`28a1d16 Create README.md`). The entire scaffold — `apps/`, `packages/`, `migrations/`, `ops/`, configs, `thoughts/` — is untracked working-tree content.
- **No migrations exist.** `migrations/versions/` contains only `.gitkeep`. `migrations/env.py` is a comment-only stub (does not import metadata, would not run).
- **Two artifacts the docs reference do not exist anywhere in the project**: a **Dockerfile** (CLAUDE.md/STRUCTURE.md mention "single Dockerfile"; only gitignored `research/` clones contain Dockerfiles) and a **Caddyfile** (`docs/bot-setup.md` claims Caddy is "already in `ops/compose.yml`"; it is not — only `db` and `redis` services are defined).

In short: the project is at the **very start of milestone M1**. Per the MVP plan, M1 ("Foundations") is the milestone where all of this scaffolding gets filled in. The map and the territory diverge cleanly along the config-vs-code line.

## Detailed Findings

### Repository shape (what physically exists)

Verified directory layout (noise dirs excluded):

- `packages/shared_py/src/smart_accounting/` — 13 model stubs, `schemas/`, `auth/`, `fx/`, `i18n/`, `data/`, `database/`, `common/`, plus `config.py`, `ioc.py`, `observability.py`. **`repositories/` and `services/` contain only `__init__.py`** — no aggregate modules.
- `packages/shared_ts/src/` — `index.ts`, `api.d.ts`, `money.ts`.
- `apps/api/src/smart_accounting_api/` — `main.py`, `deps.py`, `routers/{auth,health,me}.py` + tests.
- `apps/bot/src/smart_accounting_bot/` — `main.py`, `__main__.py`, `storage.py`, `handlers/commands.py`, empty `middlewares/`, `dialogs/`, `services/` packages + tests.
- `apps/miniapp/src/` — `app/{layout,page}.tsx`, `lib/{api-client,telegram}.ts`, `i18n/{en,ru}/main.ftl`, empty `components/`.
- `migrations/` — `env.py` (stub), `script.py.mako` (real), `README` (real), `versions/.gitkeep` only.
- `ops/compose.yml`, `db/password.txt`, `Makefile`, root configs, `docs/`, `thoughts/`.

### `packages/shared_py` — domain core (all placeholders)

Every file is comment-only; the comments specify the intended schema/signatures precisely.

- **Models** ([packages/shared_py/src/smart_accounting/models/](packages/shared_py/src/smart_accounting/models/)) — 11 domain tables documented in comments: `users`, `tg_chats`, `books`, `book_members`, `book_invites`, `currencies`, `accounts`, `categories`, `exchange_rates`, `fx_transactions`, `notifications_outbox`. `models/__init__.py` has all 11 imports **commented out**.
  - [models/base.py](packages/shared_py/src/smart_accounting/models/base.py) — documents `Base(AsyncAttrs, DeclarativeBase)` with index naming convention + `created_at`/`updated_at` timestamp mixin.
  - [models/fields.py](packages/shared_py/src/smart_accounting/models/fields.py) — documents `Annotated` column aliases: `uuid_pk`, `bigserial_pk`, `currency_code` (`String(8)`), `money_amount` (`NUMERIC(20,8)`), `ltree_path` (`LtreeType`), `tg_user_id`, `timestamptz`.
  - [models/fx_transaction.py](packages/shared_py/src/smart_accounting/models/fx_transaction.py) — the headline table; documents `kind`/`direction` Postgres enums, `amount_quote`/`rate`/`amount_base`/`fee` as `NUMERIC(20,8)`, self-FK `linked_transaction_id`, and 3 indexes. Invariant noted: weighted-avg = `SUM(amount_quote*rate)/SUM(amount_quote)`.
  - [models/category.py](packages/shared_py/src/smart_accounting/models/category.py) — `parents_tree LTREE` with documented `GIST(book_id, parents_tree)` index (D14).
  - `archived BOOLEAN` is documented inline on `accounts`, `books`, `categories`, `currencies`, `fx_transactions` (D29).
- **schemas/** — [schemas/money.py](packages/shared_py/src/smart_accounting/schemas/money.py) documents the `Money = Annotated[Decimal, BeforeValidator, PlainSerializer(...when_used="json"), WithJsonSchema(...string...)]` contract (Q5/D23). No code.
- **config.py / ioc.py / database/engine.py / common/uow.py** — all comment-only. They sketch `get_config()` (pydantic-settings + `@lru_cache`), Dishka `DepsProvider`, `create_async_engine`/`async_sessionmaker`, and the `UoW` async-context-manager respectively.
- **repositories/ and services/** — confirmed empty: only `__init__.py` in each, comment-only, exporting nothing. The `__init__.py` comments list the *planned* per-milestone files (e.g. M1 `users.py`/`books.py`; M3 `transaction_service.py`/`reports.py`).

### `packages/shared_py` — cross-cutting (all placeholders)

- [auth/initdata.py](packages/shared_py/src/smart_accounting/auth/initdata.py) — documents `verify_init_data(init_data, bot_token, max_age_seconds=86400)` HMAC-SHA256 algorithm + `InitDataInvalid`/`InitDataExpired`. No code.
- [auth/jwt.py](packages/shared_py/src/smart_accounting/auth/jwt.py) — documents `issue_token(...)` / `decode_token(...)`, HS256, claims `{sub, book_id, role, exp, iat, jti}`, 1800s lifetime (D12). No code.
- [auth/rbac.py](packages/shared_py/src/smart_accounting/auth/rbac.py) — documents `Role(IntEnum)` (OWNER=0…VIEWER=3) and a `PERMISSIONS` matrix (OWNER 8 perms, ADMIN 7, EDITOR 5, VIEWER 2) + `has_permission`/`require_or_raise`. No code.
- [fx/clients.py](packages/shared_py/src/smart_accounting/fx/clients.py) — documents `FxClient` Protocol + `FrankfurterClient` (`https://api.frankfurter.dev/v1/latest`). No code.
- [fx/refresh.py](packages/shared_py/src/smart_accounting/fx/refresh.py) — documents `refresh_loop(*, sessionmaker, http, interval_seconds=3600)` run inside API lifespan. No code.
- [data/currencies_seed.py](packages/shared_py/src/smart_accounting/data/currencies_seed.py) — documents ~45 currencies (~40 fiat + BTC/ETH/USDT/USDC/BNB + XAU/XAG) with fields `{code, symbol, decimals, kind}`. **No actual seed list.**
- [observability.py](packages/shared_py/src/smart_accounting/observability.py) — documents `configure_observability(sentry_dsn, environment)` (structlog + Sentry). No code.
- **i18n** — [i18n/en/main.ftl](packages/shared_py/src/smart_accounting/i18n/en/main.ftl) and [i18n/ru/main.ftl](packages/shared_py/src/smart_accounting/i18n/ru/main.ftl) each contain **zero live message ids** (en has 2 commented-out examples; ru has none).

### `apps/api` — FastAPI surface (only pyproject.toml is real)

- [apps/api/pyproject.toml](apps/api/pyproject.toml) — **real**. Declares `fastapi[standard]>=0.115`, `uvicorn`, `pydantic`, `dishka>=1.4`, `httpx`, `pyjwt>=2.9`, `structlog`, `sentry-sdk[fastapi]`, workspace dep `smart-accounting`. Script entry `smart_accounting_api.main:run`.
- [main.py](apps/api/src/smart_accounting_api/main.py) — comment-only. No `FastAPI()` instance, no lifespan, no CORS, no router registration, no Dishka wiring exists as code.
- [deps.py](apps/api/src/smart_accounting_api/deps.py) — comment-only. Documents `current_jwt_claims()`, `current_user()`, `current_book_member()`, `require(permission)`. No providers implemented.
- **Routers**: only `auth.py`, `health.py`, `me.py` exist, all comment-only. Documented endpoints: `POST /auth/telegram`, `GET /healthz`, `GET /readyz`, `GET /me`. **Missing entirely** (no files): books, invites, accounts, currencies (M2); transactions, reports (M3); categories, transfers, export (M4).
- **Tests** ([tests/conftest.py](apps/api/tests/conftest.py)) — comment-only; no fixtures, no test functions.

### `apps/bot` — aiogram bot (only pyproject.toml is real)

- [apps/bot/pyproject.toml](apps/bot/pyproject.toml) — **real**. Declares `aiogram>=3.13`, `aiogram-dialog>=2.2`, `dishka>=1.4`, `redis>=5.2`, `structlog`, `sentry-sdk`. Comment reiterates the Q4 rule (no `httpx` on purpose; bot never HTTPs the API). Script entry `smart_accounting_bot.__main__:main`.
- [__main__.py](apps/bot/src/smart_accounting_bot/__main__.py) / [main.py](apps/bot/src/smart_accounting_bot/main.py) — comment-only. Document the 7-step boot (observability → Dishka container → `setup_dishka` → include routers → `register_dialogs` → `setup_dialogs` → `start_polling`), attributed to AiogramBotTemplate. No `Bot`/`Dispatcher` constructed.
- [storage.py](apps/bot/src/smart_accounting_bot/storage.py) — comment-only. Documents `RedisStorage.from_url(...)` with `DefaultKeyBuilder(with_destiny=True)`. No code.
- [handlers/commands.py](apps/bot/src/smart_accounting_bot/handlers/commands.py) — comment-only. Documents `/start`, `/start invite_<token>`, `/books`, `/lang`, `/avg`, `/trade`. No handlers, no router object.
- `dialogs/`, `middlewares/`, `services/` — empty packages (only comment-only `__init__.py`). **No aiogram-dialog scenes exist** — `MainScene`, `RecordTradeDialog`, etc. appear only inside comments.
- **Tests** ([tests/conftest.py](apps/bot/tests/conftest.py)) — comment-only; no fixtures, no tests.

### `apps/miniapp` + `packages/shared_ts` — frontend (config real, source placeholder)

Real, working config (8 files): [apps/miniapp/package.json](apps/miniapp/package.json) (`next ^15`, `react ^19`, `@tanstack/react-query ^5.59`, `@telegram-apps/sdk-react ^2`, `recharts`, `@fluent/*`, `zod`, tailwind), [next.config.mjs](apps/miniapp/next.config.mjs) (`output: 'standalone'`), [postcss.config.mjs](apps/miniapp/postcss.config.mjs), [tailwind.config.ts](apps/miniapp/tailwind.config.ts), [tsconfig.json](apps/miniapp/tsconfig.json) (`@/*`, `@shared/*` aliases), [packages/shared_ts/package.json](packages/shared_ts/package.json), [packages/shared_ts/tsconfig.json](packages/shared_ts/tsconfig.json).

Placeholders (comment-only): [app/layout.tsx](apps/miniapp/src/app/layout.tsx), [app/page.tsx](apps/miniapp/src/app/page.tsx), [lib/api-client.ts](apps/miniapp/src/lib/api-client.ts) (no fetch client, no TanStack setup, no JWT handling), [lib/telegram.ts](apps/miniapp/src/lib/telegram.ts) (no SDK integration), both `i18n/*/main.ftl` (0 message ids), [shared_ts/src/index.ts](packages/shared_ts/src/index.ts), [shared_ts/src/money.ts](packages/shared_ts/src/money.ts) (no `Money` type, `big.js` not yet a dep).

Partial: [shared_ts/src/api.d.ts](packages/shared_ts/src/api.d.ts) — real exports but `export type paths = Record<string, never>` / `components = Record<string, never>` (regenerated by `pnpm types:gen` against the live OpenAPI once the API exists).

### Infrastructure & build (config real; migrations/Docker absent)

- **Root tooling (real)**: [pyproject.toml](pyproject.toml) — uv workspace members `apps/api`, `apps/bot`, `packages/shared_py`; ruff (line-length 100, py312, select `E,W,F,I,B,UP,ASYNC,SIM,RUF`), mypy `strict=true` + pydantic plugin, pytest `asyncio_mode=auto`. [package.json](package.json) — turbo scripts + `types:gen` via `openapi-typescript`. [turbo.json](turbo.json), [pnpm-workspace.yaml](pnpm-workspace.yaml), [.oxlintrc.json](.oxlintrc.json), [.prettierrc](.prettierrc).
- **Makefile (real)** — targets: `bootstrap`, `up`/`down`/`restart`/`logs`, `migrate`/`revision`, `dev-api`/`dev-bot`/`dev-miniapp`/`tunnel`, `test`/`lint`/`format`/`typecheck`/`check`, `clean`. `dev-api` runs `uvicorn smart_accounting_api.main:app` (target symbol doesn't exist yet).
- **Alembic**: [alembic.ini](alembic.ini) real (date-prefixed `file_template`, `ruff format` post-write hook); [migrations/script.py.mako](migrations/script.py.mako) real; [migrations/env.py](migrations/env.py) **comment-only stub** (no metadata import, would not run); [migrations/versions/](migrations/versions/) **only `.gitkeep`** — zero migrations.
- **Ops**: [ops/compose.yml](ops/compose.yml) real — defines **only `db` (postgres:16)** and **`redis` (redis:7-alpine)** with healthchecks, volumes, and a `db-password` Docker secret. No api/bot/miniapp/caddy services.
- **Absent artifacts**: no **Dockerfile** anywhere in the project (only in gitignored `research/` clones), despite `.dockerignore` and the architecture docs referencing one. No **Caddyfile**, despite `docs/bot-setup.md:232` claiming Caddy is already in compose.
- **Docs (real, substantive)**: [docs/architecture.md](docs/architecture.md) (~47 lines, topology diagram), [docs/bot-setup.md](docs/bot-setup.md) (~366 lines, BotFather walkthrough), [docs/onboarding.md](docs/onboarding.md) (~81 lines, local-dev workflow).

## Code References

- `packages/shared_py/src/smart_accounting/models/fx_transaction.py` — headline table spec (comment-only)
- `packages/shared_py/src/smart_accounting/repositories/__init__.py` — empty repo layer; lists planned files
- `packages/shared_py/src/smart_accounting/services/__init__.py` — empty service layer; lists planned files
- `apps/api/src/smart_accounting_api/main.py` — FastAPI boot spec (comment-only)
- `apps/bot/src/smart_accounting_bot/__main__.py:4-12` — 7-step bot boot spec (comment-only)
- `apps/miniapp/src/lib/api-client.ts` — API client spec (comment-only)
- `packages/shared_ts/src/api.d.ts:6-7` — empty-stub OpenAPI types
- `migrations/env.py` — Alembic env stub (no metadata import)
- `migrations/versions/.gitkeep` — only file in versions dir
- `ops/compose.yml` — db + redis services only
- `pyproject.toml:25` — uv workspace members
- `Makefile` — all dev/quality targets

## Architecture Documentation (patterns present as design, not code)

The documents `CLAUDE.md` and `STRUCTURE.md` describe the intended system: a uv Python workspace (`shared_py` + `apps/api` + `apps/bot`) plus a pnpm/Turborepo TS workspace (`shared_ts` + `apps/miniapp`); strict layering models ← repositories ← services ← presentation; bot calling `services.*` directly (Q4); money as `NUMERIC(20,8)`/`Decimal`/string (Q5/D23); `book_id`-scoped multitenancy (D2); `{code, params}` error envelopes (D13/D24). **Every one of these patterns currently exists only as prose** — in the architecture docs and as the `#`-comment specifications embedded in each scaffolded source file. The package boundaries and dependency manifests that would enforce the DAG are real; the code that would live inside them is not.

The one place where the docs are already stale relative to the (absent) code: the **Dockerfile** and **Caddyfile** are referenced as existing but do not exist. Per STRUCTURE.md §15 ("if the doc and the code disagree, the code is right"), these are doc-ahead-of-code gaps rather than code defects.

## Historical Context (from thoughts/)

From [thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md](thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md):

- **Milestones** are 2-week each: **M1 Foundations** (monorepo bootstrap, all 11 tables in one Alembic migration, end-to-end `/start` → auto-create user+book → JWT → Mini-App `GET /me`), **M2** books/invites/accounts/currencies + RBAC, **M3** fx_transactions + the weighted-average headline (the "demo milestone"), **M4** categories/charts/EN-RU/transfers/CSV. **M5** (hardening/ops/release) is **deferred** as of 2026-05-04.
- **Weighted-average headline ships at the end of M3** (week 6); plan line 122: "everything before M3 is plumbing in service of it." Query: `sum(amount_quote*rate)/sum(amount_quote)` in `repositories/reports.py`.
- **D11–D32** are locked (D11 Caddy, D12 JWT, D13 i18n-agnostic errors, D14 ltree cascade, D15 tg_chats, D16 user rate authoritative, D17/D18/D19 deferred, D20 secrets, D21 silent auto-create, D22 bot direct service calls, D23 money-as-string, D24 error envelope, D25 cursor pagination, D26 invite=Editor, D27 reactive JWT refresh, D28 idempotency key, D29 soft-delete, D30 public OpenAPI, D31 oxlint, D32 user-TZ period boundaries).
- **Explicitly out of scope (v1.0)**: bank import, push/WebSocket notifications, recurring transactions, crypto accounting beyond currency rows, any LLM/AI features, PDF/Excel reports, multi-server deploy, Prometheus/OTel, `apps/worker`, webhook bot, 2FA, audit-log table, rate limiting.
- **M1 definition of done** includes: `make bootstrap`/`make up`/`make migrate`/`make check` succeed; `/healthz` returns ok; `/start` creates user+tg_chat+book; Mini-App authenticates via initData and renders "Hello {name}, book '{name}'"; tampered JWT → 401; tampered initData → 403. Plan line 475: "M2 cannot start until the auth path works end-to-end on a real Telegram account."
- **Testing strategy**: pytest-asyncio + httpx against real Postgres (testcontainers), per-test rollback; hypothesis property tests for `verify_init_data`/`decode_token`; parametric RBAC matrix; weighted-avg precision/divide-by-zero cases; weighted-avg query target <10ms at 100k rows.

Related background: [thoughts/shared/research/2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md](thoughts/shared/research/2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md) (D1–D10), [thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md](thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md) (cherry-pick list).

## Related Research

- `thoughts/shared/research/2026-04-23-open-source-tg-finance-bot-references.md`
- `thoughts/shared/research/2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md`
- `thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md`
- `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md`

## Open Questions

- The scaffold's embedded `#`-comment specs are detailed and internally consistent, but nothing has been validated against a running stack (no migration has ever been applied; no app has ever booted). Whether the documented column types/enums/indexes round-trip cleanly through `alembic revision --autogenerate` is untested.
- `docs/onboarding.md` and the `Makefile` reference symbols that do not yet exist (`smart_accounting_api.main:app`, the `0001_initial` migration). These are forward references in the scaffold, not defects, but they will fail if run today.
- The Dockerfile and Caddyfile referenced by the architecture/docs are absent; whether they were intended for M1 or M5 (D11 Caddy is "deferred" per CLAUDE.md but "in scope" per the M1 plan's container list) is a doc-internal inconsistency.
