---
date: 2026-05-01
researcher: Claude (Opus 4.7, 1M)
status: complete
supersedes_in_part: 2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md (§1, §8)
related:
  - 2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md
  - 2026-04-23-open-source-tg-finance-bot-references.md
tags: [research, references, finwave, aiogram, scaffolding, domain-model, fx-accounting]
---

# Deep-Dive: FinWave-Backend, FinWave-Telegram-Bot, AiogramBotTemplate as references

> **TL;DR.** FinWave is the closest existing OSS analog of what we want, but it is **single-tenant, has no historical FX rate table, no weighted-average rate logic, and no Telegram integration**. So FinWave gives us a domain *skeleton* and several architecturally interesting patterns (hierarchical categories via `ltree`, polymorphic transactions via metadata, ActionsWorker strategy dispatch, two-table notification queue) — but the headline features that justify our project (weighted-avg FX, book-scoped multi-tenancy, Mini-App initData auth) we still have to design ourselves. AiogramBotTemplate (MIT, Python 3.12 + uv + aiogram + Dishka + FastAPI + SQLAlchemy 2.x) matches our stack exactly but is a 600-LOC seed: cherry-pick patterns, do not fork. FinWave-Telegram-Bot is a Java thin-client that uses a manual session-paste flow we will *not* replicate.

## 0. Verdict and adoption matrix

