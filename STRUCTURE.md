# Architecture Specification

> Living document. Last revised 2026-05-04. Companion to:
>
> - `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` — milestone-by-milestone *what* to build (D1–D32 locked).
> - `thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md` — *why* we chose these patterns (and what we deliberately rejected).
>
> This file is the single-page "how the system fits together". Use it to interrogate the design before code goes in.

---

## 1. System at one glance

```text
                                  ╔══════════════════╗
                                  ║   USER SURFACE   ║
                                  ╚════════╦═════════╝
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
     ┌───────────────┐         ┌────────────────────┐        ┌──────────────────────┐
     │  Telegram     │         │   Telegram WebApp  │        │  (anyone with the    │
     │  client (chat)│         │   inside Telegram  │        │   API URL — devtools)│
     └───────┬───────┘         └─────────┬──────────┘        └──────────┬───────────┘
             │ long-poll                 │ HTTPS via                    │ HTTPS via
             │ updates                   │ cloudflared tunnel           │ cloudflared tunnel
             │                           │                              │
             ▼                           ▼                              ▼
     ╔═══════════════╗         ╔═════════════════════╗     ╔══════════════════════╗
     ║  apps/bot     ║         ║   apps/miniapp      ║     ║   apps/api           ║
     ║  python -m    ║         ║   Next.js 15 :3000  ║◀────║   FastAPI :8000      ║
     ║  smart_       ║         ║   (TS + shadcn +    ║     ║   uvicorn --reload   ║
     ║  accounting_  ║         ║    TanStack Query)  ║     ║                      ║
     ║  bot          ║         ║                     ║     ║                      ║
     ╚══════╦════════╝         ╚══════════╦══════════╝     ╚══════════╦═══════════╝
            │ direct python                │ HTTP+JWT                  │ python imports
            │ imports (Q4)                 │ (D12)                     │
            ▼                              ▼                           ▼
     ╔══════════════════════════════════════════════════════════════════════════════╗
     ║   packages/core — services, repositories, models, auth, fx, i18n        ║
     ║                                                                              ║
     ║   The single Python package that holds the entire domain. Both apps import.  ║
     ╚════════════════════════════════════╦═════════════════════════════════════════╝
                                          │
                          ┌───────────────┼───────────────┐
                          ▼                               ▼
                   ┌──────────────┐               ┌──────────────┐
                   │  Postgres 16 │               │   Redis 7    │
                   │  :5432       │               │   :6379      │
                   │  (docker)    │               │   (docker)   │
                   └──────────────┘               └──────────────┘

                   ╔══════════════════════════════════════════════╗
                   ║  Frankfurter (https://api.frankfurter.dev)   ║
                   ║  ← apps/api lifespan task, hourly fetch      ║
                   ╚══════════════════════════════════════════════╝
```

Local dev: every coloured box is a process running on your laptop. `apps/api` and `apps/bot` are `uv run`. `apps/miniapp` is `pnpm dev`. Postgres + Redis are in `ops/compose.yml`. Cloudflared exposes `:3000` over HTTPS so Telegram's WebView can fetch the Mini-App.

---

## 2. Process boundaries and what each owns

| Process | Language | What it owns | Crash impact |
|---|---|---|---|
| **`apps/bot`** | Python 3.12 | Telegram updates (commands, callback queries, dialog state). Single-replica polling worker. **Owns nothing persistent** — every action calls into `services/`. | Bot users see "I'm offline" until restarted. Mini-App users unaffected. |
| **`apps/api`** | Python 3.12 | HTTP surface for the Mini-App. JWT auth, REST endpoints, FX rate refresh task. | Mini-App returns errors. Bot keeps working. |
| **`apps/miniapp`** | TS / Next.js 15 | Browser/WebView UI. Reads `apps/api` over HTTPS. Stateless beyond TanStack Query cache + JWT in sessionStorage. | UI users see Telegram's "this site can't be loaded". Bot+API keep working. |
| **`packages/core`** | Python 3.12 | Domain logic, persistence, auth helpers, FX clients. **Imported by both apps; imports nothing app-specific.** | Cannot crash on its own — it's a library. |
| **`packages/api-types`** | TS | OpenAPI-generated client types + zod schemas + `Money` type. Imported by `apps/miniapp`. | Build-only artefact. |
| **Postgres** | — | All durable state. Source of truth. | All three apps stop working. `make up` restores. |
| **Redis** | — | Aiogram FSM state only. Ephemeral. | Bot loses in-flight dialog state; users restart their conversation. Everything else fine. |

### Q4-locked rule: bot bypasses the HTTP API

`apps/bot` calls `smart_accounting.services.*` directly via Python imports. **It never makes an HTTP request to `apps/api`.** Both processes share the same Postgres + Redis. CI grep-guard refuses any `from smart_accounting.{models,repositories}` import inside `apps/bot/src/` — bot must enter through the service layer, not below it.

---

## 3. Layering inside `packages/core`

```text
              ┌─────────────────────────────────────────────────────────┐
              │  apps/api/routers          apps/bot/handlers + dialogs  │  ← presentation
              └─────────────────┬───────────────────────┬───────────────┘
                                │                       │
                                ▼                       ▼
                       ┌────────────────────────────────────────┐
                       │  smart_accounting/services/            │  ← business logic
                       │  (auth_service, book_service,           │     (orchestrates
                       │   transaction_service, ...)             │      multiple repos
                       │                                          │      in one tx)
                       └─────────────────┬──────────────────────┘
                                         │
                                         ▼
                       ┌────────────────────────────────────────┐
                       │  smart_accounting/repositories/        │  ← persistence
                       │  (users, books, accounts,               │     (one file per
                       │   fx_transactions, reports, ...)        │      aggregate root,
                       │                                          │      no business
                       │                                          │      rules)
                       └─────────────────┬──────────────────────┘
                                         │
                                         ▼
                       ┌────────────────────────────────────────┐
                       │  smart_accounting/models/              │  ← schema
                       │  (User, Book, FxTransaction, ...)       │     (SQLAlchemy 2
                       │                                          │      DeclarativeBase)
                       └────────────────────────────────────────┘

              cross-cutting (used by services + repositories):
              · auth/          initData verification, JWT, RBAC matrix
              · common/uow.py  Unit-of-Work wrapper around AsyncSession
              · database/      engine + sessionmaker
              · fx/            Frankfurter client + refresh loop task
              · schemas/       Pydantic v2 wire-format types (Money, request bodies)
              · i18n/          Fluent message catalogues (en, ru)
              · data/          Static seed data (currency catalogue)
              · ioc.py         Dishka Provider classes
              · config.py      pydantic-settings shape
              · observability  structlog config (D17 deferred → plain stdlib for now)
```

### Strict rules

1. **Models know nothing.** They're SQLAlchemy classes only — no methods doing business logic, no validation beyond column constraints.
2. **Repositories don't open transactions.** They accept a `UoW` (or `AsyncSession`) and run queries. The caller (a service) is responsible for the transaction boundary.
3. **Services are the only place transactions begin and end.** They own UoW lifecycle (`async with uow:`), call repositories, enforce RBAC, dispatch hooks (e.g. notification outbox).
4. **Routers/handlers/dialogs are presentation only.** They:
   - parse the transport-shaped input (HTTP body / Telegram update)
   - resolve auth (JWT claim or telegram update payload)
   - call exactly one service method
   - render the result back into transport shape (Pydantic response model / `bot.edit_message_text`)
5. **Two distinct kinds of "models":**
   - `models/` = SQLAlchemy ORM (Postgres rows)
   - `schemas/` = Pydantic v2 (HTTP wire format)
   - These never share types. The service layer translates between them.

---

## 4. Module-dependency graph (must be acyclic)

```text
                     ┌───────────────────────────────┐
                     │       apps/miniapp (TS)       │
                     │       depends on:              │
                     └────────────┬───────────────────┘
                                  │ generated types
                                  ▼
                     ┌───────────────────────────────┐
                     │     packages/api-types        │  ← OpenAPI codegen output
                     │     api.d.ts, money.ts        │     + zod schemas
                     └───────────────────────────────┘

                     ┌──────────────┐    ┌──────────────┐
                     │  apps/api    │    │  apps/bot    │
                     │  (Python)    │    │  (Python)    │
                     └──────┬───────┘    └──────┬───────┘
                            │   imports         │   imports
                            └─────┬─────────────┘
                                  ▼
                     ┌───────────────────────────────┐
                     │     packages/core        │
                     │     (no upward dependency!)   │
                     └───────────────────────────────┘
```

**Hard rules:**