| Reference | Language | Role | Adoption decision |
|---|---|---|---|
| **FinWave-Backend** ([github](https://github.com/FinWave-App/FinWave-Backend)) | Java 17 + jOOQ + Flyway + Spark + Guice | Domain-model inspiration for accounting primitives | **Adopt as architectural reference** — do not port code; rewrite each useful pattern in Python. |
| **FinWave-Telegram-Bot** ([github](https://github.com/FinWave-App/FinWave-Telegram-Bot)) | Java 17 + pengrad + Java-WebSocket | Telegram-side UX patterns (single rolling message, scenes, WS push) | **Light architectural reference only.** Reject auth flow, i18n approach, blocking `.get()` patterns. |
| **AiogramBotTemplate** ([github](https://github.com/arturboyun/AiogramBotTemplate)) | Python 3.12 + aiogram 3.13 + Dishka + FastAPI + SQLAlchemy 2.x | Code-level scaffolding | **Cherry-pick ~12 files, do not fork.** MIT licence; retain copyright in our `THIRD_PARTY_NOTICES.md`. |

This supersedes the earlier shortlist in `2026-04-23-open-source-tg-finance-bot-references.md`: the prior shortlist had `archiesir/aiogram_bot_template`; the cloned/reviewed repo is in fact `arturboyun/AiogramBotTemplate`. The prior recommendation to "read all four FinWave repos" is also revised: we only need `FinWave-Backend` for domain inspiration and `FinWave-Telegram-Bot` for UX patterns. The frontend and deploy repos add little — FinWave-Frontend is a Vue.js SPA and FinWave-Deploy is the same docker-compose recipe we'd write ourselves. Skip them.

## 1. What changed since the Yakov teardown

The 2026-04-23 design doc was written against Yakov, which is a Ukrainian utility bot with no accounting domain. With FinWave on the table, we now have:

1. **A real OSS accounting domain to compare against.** FinWave maps `accounts → transactions → categories → currencies → notifications` end-to-end. Confirms our table list in §4 of the design doc is roughly right.
2. **Concrete validation of two design choices** in our locked decisions table (D1-D10):
   - **D5 (`numeric` precision):** FinWave uses unbounded `numeric`, which we explicitly reject. Our `NUMERIC(20,8)` mandate stands and is more disciplined than the OSS prior art.
   - **D8 (separate `users_sessions` for revocable bearer tokens):** Validated. FinWave's session model (DB-stored bearer tokens, `limited` flag for sensitive-op gating) is exactly the pattern we proposed for our Mini-App tokens vs full web sessions.
3. **Confirmed gaps that still require fresh design:**
   - **D2 (book-scoped multi-tenancy)** — FinWave has zero precedent. Every domain table is `owner_id INTEGER → users(id)`. There is no books, workspaces, households, role matrix, or invite flow anywhere in the OSS world we surveyed. We are first.
   - **D3 (weighted-average FX rate)** — Not in FinWave. Cross-currency transfers in FinWave are two unrelated transactions linked by metadata; the implicit rate is never persisted, never aggregated. We are first.
   - **D6 (historical rates with provenance)** — Not in FinWave. Rates are fetched live from `cdn.jsdelivr.net/.../fawazahmed0/currency-api/...` and held in an in-memory Guava cache only.
4. **Three patterns we should adopt that we hadn't designed for:**
   - **Hierarchical categories via PostgreSQL `ltree`** — see §2.1 below. Adds to our schema.
   - **Polymorphic transactions via `transactions_metadata(type, arg) + per-type sub-tables`** — see §2.2. Cleaner than a single fat table for FX-conversion vs. plain-cash transactions.
   - **Two-table notification pipeline (`notifications_pull` queue drained by a 1-second worker)** — see §2.4. Lightweight inbox without Redis/celery.

The result: the design doc's §0 (Locked Decisions D1-D10) is still correct. §4 (domain model) needs three additions documented in §6 of this doc.

## 2. FinWave-Backend deep-dive (Java, Spark, jOOQ, Flyway)

Cloned at `research/FinWave-Backend/`. Single Flyway migration `V1.0.0__base.sql` was directly readable; later migrations were inferred from jOOQ access classes. The summary below is what we can verify; complete column lists are in the deep-dive transcript.

### 2.1 Domain tables

Verbatim from `V1.0.0__base.sql`:

- `users(id serial PK, username text not null unique, password text not null)` — PBKDF2-HMAC-SHA512, 8192 iterations, base64 (`PBKDF2.java:23-24, 65`).
- `users_sessions(id bigserial PK, user_id integer FK, token text not null unique, created_at, expires_at, description text)` — bearer-token auth. A `limited boolean` column added later (`SessionDatabase.java:29`) gates sensitive ops.
- `users_settings(id, user_id, language varchar(16), time_zone text)`.
- `notes(id, owner_id, notification_time timestamptz, last_edit timestamptz, note text)` — reminders/notes domain.
- `accounts_tags` (later renamed `accounts_folders`) — `(id, owner_id, name, description)`.
- `accounts(id, owner_id, tag_id/folder_id FK, currency_id FK, amount numeric, hidden boolean, name, description)` — bank/cash account.
- `transactions_tags` (later renamed `categories`) — `(id, owner_id, type smallint, parents_tree ltree, name, description)`. **Hierarchical categories via the `ltree` extension** (created at `V1.0.0__base.sql:1`).
- `currencies(id, owner_id, code text, symbol, decimals smallint, description)` — **per-user copies**. No unique on `code`. Defaults are owned by user id=1 and seeded via `DefaultCurrencies.java:6-13` (USD, EUR, GBP, JPY, RUB).
- `transactions(id, owner_id, tag_id/category_id FK, account_id FK, currency_id FK, created_at timestamptz, delta numeric, description)` — `delta` carries sign (positive=income, negative=expense).
- `recurring_transactions(...)` — same shape as transactions plus `repeat_func smallint` (enum index), `repeat_func_arg`, `notification_mode`, `last_repeat`, `next_repeat`.

Inferred from jOOQ usage (later migrations not directly readable):

- `categories_budgets` — `(id, owner_id, category_id, currency_id, date_type smallint, amount numeric)` — `CategoryBudgetDatabase.java:20-28`.
- `accumulation_settings` — savings-bucket rules; unique on `source_account_id` — `AccumulationDatabase.java:21-34`.
- `transactions_metadata(id, type smallint, arg bigint)` — polymorphic dispatch for transaction variants. `MetadataType` enum: `WITHOUT_METADATA=0, INTERNAL_TRANSFER=1, RECURRING=2, HAS_ACCUMULATION=3` (`MetadataType.java:4-7`).
- `internal_transactions_metadata(id, from_transaction_id, to_transaction_id)` — links the two legs of a cross-account / cross-currency transfer.
- `notifications_pull(id, text, options jsonb, user_id, created_at)` — push-queue inbox.
- `notifications_points(id, user_id, is_primary boolean, type smallint, created_at, data jsonb, description)` — destination per user; `NotificationPointType` enum is `WEB_PUSH | WEB_SOCKET` (`NotificationPointType.java:3-6`).
- `files`, `reports`, `ai_contexts`, `ai_messages` — auxiliary subsystems (LLM features and PDF reports).

### 2.2 FX / multi-currency: live-only, no history

`ExchangeManager.java:46-50` builds a Guava `Cache` with `expireAfterWrite(config.hoursCaching, TimeUnit.HOURS)`. On miss, `fawazahmed0Fetch(currencyCode, 0)` (`ExchangeManager.java:84`) hits `<server>/<code>.min.json`, parses with Gson, and bulk-inserts every paired rate into the cache. Returns `BigDecimal.valueOf(-1)` to signal unavailable (`ExchangeManager.java:54, 64, 74`).

There is **no `exchange_rates` table**. There is **no historical-rate query path**. There is **no concept of weighted-average / cost-basis** anywhere in the schema or services. Cross-currency transfers are modelled as two independent rows in `transactions` (one per account), linked through `internal_transactions_metadata`. The applied rate is implicit in the two `delta` values and is **never persisted explicitly** (`InternalActionsWorker.java:32-39`, `MetadataDatabase.java:33-43`). For our weighted-average headline feature this is a hard gap; we must design from scratch.

### 2.3 Multi-tenancy: flat single-owner

Every domain table carries `owner_id INTEGER → users(id)`. There is no `books`, `workspaces`, `households`, `groups`, `members`, or `invites` table. Authorization is per-class predicates: `userOwnAccount` (`AccountDatabase.java:58-64`), `userOwnCategory` (`CategoryDatabase.java:53-59`), etc. The single role-like distinction is `record.getUserId() != 1` for admin gating (`AuthApi.java:74`) — a hardcoded "user-id 1 is admin" check.

Currencies have a two-tier read rule: any user can read their own + root user 1's defaults (`CurrencyDatabase.userCanReadCurrency` at `:85-93`); only the owner can edit (`:95-101`). This `WHERE owner_id = userId OR owner_id = 1` pattern is worth lifting for our **per-book custom currencies** (let books override or extend a system catalogue without duplicating rows).

### 2.4 Background jobs: plain ScheduledExecutorService, no Redis

`ServicesManager.java:37` uses `Executors.newScheduledThreadPool`. Four services:

- `RecurringService` — every 1 minute, polls `recurring_transactions` where `next_repeat <= now()`, applies, recomputes `next_repeat` via `NextRepeatTools.calculate(...)` (`RecurringService.java:33-66`).
- `NotificationsService` — every 1 second, drains `notifications_pull` via a `DELETE ... RETURNING ... ORDER BY created_at LIMIT n` query (`NotificationDatabase.java:35-47`), then `NotificationManager.pushImmediately`. Two-table pattern: synchronous attempts go directly; if rate-limit exceeded, the message is parked in `notifications_pull` for the worker to drain (`NotificationManager.java:84-98`). **No Redis. No external queue.**
- `NotesService` — every 30 seconds, surfaces note reminders (`NotesService.java:30`).
- `FilesService` — every 1 hour, GC of expired files (`FilesService.java:33-46`).

### 2.5 HTTP API: Spark Java, hand-rolled

All routes declared imperatively in `HttpWorker.java:117-286` via `path("/...", () -> { ... })`. Auth is bearer-token via `Authorization: Bearer <token>` header (`AuthApi.java:39-42`); validated by Guava-cached lookup in `users_sessions` (`SessionManager.java:30, 60-68`). Sessions can be marked `limited` to refuse password-change-style ops (`UserApi.java:94-98`).

This is a hand-rolled style we do not need to mimic — FastAPI + Pydantic gives us typed routes, OpenAPI, and validation for free.

### 2.6 Telegram integration: zero

There is no bot token config, no `initData` HMAC validation, no Telegram user ID column on `users`, no `/telegram/*` route, no Telegram-specific notification point. Notification dispatch is web-push (`nl.martijndwars:web-push:5.1.1`) and WebSocket. The Telegram bot (next section) is a separate process that consumes the public REST/WS API.

## 3. FinWave-Telegram-Bot deep-dive (Java thin client)

Cloned at `research/FinWave-Telegram-Bot/`. The substantive logic (HTTP client, request DTOs, WebSocket framing, scene/menu primitives) lives in two private Maven artifacts: `app.finwave.api:finwave-java-api:1.5.0` and `app.finwave.tat:telegram-abstractions-tools:2.1.3`. This repo is orchestration glue.

### 3.1 UX shape: single rolling message + scenes

The bot does not operate as a transcript. It owns one inline-keyboard message per chat and edits it. The `message_id` is persisted in `chats.last_message` (`ChatHandler.java:36-39`). Scenes (`InitScene`, `MainScene`, `SettingsScene`, `NotificationScene`) are pre-registered once on the chat handler (`ChatHandler.java:31-34`); transitions are imperative `stopActiveScene()` + `startScene("name")`. Per-scene state lives in instance fields. **There are no slash commands** — no `/start`, no `/help`, no `setMyCommands`. The first message in a private chat triggers `InitScene`; everything else flows through `MainScene` and inline-button taps.

### 3.2 Account linking: manual session paste — REJECTED

`InitScene.askSession()` (`InitScene.java:133-203`) instructs the user (in Russian) to log into the FinWave web UI, mint a session token in the Sessions tab, and paste it into the chat. The bot then constructs `FinWaveClient(serverUrl, session)` and stores `(chatId, apiUrl, session, type, lastMessage)` in its local `chats` table.

We will not replicate this. Telegram WebApp `initData` HMAC verification (against `BOT_TOKEN`) is the canonical Mini App auth surface and we have to implement it anyway. The FinWave linking flow is a workaround for not having implemented WebApp auth.

### 3.3 Mini-App handoff: deep-link with `?autologin=`

`MainScene.update()` (`MainScene.java:424-432`) builds `https://<host>/?autologin=<client.getToken()>` and either attaches it as a `WebAppInfo` button (private chat) or a plain URL (group chat). The query-param `autologin` carries the long-lived session token directly to the SPA. **This is unsafe** — in our system the equivalent must be a short-lived (≤60s) one-time JWT bound to `chat_id`. Pattern shape is right; security is wrong.

### 3.4 Backend channels: REST + WebSocket

REST through `FinWaveClient.runRequest(IRequest<R>) -> CompletableFuture<R>` (`MainScene.java:106`, `ClientState.java:62-79`). WebSocket through `client.connectToWebsocket(handler)` (`MainScene.java:122`); the handler subscribes to `notifyUpdate` / `notification` / `authStatus` / `notificationPointRegistered` callbacks (`WebSocketHandler.java:31-75`). Authed handshake is a `CompletableFuture<Boolean>` waited on for up to 5s (`MainScene.java:128`). After auth, the bot either registers a fresh notification point (`NewNotificationPointRequest("Telegram Bot", false)`, `MainScene.java:137`) or resubscribes with a stored UUID (`SubscribeNotificationsRequest(uuid)`, `MainScene.java:139`).

The two-channel split is a good pattern. The WS handler swaps in `NotificationScene` when an alert arrives (`WebSocketHandler.java:54-57`, `NotificationScene.notify` `:72-78`), preserving prior UI state.

### 3.5 NLP-lite intake: ActionParser

`ActionParser.parse(text, preferredAccountId)` (`ActionParser.java:86-147`) tokenises the message, finds the numeric delta, runs Jaccard similarity against account-folder names + transaction-category names, and returns either a `TransactionApi.NewTransactionRequest` or, if the message starts with `!`, a `NoteApi.NewNoteRequest`. Lightweight and surprisingly effective. Worth replicating in our intake handler — `rapidfuzz` in Python gives the same affordance.

### 3.6 Anti-patterns we reject from this repo

- **Hard-coded Russian strings everywhere** (e.g. `MainScene.java:150-482`, `GPTMode.java:4-6`). No `ResourceBundle`, no i18n. Our EN+RU mandate forbids this.
- **Blocking `.get()` on `CompletableFuture` inside event handlers** (`MainScene.java:128, 388, 441-446`). In Python aiogram everything must be `await`ed natively.
- **Single shared JDBC `Connection`** (`DatabaseWorker.java:43-45`) with no pool. We start with `asyncpg` pooling on day one.
- **Conflating session/connection with FSM state** in scene instance fields (`MainScene.java:105-141, 71, 185, 211`) — a `dict[chat_id, Session]` outside the FSM is cleaner.

## 4. AiogramBotTemplate deep-dive (Python, MIT)

Cloned at `research/AiogramBotTemplate/`. Origin: `arturboyun/AiogramBotTemplate`. ~600 LOC. Python 3.12 + uv + aiogram 3.13 + aiogram-dialog + Dishka + FastAPI + SQLAlchemy 2.x async + asyncpg + Alembic + Redis + Docker. License: MIT (Artur Boyun, 2024).

### 4.1 Architecture: bot+API in one process, mode-switched

There is one entry point — `bot/__main__.py` — which branches on `USE_WEBHOOK`:

```python
if config.USE_WEBHOOK:
    uvicorn.run(app, host="0.0.0.0", port=8000)
else:
    asyncio.run(start_pooling())
```

In webhook mode, the FastAPI `app` (`api/main.py:28`) hosts a single route `POST /api/v1/webhook` that calls `dp.feed_webhook_update(bot=bot, update=update)`. The Bot and Dispatcher singletons are created at import time in `bot/misc.py:12-18` and shared between the polling and webhook paths. **Single Postgres engine, single Redis connection, single process.** `compose.yml:1-13` has only a `bot:` service.

We will likely split this for prod (separate `apps/api` for the Mini-App REST + `apps/bot` for polling/webhook) but keep the unified shape for local dev.

### 4.2 Dishka DI: one provider, one binding

`DepsProvider` in `bot/ioc.py:8-12` registers a single request-scoped binding:

```python
class DepsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_uow(self) -> AsyncGenerator[UoW, None]:
        async with SessionFactory() as session:
            yield UoW(session)
```

Wired into the dispatcher in `bot/main.py:44-45`: `make_async_container(DepsProvider())` then `setup_dishka(container=container, router=dp)`. Aiogram middleware opens the request scope per Telegram update. **Dishka is NOT integrated with FastAPI** — webhook handlers can't `FromDishka[UoW]` out of the box. We must add `dishka.integrations.fastapi.setup_dishka` ourselves.

### 4.3 SQLAlchemy 2 async: clean Base, Annotated types

`bot/models/base.py:1-33` has the patterns we want to lift verbatim: `MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)`, `Base(AsyncAttrs, DeclarativeBase, __abstract__=True)` with `created_at`/`updated_at` timezone-aware columns. `bot/models/fields.py:8-19` defines `Annotated` types `uuid_pk` (UUID primary key with `gen_random_uuid()` server default) and `chat_id_bigint` (`BigInteger` unique).

There is one toy domain model: `User(id uuid_pk, chat_id BigInt unique, username str?, first_name str, last_name str?, blocked bool)` (`bot/models/user.py:6-13`). No accounts, no transactions, no currencies. We add ours.

### 4.4 Migrations: async-aware Alembic

`migrations/env.py:69-84` runs `async_engine_from_config(... poolclass=pool.NullPool)`, opens a connection, calls `connection.run_sync(do_run_migrations)`. DSN is injected at runtime from `bot.config.get_config()` so migrations never hit a hard-coded URL (`migrations/env.py:34-35`). Models are explicitly imported at `migrations/env.py:25-26` — there is no auto-discovery glob, so we will add an `__init__.py` aggregator or maintain the explicit list.

`alembic.ini:10` uses date-prefixed file template. `alembic.ini:77-80` runs `ruff format` as a post-write hook, which we keep.

### 4.5 Aiogram + aiogram-dialog: Redis FSM + one toy dialog

`bot/misc.py:12-13`:

```python
key_builder = DefaultKeyBuilder(with_destiny=True)
storage = RedisStorage.from_url(str(config.REDIS_DSN), key_builder=key_builder)
dp = Dispatcher(storage=storage)
```

The `with_destiny=True` flag is non-obvious but required for aiogram-dialog to share storage cleanly with regular FSM. Worth keeping.

There is exactly one dialog (`menu_dialog`, `bot/dialogs/menu/dialog.py:8-16`), with a single state and two URL buttons. **Not a useful example of a multi-step flow.** We design our dialogs from scratch.

The `/start` handler (`bot/handlers/commands.py:17-26`) gates the dialog with `AccessSettings(config.ADMIN_IDS)` — admin-only by default. We remove this.

### 4.6 What's missing vs our needs

A non-exhaustive list (full list in deep-dive transcript §13):

1. **i18n** — README marks it `~~I18n~~ (TODO)`. We need EN + RU from day one. Adopt Fluent (`aiogram-i18n` with `fluent.runtime`).
2. **Telegram WebApp `initData` HMAC verification** — entirely absent. Primary auth surface for our Mini-App. We design.
3. **JWT auth for the Mini-App API** — no `pyjwt` / `authx` / `OAuth2PasswordBearer`. We add.
4. **FastAPI ↔ Dishka integration** — only aiogram has it. We add `dishka.integrations.fastapi`.
5. **Background workers** — no `arq` / `celery` / `taskiq`. We need one for FX-rate refreshes and report generation.
6. **Sentry / observability / structured logs** — `bot/utils.py:6-8` only sets `logging.basicConfig`. We add `structlog` + `sentry-sdk` + a `/healthz` endpoint.
7. **Repository layer** — `UoW` only exposes `commit/rollback/close`. We add `repositories/` and `services/`.
8. **Tests + CI** — no `tests/`, no `.github/`. We add pytest + GitHub Actions matrix.
9. **Initial migration** — `migrations/versions/` is empty. We will commit an initial migration with our base schema.
10. **Healthcheck on bot service** — `compose.yml` has none. We add `/healthz` and a `curl` healthcheck.
11. **Two-process split** for prod scaling — current design fuses bot+API. We split into `apps/api` and `apps/bot` containers in our monorepo while keeping the unified mode for `pnpm dev`.
12. **Inconsistencies to fix:** `.env.dist:18` uses DB name `/bot` while `compose.yml:18` sets `POSTGRES_DB=notify_bot`. `API_HOST` in `.env.dist:13` lacks a scheme.

### 4.7 Cherry-pick list (~12 files)

Lift verbatim or near-verbatim into our monorepo:

1. `bot/models/base.py:1-33` → `apps/bot/models/base.py` and shared with API. Naming convention + timestamped Base.
2. `bot/models/fields.py:1-19` → `apps/bot/models/fields.py`. `uuid_pk`, `chat_id_bigint`.
3. `migrations/env.py:1-96` → `migrations/env.py`. Async-aware setup.
4. `alembic.ini:1-115` → `alembic.ini`. Especially `file_template` + ruff post-write hook.
5. `bot/database/db.py:1-9` → `apps/bot/database/engine.py`. Engine + sessionmaker.
6. `bot/common/uow.py:1-27` → `apps/bot/common/uow.py`. Minimal UoW (we extend with repositories).
7. `bot/ioc.py:1-12` → `apps/bot/ioc.py`. Request-scoped UoW provider.
8. Pattern from `bot/__main__.py:1-23` — `USE_WEBHOOK` switch (we adapt to two entry points).
9. Pattern from `bot/main.py:42-58` — exact boot order: `make_async_container` → `setup_dishka(container, dp)` → `dp.include_router` → `setup_dialogs(dp)`.
10. `bot/misc.py:1-18` → `apps/bot/storage.py`. Redis FSM with `with_destiny=True`.
11. Pattern from `api/main.py:17-50` — FastAPI lifespan (`setup_webhook` on enter, `delete_webhook` on exit) + `X-Telegram-Bot-Api-Secret-Token` header check (we promote to 401 + FastAPI dependency).
12. `bot/config.py:1-51` — pydantic-settings shape + `@lru_cache get_config()`. Replace fields with our own.

Bonus patterns:

- `Dockerfile:13-23` — two-step `uv sync` with bind-mount cache.
- `compose.yml:18-32` + `compose.yml:51-53` — Docker secret pattern for Postgres password.
- `bot/main.py:32-39` — global aiogram error handler that resets dialog stack to a known state.

## 5. Patterns to adopt across all three references (consolidated)

This list extends §8 of the prior design doc.

1. **Hierarchical categories via PostgreSQL `ltree`** — FinWave's `parents_tree ltree NOT NULL` (`V1.0.0__base.sql:70`) with `<@` containment queries (`CategoryDatabase.java:96`). In SQLAlchemy use `sqlalchemy_utils.LtreeType`. Add a `categories.parents_tree` column to our schema and a `category_path` computed property. Postgres extension `ltree` must be loaded in our base migration.
2. **Polymorphic transactions via metadata + per-type sub-tables** — FinWave's `transactions_metadata(type smallint, arg bigint)` with `MetadataType` enum and per-type sub-tables (`internal_transactions_metadata`, etc.). Adopt for our **FX-conversion transactions** and **internal transfers**: a `fx_transactions` row points to either a regular cash transaction metadata or to a "conversion pair" metadata that records the explicit weighted rate.
3. **ActionsWorker strategy dispatch** — `HashMap<MetadataType, TransactionActionsWorker>` (`TransactionsManager.java:41, 56-59`) with a single `apply/edit/cancel` interface and pre/post hooks. Translate to a Python protocol (`class TransactionActionsWorker(Protocol)`) keyed by enum.
4. **Two-table notification pipeline** — synchronous push attempt → fall back to `notifications_pull` queue → 1-second drain worker. Avoids Redis/celery for our MVP notification path. Use `arq` later if we outgrow it; the table-based outbox keeps the system observable from `psql`.
5. **DB-stored bearer tokens with `limited` flag** — FinWave's `users_sessions(token text unique, limited boolean, expires_at)`. Validates our D8 design. Implement: web-session tokens are full-access; Mini-App tokens minted from `initData` are `limited=true` so they cannot rotate password or revoke other sessions.
6. **Per-user/per-book overrides on a global catalogue** — FinWave's `WHERE owner_id = userId OR owner_id = 1` for currencies. Adopt for our **per-book custom currencies**: a system catalogue (book_id NULL) plus per-book overrides.
7. **Single rolling Telegram message UX** — FinWave-Telegram-Bot's pattern of editing one pinned inline-keyboard message per chat (`MainScene.java:441-450`). Aiogram analog: store `message_id` in our `tg_chats` table and `bot.edit_message_text` on each state change.
8. **Notification scene swap-in with state preservation** — `WebSocketHandler.notification` swaps in `NotificationScene` in front of `MainScene` (`WebSocketHandler.java:54-57`); on dismiss it returns. Aiogram-dialog supports this via dialog-stack push/pop.
9. **NLP-lite intake parser** — Jaccard similarity over category/account names with a numeric delta extractor (`ActionParser.java:86-147`). Use `rapidfuzz` in Python; gives users frictionless `300 кофе наличные` → "expense, ₽300, category=кофе, account=наличные".
10. **WebSocket push channel from backend → bot** — FinWave's WS for live updates (`WebSocketHandler.java:31-75`). For our FX-rate alerts, the bot keeps a long-lived WS to the API; the API broadcasts on rate-tick events.
11. **`Annotated` SQLAlchemy types for repeated column patterns** — `uuid_pk`, `chat_id_bigint` from AiogramBotTemplate. Extend with `book_fk`, `currency_code`, `money_amount` (NUMERIC(20,8)).
12. **Async Alembic + ruff post-write hook** — straight from AiogramBotTemplate.
13. **Redis FSM with `with_destiny=True`** — required for aiogram-dialog co-existence.
14. **FastAPI lifespan to register/deregister Telegram webhook** — clean pattern.
15. **`@lru_cache` config singleton** — pydantic-settings `get_config()` factory.

## 6. Updates required to the design doc

The 2026-04-23 design doc needs three additions in §4 (domain model) before we can produce the MVP plan. Each is small.

### 6.1 Add `categories` table with `ltree` path

```sql
CREATE EXTENSION IF NOT EXISTS ltree;

CREATE TABLE categories (
    id           BIGSERIAL PRIMARY KEY,
    book_id      BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    parents_tree ltree NOT NULL,                       -- materialised path
    kind         SMALLINT NOT NULL,                    -- income | expense | both
    name         TEXT NOT NULL,
    description  TEXT,
    archived     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX categories_book_path_gist ON categories USING GIST (book_id, parents_tree);
```

Used to scope categories per book; the GIST index keeps `<@` containment queries fast.

### 6.2 Add `transaction_metadata` + `transaction_links` for polymorphic transactions

```sql
CREATE TYPE transaction_kind AS ENUM (
    'plain_cash',          -- single-leg cash flow
    'internal_transfer',   -- two-leg same-currency transfer
    'fx_conversion',       -- two-leg cross-currency with explicit rate
    'recurring_apply',     -- generated by recurring_transactions
    'accumulation_apply'   -- savings rule auto-transfer
);

ALTER TABLE fx_transactions
    ADD COLUMN kind transaction_kind NOT NULL DEFAULT 'plain_cash',
    ADD COLUMN linked_transaction_id BIGINT NULL REFERENCES fx_transactions(id);

CREATE INDEX fx_transactions_linked ON fx_transactions(linked_transaction_id) WHERE linked_transaction_id IS NOT NULL;
```

`linked_transaction_id` covers the two-leg cases without a separate metadata table — simpler than FinWave's `transactions_metadata + per-type sub-tables` because we have a single `fx_transactions` table to begin with. The kind enum carries the dispatch information for the ActionsWorker pattern (§5 #3).

### 6.3 Add `notifications_outbox` table

```sql
CREATE TABLE notifications_outbox (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id       BIGINT NULL REFERENCES books(id) ON DELETE CASCADE,
    kind          TEXT NOT NULL,                      -- e.g. 'rate_alert', 'low_balance'
    payload       JSONB NOT NULL,
    delivered_at  TIMESTAMPTZ NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempts      SMALLINT NOT NULL DEFAULT 0
);
CREATE INDEX notifications_outbox_pending ON notifications_outbox(created_at) WHERE delivered_at IS NULL;
```

Drained by an `arq` worker every 1-2 seconds; rows are soft-deleted (`delivered_at = now()`) on success and retried on failure. Replaces FinWave's two-table pattern with a single soft-delete table — same observability, fewer joins.

The rest of the schema stands. The `exchange_rates` table from §4.x of the design doc is unaffected — FinWave doesn't have one, so we have nothing to copy or reject.

## 7. Open questions (still)

1. **Categorisation source-of-truth on conflict** — when our weighted-avg rate disagrees with a user-supplied rate on an `fx_conversion`, which wins? Recommend: **user-supplied wins for the row, but the book's running weighted avg ignores user-supplied rate when computing — only the per-leg `amount_quote` and `amount_base` go in.** Confirm before MVP.
2. **i18n scope for backend errors** — does the FastAPI surface return localised error messages, or always English with code? Recommend English-with-code, localised in the bot/Mini-App layer. Confirm.
3. **Mini-App initData token lifetime** — how short? Telegram says treat `initData.auth_date` as fresh for 24h; our minted JWT should be ≤30 minutes with refresh on every Mini-App focus event. Confirm.
4. **Categories path mutability** — when the user reparents a category, do we cascade-update `parents_tree` for descendants (`UPDATE ... SET parents_tree = subpath_replace(...)`) or freeze child paths? Recommend cascade for UX consistency. Confirm.
5. **Per-book vs per-user `tg_chats` linking** — FinWave-Telegram-Bot links chat → session (i.e. user). We need `tg_chats(chat_id, user_id, active_book_id NULL)` so a user can switch the chat's active book. Confirm shape.

## 8. Next steps (revised)

1. **Resolve the open questions in §7 of this doc and §7.2 of the prior design doc.** I'll send a single AskUserQuestion batch when we're ready to plan.
2. **Produce the MVP plan** at `thoughts/shared/plans/2026-05-XX-mvp-scope-and-milestones.md`. The schema additions in §6 of this doc go into the plan's Phase 1 milestone alongside the §4 base schema from the design doc.
3. **Bootstrap the monorepo per design doc §6** — pnpm + Turborepo, uv workspace, ruff/mypy/pre-commit, biome/vitest, docker-compose with postgres+redis+backend+worker+miniapp+caddy. **Cherry-pick the 12 files in §4.7** of this doc when wiring `apps/bot` and `apps/api`.
4. **Spike Telegram initData auth + book-membership resolution** as the first end-to-end test. This is the auth surface that AiogramBotTemplate explicitly does not provide.
5. **Ship weighted-avg-rate vertical slice as the first feature** — tables, repository, service, API endpoint, bot command, Mini-App card. Demonstrates the headline value end-to-end.

## 9. Adoption recipe (for bootstrapping)

Concrete commands when we start the monorepo:

```bash
# In the monorepo root, after creating apps/bot/ and apps/api/:

# Lift Base + fields verbatim:
cp research/AiogramBotTemplate/bot/models/base.py     apps/bot/src/smart_accounting/models/base.py
cp research/AiogramBotTemplate/bot/models/fields.py   apps/bot/src/smart_accounting/models/fields.py
cp research/AiogramBotTemplate/bot/common/uow.py      apps/bot/src/smart_accounting/common/uow.py
cp research/AiogramBotTemplate/bot/database/db.py     apps/bot/src/smart_accounting/database/engine.py
cp research/AiogramBotTemplate/bot/ioc.py             apps/bot/src/smart_accounting/ioc.py
cp research/AiogramBotTemplate/migrations/env.py      apps/bot/migrations/env.py
cp research/AiogramBotTemplate/migrations/script.py.mako apps/bot/migrations/script.py.mako
cp research/AiogramBotTemplate/alembic.ini            apps/bot/alembic.ini

# Then:
# - retain the MIT copyright header in those files
# - add THIRD_PARTY_NOTICES.md crediting Artur Boyun and the FinWave team
# - update naming: package name 'bot_template' -> 'smart_accounting'
# - extend Base with our domain models (books, book_members, currencies, exchange_rates, accounts, fx_transactions, categories, transaction_links, notifications_outbox)
```

## Appendix A — files and references touched

**Cloned references:**
- `/Users/raiqasvl/Enterprise/web-development/0-FreeLance/smart-accounting-hub/research/FinWave-Backend/`
- `/Users/raiqasvl/Enterprise/web-development/0-FreeLance/smart-accounting-hub/research/FinWave-Telegram-Bot/`
- `/Users/raiqasvl/Enterprise/web-development/0-FreeLance/smart-accounting-hub/research/AiogramBotTemplate/`

**Key files from FinWave-Backend:**
- `src/main/resources/db/migration/V1.0.0__base.sql` — base schema
- `src/main/java/.../service/ExchangeManager.java` — live-rate fetch + cache
- `src/main/java/.../service/TransactionsManager.java` — ActionsWorker dispatch
- `src/main/java/.../service/NotificationManager.java` + `NotificationsService.java` — two-table outbox
- `src/main/java/.../api/AuthApi.java`, `SessionDatabase.java`, `SessionManager.java` — bearer-token auth
- `src/main/java/.../HttpWorker.java` — Spark Java route declarations
- `src/main/java/.../database/CategoryDatabase.java` + `BudgetTree.java` — `ltree` usage

**Key files from FinWave-Telegram-Bot:**
- `src/main/java/.../scenes/MainScene.java`, `InitScene.java`, `SettingsScene.java`, `NotificationScene.java`
- `src/main/java/.../utils/ClientState.java`, `ActionParser.java`, `WebSocketHandler.java`
- `src/main/java/.../handlers/ChatHandler.java`
- `src/main/java/.../database/ChatDatabase.java`, `ChatPreferenceDatabase.java`

**Key files from AiogramBotTemplate:**
- `pyproject.toml`, `alembic.ini`, `compose.yml`, `Dockerfile`, `.env.dist`
- `bot/__main__.py`, `bot/main.py`, `bot/misc.py`, `bot/config.py`, `bot/ioc.py`
- `bot/common/uow.py`, `bot/database/db.py`
- `bot/models/base.py`, `bot/models/fields.py`, `bot/models/user.py`
- `migrations/env.py`, `migrations/script.py.mako`
- `api/main.py`

## Appendix B — what we now know FinWave does NOT have

A short list, in case it surfaces in future questions. Each is a confirmed gap from this deep-dive — none of these should be "ported" because they don't exist:

- ❌ `exchange_rates` table (rates are in-memory cache only)
- ❌ Weighted-average / cost-basis / FX P&L logic
- ❌ Books / workspaces / households / shared accounts
- ❌ Roles (owner/admin/editor/viewer) and invite flow
- ❌ Telegram WebApp `initData` HMAC verification
- ❌ JWT auth (uses opaque DB-backed bearer tokens)
- ❌ i18n (the bot is Russian-only; backend has `users_settings.language` but no localised payloads)
- ❌ Tests, CI workflows, structured logs, Sentry, OpenAPI generation
- ❌ Crypto-asset accounting (FinWave's currencies table is fiat-shaped)
- ❌ Any precision contract on money columns (`numeric` is unbounded)