- `packages/core` imports **nothing from apps/**. If it ever needs to, that's a sign business logic leaked into a presentation layer — fix the layer, not the import.
- `apps/api` and `apps/bot` may **not import from each other**.
- `apps/miniapp` imports only `packages/api-types` (which itself is generated, no Python deps).

These constraints make the workspace a strict DAG. CI can verify with a static check (deferred until M5 returns).

---

## 5. Request lifecycle — Mini-App `POST /transactions`

```text
1. Mini-App (browser)
   ├─ Builds payload { book_id, direction, base_currency_code, ..., rate, amount_quote, ... }
   ├─ Money fields are strings (Q5)
   ├─ Adds Authorization: Bearer <jwt> + Idempotency-Key: <uuid> (D26)
   └─ POST /api/v1/transactions  ──────────────► apps/api

2. apps/api/routers/transactions.py
   ├─ FastAPI parses body → Pydantic schemas/transaction.TransactionCreate
   ├─ Depends() on current_jwt_claims() → decodes JWT, returns Claims(user_id, book_id, role, exp)
   ├─ Depends() on require("tx.write") → checks role permission against rbac.PERMISSIONS
   ├─ Depends() on uow: FromDishka[UoW] → opens AsyncSession
   └─ Calls services.transaction_service.record(uow, claims, schema)

3. services/transaction_service.py
   ├─ Re-validates business rules: account belongs to book, currency exists, etc.
   ├─ Computes amount_base = amount_quote * rate (Q5/D16)
   ├─ Calls repositories.fx_transactions.insert_or_get_idempotent(uow, ...)
   │  ├─ INSERT ... ON CONFLICT (book_id, idempotency_key) DO NOTHING RETURNING *  (D26)
   │  └─ If conflict, SELECT existing row and signal Idempotent-Replayed
   ├─ Optionally enqueues a notification outbox row (FinWave pattern)
   └─ uow.commit()

4. Back up the stack
   ├─ Service returns the FxTransaction model
   ├─ Router serialises via schemas.transaction.TransactionRead
   ├─ Pydantic emits JSON; Money fields become strings via PlainSerializer
   └─ Returns 201 Created (or 200 OK with `Idempotent-Replayed: true` header)

5. Mini-App
   ├─ TanStack Query cache invalidation on the transactions list query key
   ├─ UI shows the new row + animates the running balance
   └─ Round-trip: ~30-80 ms in dev, single Postgres roundtrip in service.
```

The exact same data path runs from `apps/bot` (RecordTradeDialog) — except step 1 is a Telegram update + dialog state, and there's no JWT (the bot is server-trust, identity from update payload). Steps 2-4 collapse since the bot doesn't go over HTTP. **Same service call, same uow boundary, same idempotency table.**

---

## 6. Auth flow — initData → JWT

```text
Telegram WebApp opens at https://*.trycloudflare.com/

  Mini-App                               apps/api                          smart_accounting.auth
  ───────                                ──────                            ─────────────
  1. window.Telegram.WebApp.ready()
  2. read initData (string, ≈300 bytes)
  3. POST /auth/telegram { init_data }   ─────────►
                                         4. router.auth.telegram(payload)
                                            └─► verify_init_data(init_data, BOT_TOKEN, max_age=86400)
                                                ├─ HMAC-SHA256(secret_key, data_check_string)
                                                ├─ secret_key = HMAC(b"WebAppData", BOT_TOKEN)
                                                ├─ constant-time compare
                                                ├─ check auth_date freshness
                                                └─ returns parsed { user, query_id, ... }
                                         5. auth_service.bootstrap_user(parsed)
                                            ├─ UPSERT users (telegram_user_id unique)
                                            ├─ if first time: auto-create personal book (D21)
                                            ├─ ensure book_members(role=OWNER)
                                            ├─ resolve active_book_id
                                            └─ returns (user, book, role)
                                         6. issue_token(user_id, book_id, role,
                                                        secret=JWT_SECRET, lifetime=1800)
                                            └─ HS256 JWT { sub, book_id, role, exp, iat, jti }
  7. ◀───── 200 { access_token, expires_in, user, book }
  8. store in sessionStorage
  9. set Authorization header on apiClient
  10. GET /me   ────────────────────────►   router.me.get
                                            └─ Depends current_jwt_claims (decodes JWT)
                                            └─ Depends current_user (loads from claims.sub)
                                            └─ returns { user, active_book, role, books[] }
  11. ◀───── 200 { ... }
  12. render dashboard

Refresh model (D27):
  - On 401 from any endpoint: re-run step 2-7 with fresh initData, retry the failed request.
  - On Telegram.WebApp.onEvent('viewportChanged'): if cached JWT < 5 min from exp,
    pre-emptively re-auth.
  - No refresh-token endpoint. initData is "the refresh token", verified server-side each time.
```

The bot has no JWT step. Telegram updates are trusted: the bot library validates the update came from Telegram (BOT_TOKEN-signed), and `update.from_user.id` is the canonical identity.

---

## 7. Bot UX — single rolling message + scenes

The bot owns **one inline-keyboard message per chat** and edits it on every state change. The `message_id` is persisted in `tg_chats.last_message_id` (D15). Pattern lifted from FinWave-Telegram-Bot's MainScene.

```text
Initial /start:
  ┌─────────────────────────────────────────────┐
  │ 👋 Welcome to Smart Accounting Hub.         │
  │ Your book "My personal book" is ready.       │
  │                                              │
  │ [📱 Open Mini-App]   [⚙️ Book settings]     │
  └─────────────────────────────────────────────┘
                                          tg_chats.last_message_id = 42

User taps [Book settings]:
  bot.edit_message_text(chat_id=..., message_id=42, ...)
  ┌─────────────────────────────────────────────┐
  │ ⚙️ Book settings                             │
  │ Name: My personal book                       │
  │ Base currency: USD                           │
  │ Members: 1 (you, owner)                      │
  │                                              │
  │ [✏️ Rename] [💱 Currency] [👥 Invite] [↩ Back]│
  └─────────────────────────────────────────────┘
                                          (same message_id, just replaced)

Notification arrives (e.g. "Member B accepted invite"):
  - WebSocket-style push is deferred (M5+).
  - At MVP, on next user interaction, NotificationScene replaces MainScene
    in front, with state preserved. Tapping Read returns to Main.
```

State machine on top of this UX is `aiogram-dialog`'s scene stack. Scenes:

- `MainScene` — dashboard (default)
- `SettingsScene` — book settings
- `RecordTradeDialog` — multi-step trade entry (M3)
- `InternalTransferDialog` — same-currency transfer (M4)
- `BookPickerDialog` — switch active book
- `LanguagePickerDialog` — EN/RU toggle

Each scene's input handler returns `start("scene_name", arg)` or `stop()`. Entering a scene swaps the rolling message; leaving restores the previous one.

---

## 8. Background work

At MVP, **one** asyncio task runs in `apps/api`'s lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(
        fx_refresh_loop(sessionmaker, http, interval_seconds=3600)
    )
    yield
    task.cancel()
```

`fx_refresh_loop` fetches Frankfurter every hour, INSERTs new `exchange_rates` rows. **No worker container at MVP.** When we add recurring transactions (v1.1), this whole loop migrates to `apps/worker` running `arq`.

`notifications_outbox` is just an audit log at MVP — the table exists, but nothing drains it. The drainer that pushes to Telegram via WebSocket lands in v1.1 alongside `apps/worker`.

---

## 9. Domain model — invariants

### Book-scoped multi-tenancy (D2)

Every domain row has `book_id NOT NULL` (except: `users`, `tg_chats`, `book_invites`, `exchange_rates`, system `currencies` rows). RBAC happens per `(book_id, user_id) → role`:

```text
                                 books
                                   │
                                   │ 1:N
                                   │
                ┌─────────────┬────┴────┬────────────┬────────────┐
                ▼             ▼         ▼            ▼            ▼
         book_members  accounts  categories  fx_transactions  notifications_outbox
              │
              │ (book_id, user_id) → role ∈ {0..3}
              ▼
         users (1:N tg_chats)

   roles:
     0=OWNER (one per book, hard-coded books.owner_id)
     1=ADMIN (full r/w + invite)
     2=EDITOR (r/w on tx + accounts + categories)
     3=VIEWER (read-only)
```

### Polymorphic transactions (D-deep-dive §6.2)

```text
fx_transactions
  ├─ kind: ENUM('plain_cash', 'internal_transfer', 'fx_conversion', ...)
  ├─ direction: ENUM('buy', 'sell')
  ├─ base_account_id, quote_account_id (one or both, depending on kind)
  └─ linked_transaction_id  ──── self-FK to the other leg of an internal_transfer / fx_conversion

  example: a "sell USD for RUB" trade is ONE row of kind='plain_cash', no linked partner.
  example: a "transfer Cash USD → Brokerage USD" is TWO rows of kind='internal_transfer',
           linked_transaction_id pointing at each other.
  example: a "convert Cash USD → Cash RUB at 90.27" is TWO rows of kind='fx_conversion',
           one in each currency, linked.
```

### Hierarchical categories via `ltree` (D14)

```text
categories.parents_tree LTREE NOT NULL
  GIST INDEX (book_id, parents_tree)

  'Food'                ⇐ root category
  'Food.Lunch'          ⇐ child
  'Food.Lunch.Cafe'     ⇐ grandchild

  Move: UPDATE categories
        SET parents_tree = subpath_replace(parents_tree, 'Food', 'Daily.Food')
        WHERE parents_tree <@ 'Food'
        ⇒ atomically rewrites all descendants in one SQL statement.
```

### Soft-delete (D29)

`books`, `accounts`, `categories`, `currencies`, `fx_transactions` carry `archived BOOLEAN NOT NULL DEFAULT FALSE`. List endpoints filter `WHERE NOT archived`. Hard-delete is reserved for: `book_invites` (purge expired), `exchange_rates` (TTL 90 days), `notifications_outbox` (purge 30 days post-delivery).

---

## 10. Configuration & secrets

```text
.env                          gitignored (chmod 600)
├─ BOT_TOKEN                  from @BotFather
├─ BOT_USERNAME
├─ JWT_SECRET                 32-byte random, used by HS256 signing (D12)
├─ JWT_LIFETIME_SECONDS       1800
├─ POSTGRES_DSN               postgresql+asyncpg://smart_accounting:<pwd>@localhost:5433/...
├─ REDIS_DSN                  redis://localhost:6380/0
├─ DOMAIN                     cloudflared subdomain (changes per restart); bot builds the Mini-App URL from it
├─ FRANKFURTER_BASE_URL
├─ FX_REFRESH_INTERVAL_SECONDS
├─ LOG_LEVEL
├─ ENVIRONMENT, DEBUG          ENVIRONMENT=production refuses to boot without BOT_TOKEN, JWT_SECRET, DOMAIN
└─ (deferred: SENTRY_DSN, RESTIC_*, B2_*)

The Mini-App reads no env vars: it calls the API by relative /api/v1/* paths.
Production .env lives on the droplet (template: deploy/.env.example; see docs/deploy.md).

db/password.txt               gitignored, mounted as Docker secret in compose.yml
                              MUST byte-equal the password in POSTGRES_DSN
                              (postgres container reads from /run/secrets/db-password,
                               python apps read from POSTGRES_DSN; same password)

`pydantic-settings` Config class in core/config.py
  - Reads .env at import time
  - Cached via @lru_cache get_config()
  - Same instance accessed by both apps
```

---

## 11. i18n architecture (D13, D31)

```text
API surface:                language-AGNOSTIC error codes
  { "error": { "code": "INVITE_EXPIRED", "params": { "expires_at": "..." } },
    "request_id": "req_abc" }

Bot side:                   Fluent .ftl files at packages/core/i18n/{en,ru}/main.ftl
  invite-expired = This invite expired on { DATETIME($expires_at) }.
  aiogram-i18n middleware reads users.language and selects bundle per update.

Mini-App side:              Fluent .ftl files at apps/miniapp/src/i18n/{en,ru}/main.ftl
  @fluent/bundle + @fluent/react. Locale derived from initDataUnsafe.user.language_code.

CI guard (M4):              `! grep -rE '"[А-Яа-я]' apps/{miniapp,bot}/src/ -l \
                               | grep -v -E 'i18n/ru/'`
                            ⇒ no hardcoded Cyrillic outside i18n/ru/.

Pydantic schemas:           english code names only.
                            UI never displays a code directly — always renders via Fluent template.
```

---

## 12. Naming conventions (consistency check)

| Entity | Plural? | Style | Example |
|---|---|---|---|
| Python package (top-level) | n/a | snake_case | `smart_accounting`, `smart_accounting_api`, `smart_accounting_bot` |
| Python module | n/a | snake_case | `auth_service.py`, `transaction_service.py` |
| Python class | n/a | PascalCase | `Book`, `FxTransaction`, `BookInvite`, `TransactionService`, `Money` |
| DB table | plural | snake_case | `users`, `books`, `book_members`, `fx_transactions`, `exchange_rates` |
| DB column | n/a | snake_case | `created_at`, `book_id`, `amount_quote`, `parents_tree` |
| FK column | suffix `_id` | snake_case | `book_id`, `created_by_user_id`, `linked_transaction_id` |
| Postgres enum type | singular | snake_case | `transaction_kind`, `transaction_direction` |
| Postgres index | naming convention | from `metadata` | `ix_fx_transactions_book_id_quote_currency_code_direction_occurred_at` |
| Pydantic schema | n/a | PascalCase verbed | `TransactionCreate`, `TransactionRead`, `BookListItem` |
| API URL | plural resource | kebab-case | `/api/v1/books`, `/api/v1/books/{id}/transactions` |
| API error code | singular | UPPER_SNAKE_CASE | `INVITE_EXPIRED`, `RATE_INVALID`, `BOOK_NOT_MEMBER` |
| Env var | n/a | UPPER_SNAKE_CASE | `BOT_TOKEN`, `JWT_SECRET`, `POSTGRES_DSN` |
| TS type / interface | n/a | PascalCase | `Money`, `TransactionCreate` |
| TS variable | n/a | camelCase | `apiClient`, `useTransactions` |
| Bot command | n/a | lowercase | `/start`, `/books`, `/avg`, `/lang` |
| Bot dialog | n/a | PascalCase + `Dialog` | `RecordTradeDialog`, `CreateBookDialog` |
| Fluent message id | n/a | kebab-case | `default-book-name`, `tx-rate-required` |

---

## 13. Locked decisions index (D1–D32)

> Cross-references for grep. Full text in `thoughts/shared/research/2026-04-23-yakov-bot-reference-analysis-and-smart-accounting-design.md` §0.3 (D1–D10) and `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` §0 (D11–D32).

| # | Subject | Status |
|---|---|---|
| D1–D10 | Stack, monorepo, audience, languages, money precision, books model, headline feature | locked |
| D11 | Caddy as reverse proxy | **deferred** (no reverse proxy in dev) |
| D12 | Mini-App auth = HS256 JWT, 30-min, claims `{sub, book_id, role, exp, iat, jti}` | locked |
| D13 | API errors are i18n-agnostic; UI localises | locked |
| D14 | `ltree` cascade on category reparent | locked |
| D15 | `tg_chats` shape (chat_id PK, active_book_id, last_message_id) | locked |
| D16 | User-supplied FX rate is row-authoritative | locked |
| D17 | Observability = structlog + Sentry | **deferred** (plain logging at MVP) |
| D18 | Backups = pg_dump + restic to B2 | **deferred** |
| D19 | CI = GitHub Actions | **deferred** |
| D20 | Secrets via .env + Docker secret for db password | locked (slimmed) |
| D21 | First /start = silent auto-create with language_code heuristic | locked |
| D22 | Bot architecture = direct service calls, no HTTP boundary | locked |
| D23 | Money on the wire = string | locked |
| D24 | Error envelope = `{ error: { code, params }, request_id }` | locked |
| D25 | Pagination = signed opaque cursor, no totals | locked |
| D26 | Default invite role = Editor | locked |
| D27 | JWT refresh = reactive on 401 + proactive on focus | locked |
| D28 | Idempotency = `fx_transactions.idempotency_key` partial unique index | locked |
| D29 | Soft-delete = `archived BOOLEAN` on most tables | locked |
| D30 | OpenAPI public in production | locked (n/a in dev) |
| D31 | Linter = oxlint, no ESLint | locked |
| D32 | Report time = compute period boundaries in user TZ | locked |

---

## 14. Open architectural questions (to interrogate)

This is the section meant for our grilling. None of these block M1; they shape M2-M4.

### 14.1 Where does FX-rate freshness fit in the user's workflow?

When a user is recording a trade in `RecordTradeDialog`, we want to **suggest the current rate** as a hint. The bot reads `exchange_rates` for the latest row, displays it. But:

- What if the latest rate is >1 hour stale (Frankfurter outage)? Show a warning? Suggest manual entry?
- What about crypto? Frankfurter doesn't cover BTC. Do we silently omit the suggestion or show "rate unknown"?
- Should the bot try to fetch on-demand if the cache is stale? Adds latency to every trade entry.

Not yet decided. Recommend: (1) show "suggested rate from frankfurter, fetched 12 min ago"; (2) for currencies not in Frankfurter, show "no system rate, please enter manually"; (3) no on-demand fetch — accept the cache age.

### 14.2 How are accounts identified for transfers across books?

`fx_transactions.book_id` is single-valued. That means transactions exist in exactly one book. But a user might want to transfer from "Personal/Cash USD" to "Family/Cash USD" — two accounts in two books. We don't support cross-book transfers in v1. **Lock as out-of-scope?** Or model as "two unrelated transactions, one in each book" with no link?

Recommend: explicitly out-of-scope at v1. Cross-book is a v2 concern.

### 14.3 What's the canonical "balance" of an account?

Accounts have `opening_balance`. Real-time balance = `opening_balance + signed sum of fx_transactions touching this account`. Computed how?

- **(a) Live SQL**: `SELECT opening_balance + COALESCE(SUM(...), 0) FROM accounts LEFT JOIN fx_transactions ON ...`. Simple, always correct, may be slow at >100k transactions per book.
- **(b) Materialised**: keep `accounts.current_balance` and update it via DB trigger or service-level. Faster reads, transactional consistency required, more complex.
- **(c) Materialised view**: refresh hourly. Simpler than (b) but eventually consistent.

Recommend (a) at MVP — Postgres can do this in <10 ms even at 1M rows with the right index. Promote to (b) only if profiling proves we need it.

### 14.4 Group chats: full UX or read-only?

The bot's privacy mode is OFF (it can read all messages). But the rolling-message UX assumes private chat. In a group:

- Should `/avg` work? (read-only, low risk.)
- Should `/trade` work? (mutates; same book as the inviter? whose role applies?)
- Does the bot try to maintain a rolling message in a group, or post fresh messages?

Recommend: at v1, group chat is read-only — `/avg`, `/books`, `/help` work; mutating commands reply with "open me in private chat to record trades". Defer group full UX to v1.1.

### 14.5 What's the user-visible "main currency" in mixed-currency reports?

A book with USD accounts + RUB accounts + EUR accounts. The dashboard shows total wealth. In what currency? Sum across currencies needs an FX rate.

- **(a) Book.base_currency_code** — every value converted to USD/RUB/EUR via latest exchange_rates. Loses "the user trades in 3 currencies" feel.
- **(b) Per-currency totals** — show three rows. Honest but harder to glance.
- **(c) Both** — primary in base_currency, plus a breakdown.

Recommend (c). Plan §M4 references "PnLByCurrencyChart" and "AccountBalanceChart" — both per-currency. Add a single "Total wealth in {base}" card on top.

### 14.6 Audit trail: do we need it at v1?

Plan §"What we're NOT doing" says "no audit log table". But for finance tools, "who edited this trade and when" matters. Options:

- **(a) None at v1** (current decision). `created_by_user_id` + `updated_at` only.
- **(b) Append-only `transaction_history` table** — every UPDATE inserts a row.
- **(c) Postgres logical decoding to a separate audit DB** — overkill.

Recommend stick with (a). Add (b) when a real user requests "who changed the rate".

### 14.7 FX rate source tradeoffs at v1.1+

Frankfurter is great but: ECB-only, fiat-only, daily resolution. For crypto we'll add CoinGecko. For stocks/ETFs we'd add another. **The architecture supports this** — `FxClient` is a Protocol; multiple implementations sit behind a single repository. **Question:** when we have multiple sources for the same pair (USD→EUR), which wins? Per-source rows in `exchange_rates`; the **latest** by source priority? Or the latest overall?

Recommend: "latest by `(base, quote, fetched_at DESC)`" — newest wins. If we add a second source, we never delete the first; both rows persist. Source priority becomes a v1.1 question only when we observe disagreement.

---

## 15. What this document is NOT

- Not a roadmap (see plan).
- Not API documentation (see OpenAPI generated by FastAPI).
- Not deployment instructions — see `docs/deploy.md`.
- Not a tutorial (see `docs/onboarding.md`).

It is a **single-page mental model** + **interrogable spec** for the architecture. If you find an inconsistency between this doc and the code, **the code is right and this doc is stale** — fix the doc.
