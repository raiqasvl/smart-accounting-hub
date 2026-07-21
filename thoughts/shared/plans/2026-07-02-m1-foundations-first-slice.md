---
date: 2026-07-02T18:40:00+07:00
researcher: i.gorvier
git_commit: 97f66fe466d83e0aec06de27c13001e7d291964c
branch: main
repository: smart-accounting-hub
topic: "M1 Foundations — implementation plan for the first end-to-end slice"
tags: [plan, m1, foundations, auth, fastapi, aiogram, nextjs, alembic, i18n, dishka]
status: ready-for-dev
last_updated: 2026-07-02
last_updated_by: i.gorvier
based_on_research: thoughts/shared/research/2026-07-02-first-runnable-slice-m1-gap.md
supersedes_in_part: "2026-05-01-mvp-scope-and-milestones.md §1.7/§1.8/§1.9 + M1 DoD (local-dev pivot)"
---

# M1 Foundations — First End-to-End Slice Implementation Plan

## Overview

Fill in the comment-only scaffold to ship the M1 "Foundations" vertical: a Telegram user
sends `/start`, we auto-create their user + default personal book, and the Mini-App
authenticates via `initData`, mints a JWT, and renders `Hello {name}, book "{name}"` on a
real phone — with tampered-JWT → 401 and tampered-initData → 403. This is the whole M1 DoD in
one milestone; every design decision below is locked (see the `/grill-me` decision log in
§Decision Log). No open questions remain.

## Current State Analysis

Per [the state research](thoughts/shared/research/2026-07-02-first-runnable-slice-m1-gap.md):
the repo is a **fully-bootstrapped, zero-implementation scaffold**. All 61 `.py` and 7
`.ts/.tsx` source files are comment-only (0 executable lines); `.venv` + `node_modules` are
installed; every dependency imports. `migrations/versions/` holds only `.gitkeep`;
`migrations/env.py` is a stub. `make dev-api` / `make dev-bot` / `make migrate` reference
symbols that don't exist yet (`main:app`, a runnable `env.py`, the `0001` migration).

Dependency manifests are already M1-complete — `packages/core` declares `pyjwt`,
`fluent.runtime`, `aiogram-i18n`, `sqlalchemy-utils` (LtreeType); `apps/miniapp` declares
`@tanstack/react-query`, `@telegram-apps/sdk-react`, `@fluent/bundle`, `@fluent/react`, shadcn
deps, vitest. **Only test tooling is missing** (testcontainers, hypothesis, pytest-asyncio).

The current tree uses `packages/core` (Python package `smart_accounting`) and
`packages/api-types`; the milestone plan's `packages/shared_py`/`shared_ts` names are stale.

## Desired End State

`make check` green; `make migrate` applies `0001_initial` to a fresh DB with `alembic check`
clean; the API boots (`app` importable, `/healthz` ok); an integration suite proves the golden
auth path + both negatives; and on a real phone, `/start` → WebApp button → Mini-App renders
the greeting card. Verification is the M1 DoD checklist in §Definition of Done.

### Key Discoveries
- Bot must never import `smart_accounting.{models,repositories}` (D22, grep-guarded) → services
  return **Pydantic DTOs**, not ORM entities. [services/__init__.py](packages/core/src/smart_accounting/services/__init__.py)
- `users` has a **surrogate `BIGSERIAL` id** + `telegram_user_id UNIQUE` → `JWT.sub = users.id`.
  [models/user.py](packages/core/src/smart_accounting/models/user.py)
- `tg_chats` is **bot-owned** (`chat_id` PK, `active_book_id NULL ⇒ onboarding`). The API auth
  path creates user+book only. [models/tg_chat.py](packages/core/src/smart_accounting/models/tg_chat.py), D15.
- initData verify + JWT specs are fully documented in
  [auth/initdata.py](packages/core/src/smart_accounting/auth/initdata.py) and
  [auth/jwt.py](packages/core/src/smart_accounting/auth/jwt.py).
- Dishka `DepsProvider`: UoW at `Scope.REQUEST`; singletons at `Scope.APP`.
  [ioc.py](packages/core/src/smart_accounting/ioc.py)
- `base.py` timestamp mixin uses a naive `datetime.now` — **fix to tz-aware** to match
  `timestamptz`. [models/base.py](packages/core/src/smart_accounting/models/base.py)

## What We're NOT Doing (M1 out of scope)

- **Caddy / Dockerfile / prod compose / CI** — deferred (local-dev pivot; D11/D19). Supersedes
  milestone plan §1.7/§1.8. Apps run on the host; only `db`+`redis` are containerized.
- **structlog + Sentry pipeline** — M1 uses **stdlib logging** at `LOG_LEVEL`; Sentry only
  initializes if `SENTRY_DSN` is set (no-op locally). Supersedes §1.9.
- **CORS middleware** — the Next.js proxy makes every call same-origin.
- **Currency seeding** (`0002_seed_currencies`), **RBAC `PERMISSIONS` matrix + `require()`**,
  **`/start invite_<token>` deep-link acceptance**, **book switching**, **the rolling
  single-message bot UX**, **any money endpoint / `big.js`**, **FX/Frankfurter**,
  **aiogram-dialog scenes** — all M2+.
- **Dev auth bypass** — Telegram-only; tests mint initData by HMAC-signing a test token.

## Implementation Approach

Bottom-up along the locked layering `models ← repositories ← services ← presentation ← UI`,
schema-first (single migration before service code). Seven phases; each ends with automated
verification, and phases with a user-visible surface add a manual gate. The backend is provable
by integration tests **before** the Telegram/tunnel externalities enter (Phases 6–7).

Cross-cutting conventions established in Phase 1 and used everywhere after:
- **Service returns:** every service method returns a Pydantic schema from
  `packages/core/src/smart_accounting/schemas/`. Repos return ORM internally; the service maps.
- **Transactions:** begin/end only inside a service method, via the injected `UoW`.
- **Errors:** raise typed domain exceptions; a FastAPI handler renders the D24 envelope
  `{"error": {"code", "params"}, "request_id"}`. The bot maps the same exceptions to Fluent text.

---

## Phase 1: Foundations (config, DI, engine, UoW, base types, entrypoint shells)

### Overview
Make everything downstream importable and bootable. Cherry-pick the AiogramBotTemplate
foundations (with MIT attribution), implement config/engine/UoW/Dishka, and stand up empty-but-
runnable API `app` and bot boot so later phases slot in.

### Changes Required

#### 1. Cherry-pick foundations (add MIT header to each)
Copy from `research/AiogramBotTemplate/` per milestone plan §1.2 table into: `models/base.py`,
`models/fields.py`, `common/uow.py`, `database/engine.py`, `ioc.py`, `config.py`, bot
`storage.py`/`main.py`/`__main__.py`, `migrations/env.py`, `migrations/script.py.mako`. Header:
```python
# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
```

#### 2. `config.py` — pydantic-settings
**File**: `packages/core/src/smart_accounting/config.py`. `Settings(BaseSettings)` mirroring
`.env.example` (DOMAIN, BOT_TOKEN, BOT_USERNAME, JWT_SECRET, JWT_LIFETIME_SECONDS=1800,
POSTGRES_DSN, REDIS_DSN, LOG_LEVEL, SENTRY_DSN|None, ENVIRONMENT, DEBUG). `@lru_cache
get_config()`.

#### 3. `database/engine.py` + `common/uow.py`
`create_async_engine(get_config().POSTGRES_DSN)`, `async_sessionmaker(expire_on_commit=False)`.
`UoW` is an async context manager wrapping one `AsyncSession` with `commit`/`rollback`.

#### 4. `models/base.py` — with the tz-aware fix
```python
metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)
class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True
    metadata = metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```
(`func.now()` server-side, not naive `datetime.now`.)

#### 5. `ioc.py` — Dishka container
`DepsProvider`: `Settings` (APP, from `get_config()`), `AsyncEngine`+`async_sessionmaker` (APP),
`UoW` (REQUEST, `async with sessionmaker() as s: yield UoW(s)`), a `JwtCodec` (APP, holds
`JWT_SECRET`). Repos/services registered REQUEST (added as written in later phases). Expose
`make_container()` and `make_async_container()`.

#### 6. `observability.py` — stdlib only (supersedes §1.9)
```python
def configure_observability(*, sentry_dsn: str | None, environment: str, log_level: str) -> None:
    logging.basicConfig(level=log_level, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if sentry_dsn:
        sentry_sdk.init(dsn=sentry_dsn, environment=environment, traces_sample_rate=0.1)
```

#### 7. Entrypoint shells
- `apps/api/.../main.py`: module-level `app = FastAPI(...)` + `def run(): uvicorn.run(...)`
  (so both `uvicorn ...main:app` and the `main:run` console-script work). Routers wired in Phase 5.
- `apps/bot/.../__main__.py` + `main.py` + `storage.py`: boot order per §1.5; handlers wired in Phase 6.

### Success Criteria
#### Automated
- [ ] `python -c "import smart_accounting.config, smart_accounting.ioc, smart_accounting.database.engine"` succeeds.
- [ ] `python -c "from smart_accounting_api.main import app"` imports (empty router set ok).
- [ ] `make lint` and `make typecheck` pass (mypy strict).
- [ ] `THIRD_PARTY_NOTICES.md` lists AiogramBotTemplate MIT; each lifted file carries the header.

---

## Phase 2: Data layer (11 models + Alembic env + `0001_initial`)

### Overview
Define all 11 ORM models, make `env.py` runnable, and land the single initial migration.

### Changes Required

#### 1. Models — all 11, per milestone plan §1.3 field lists
`user, tg_chat, book, book_member, book_invite, currency, account, category, exchange_rate,
fx_transaction, notifications_outbox`. Use `fields.py` aliases (`bigserial_pk`, `money_amount`
NUMERIC(20,8), `ltree_path` LtreeType, `currency_code` String(8), `timestamptz`). Un-comment all
11 imports in [models/__init__.py](packages/core/src/smart_accounting/models/__init__.py).

#### 2. `migrations/env.py` — async, real
Import `Base.metadata` (via `smart_accounting.models`), read DSN from `get_config()`, implement
`run_async_migrations()` with `NullPool` + `run_migrations_online()`.

#### 3. `0001_initial` migration
**File**: `migrations/versions/2026_05_01_0001_initial.py`. In `upgrade()`:
`CREATE EXTENSION IF NOT EXISTS ltree; ... pgcrypto;` → `CREATE TYPE transaction_kind AS ENUM
('plain_cash','internal_transfer','fx_conversion')` + `transaction_direction AS ENUM
('buy','sell')` → all 11 tables in FK order (users → tg_chats → books → book_members →
book_invites → currencies → accounts → categories → exchange_rates → fx_transactions →
notifications_outbox) → indexes (categories GIST `(book_id, parents_tree)` D14; fx_transactions
`(book_id, quote_currency_code, direction, occurred_at DESC)`; exchange_rates + outbox partial).
Prefer `alembic revision --autogenerate` then hand-verify against §1.3, adding the extensions +
enum `CREATE TYPE` (which autogen won't emit) at the top of `upgrade()` and their `DROP` in `downgrade()`.

### Success Criteria
#### Automated
- [ ] `make migrate` (alembic upgrade head) applies cleanly to a fresh DB (`make up` running).
- [ ] `uv run alembic check` reports **no diff** after upgrade (models ↔ migration match).
- [ ] `uv run alembic downgrade base` then `upgrade head` round-trips without error.
- [ ] `make typecheck` passes on the models.

---

## Phase 3: Auth primitives + schemas (DTOs) + error envelope

### Overview
Pure, DB-free building blocks: initData HMAC, JWT codec, the Role enum, the Pydantic DTOs that
cross the service boundary, and the typed domain exceptions + D24 renderer.

### Changes Required

#### 1. `auth/initdata.py`
`verify_init_data(init_data, bot_token, max_age_seconds=86400) -> dict` per the documented
algorithm (WebAppData secret, sorted data-check-string, constant-time compare;
`InitDataInvalid` / `InitDataExpired`).

#### 2. `auth/jwt.py`
`issue_token(*, user_id, book_id, role, secret, lifetime_seconds=1800) -> str` (claims
`{sub, book_id, role, exp, iat, jti}`, HS256) and `decode_token(token, secret) -> Claims`
(rejects `none` alg, expiry → `JwtExpired`, bad sig/claims → `JwtInvalid`).

#### 3. `auth/rbac.py`
`class Role(IntEnum): OWNER=0; ADMIN=1; EDITOR=2; VIEWER=3`. (Matrix + `require()` deferred to M2.)

#### 4. `schemas/` — the boundary DTOs
`UserOut{id, telegram_user_id, first_name, last_name, username, language, timezone}`,
`BookOut{id, name, kind, base_currency_code, role}`, `TokenOut{access_token, expires_in, user:
UserOut, book: BookOut}`, `MeOut{user: UserOut, active_book: BookOut, role: int, books: list[BookOut]}`,
request `AuthTelegramIn{init_data: str}`, and `ErrorOut{error: {code: str, params: dict}, request_id: str}`.

#### 5. Domain exceptions + D24 mapping (types only here; handler wired in Phase 5)
`AppError(code, params)` base; subclasses `InitDataInvalid`/`InitDataExpired` → 403,
`JwtInvalid`/`JwtExpired` → 401.

### Success Criteria
#### Automated
- [ ] Unit: `issue_token` → `decode_token` round-trips; expired token → `JwtExpired`; `none`-alg
      + one-char tamper → `JwtInvalid`.
- [ ] Hypothesis: `verify_init_data` rejects tampered hash / off-by-one bytes / expired
      `auth_date` / missing fields / reordered fields; accepts a correctly-signed payload.
- [ ] `make typecheck` + `make lint` pass.

---

## Phase 4: Repositories + services (the onboarding transaction)

### Overview
The M1 repos and the two services — `user_service` (shared core) and `auth_service` (API arm).

### Changes Required

#### 1. Repositories (queries only, no tx)
`repositories/users.py` (`get_by_telegram_id`, `insert`, `update_profile`), `tg_chats.py`
(`get`, `upsert`, `set_active_book`), `books.py` (`insert`, `list_for_user`, `get`).

#### 2. `services/user_service.py` — shared core (D21, one transaction)
```python
class UserService:
    def __init__(self, uow: UoW, users: UsersRepo, books: BooksRepo, members: BookMembersRepo):
        ...
    async def ensure_user_and_default_book(self, ident: TgIdentity) -> tuple[UserOut, BookOut]:
        async with self.uow:                      # the ONLY transaction boundary
            user = await self.users.get_by_telegram_id(ident.telegram_user_id)
            if user is None:
                user = await self.users.insert(ident, language=pick_language(ident.language_code))
                book = await self.books.insert(owner_id=user.id, name=default_book_name(ident),
                                               kind=0, base_currency_code=pick_currency(ident.language_code))
                await self.members.insert(book_id=book.id, user_id=user.id, role=Role.OWNER)
            else:
                book = await self.books.primary_for(user.id)
            await self.uow.commit()
        return UserOut.model_validate(user), BookOut.model_validate(book, ...)  # ORM→DTO
```
`pick_language`: `'ru' if code.startswith('ru') else 'en'` (uk→en). `pick_currency`:
`ru→RUB, uk→UAH, tr→TRY, de/fr/es/it/pl/nl→EUR, else→USD`.

#### 3. `services/auth_service.py` — API arm
```python
class AuthService:
    def __init__(self, user_service: UserService, jwt: JwtCodec, settings: Settings): ...
    async def authenticate(self, init_data: str) -> TokenOut:
        parsed = verify_init_data(init_data, self.settings.BOT_TOKEN)     # raises → 403
        ident = TgIdentity.from_init_data(parsed)
        user, book = await self.user_service.ensure_user_and_default_book(ident)
        token = self.jwt.issue(user_id=user.id, book_id=book.id, role=book.role)
        return TokenOut(access_token=token, expires_in=self.settings.JWT_LIFETIME_SECONDS,
                        user=user, book=book)
```
Register `UserService`/`AuthService` + repos as `Scope.REQUEST` providers in `ioc.py`.

### Success Criteria
#### Automated (testcontainers PG16 + per-test rollback)
- [ ] New identity → exactly one `users` + one `books(kind=0)` + one `book_members(role=OWNER)`,
      all committed atomically; returns DTOs (not ORM).
- [ ] Repeat call with same `telegram_user_id` → **no** duplicate user/book (idempotent).
- [ ] `auth_service.authenticate(valid_init_data)` → `TokenOut` whose JWT decodes to `sub=user.id`,
      `book_id=book.id`. (Test signs initData with a test `BOT_TOKEN`.)
- [ ] `make typecheck` passes; grep-guard: `apps/bot` imports no `models`/`repositories` (n/a yet, but keep services import-safe).

---

## Phase 5: API surface (deps, routers, main wiring, D24 handler)

### Overview
Expose the auth path over HTTP with the `/api/v1` prefix, the D24 envelope, and a request-id.

### Changes Required

#### 1. `deps.py`
`current_jwt_claims()` (parse `Authorization: Bearer`, `decode_token` → 401 on failure),
`current_user()` (load `UserOut` for `claims.sub`), `current_book_member()` (load `(BookOut, role)`
for `claims.book_id`+`sub`). Dishka-injected services.

#### 2. Routers
- `routers/health.py`: `GET /healthz` → `{"status":"ok"}`; `GET /readyz` → pings PG (`SELECT 1`) +
  Redis, 503 on failure. **Bare paths** (no `/api/v1`).
- `routers/auth.py`: `POST /auth/telegram` (`AuthTelegramIn` → `auth_service.authenticate` →
  `TokenOut`).
- `routers/me.py`: `GET /me` (deps chain → `MeOut`), `response_model=MeOut`.

#### 3. `main.py` wiring
```python
app.include_router(health.router)                      # bare /healthz /readyz
api = APIRouter(prefix="/api/v1")
api.include_router(auth.router); api.include_router(me.router)
app.include_router(api)                                 # /api/v1/auth/telegram, /api/v1/me
app.add_middleware(RequestIdMiddleware)                # sets request.state.request_id = "req_..."
@app.exception_handler(AppError)
async def app_error_handler(request, exc):             # D24 envelope
    return JSONResponse(status_code=exc.http_status,
        content={"error": {"code": exc.code, "params": exc.params},
                 "request_id": request.state.request_id})
setup_dishka(container=make_container(), app=app)
```
`configure_observability(...)` called in `run()` and at import.

### Success Criteria
#### Automated (httpx AsyncClient against the app + testcontainers DB)
- [ ] `GET /healthz` → 200 `{"status":"ok"}`; `GET /readyz` → 200 with DB+Redis up.
- [ ] `POST /api/v1/auth/telegram` with valid signed initData → 200 `TokenOut` (JWT decodes).
- [ ] `GET /api/v1/me` with that Bearer JWT → 200 `MeOut` (`user.first_name`, `active_book.name`, `books:[...]`).
- [ ] **Tampered JWT** (one char) → `GET /api/v1/me` → **401** with D24 envelope shape.
- [ ] **Tampered initData** (one byte) → `POST /api/v1/auth/telegram` → **403** with D24 envelope.
- [ ] `GET /openapi.json` lists `/api/v1/auth/telegram` + `/api/v1/me` (feeds `types:gen`).
- [ ] `make check` passes end-to-end on the Python side.

---

## Phase 6: Bot (`/start` + full EN+RU i18n + boot)

### Overview
Wire the bot to call `user_service` directly, send the WebApp button, and localize via Fluent.

### Changes Required

#### 1. i18n catalogues + middleware
Populate `packages/core/src/smart_accounting/i18n/{en,ru}/main.ftl` with the M1 message ids
(`start-welcome`, `open-app-button`, `card-greeting`, `error-auth`). Wire `aiogram-i18n`
`I18nMiddleware(FluentRuntimeCore(path=".../i18n/{locale}"))`, locale getter = `users.language`
(fallback `en`).

#### 2. `handlers/commands.py` — bare `/start`
```python
@router.message(CommandStart(deep_link=False))
@inject
async def start(msg: Message, i18n: I18nContext, user_service: FromDishka[UserService],
                tg_chats: FromDishka[TgChatsRepo]):
    ident = TgIdentity.from_message(msg)
    user, book = await user_service.ensure_user_and_default_book(ident)
    await tg_chats.upsert(chat_id=msg.chat.id, user_id=user.id, active_book_id=book.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text=i18n.get("open-app-button"),
        web_app=WebAppInfo(url=f"https://{settings.DOMAIN}"))]])
    sent = await msg.answer(i18n.get("start-welcome", name=user.first_name), reply_markup=kb)
    await tg_chats.set_last_message_id(msg.chat.id, sent.message_id)
```
No `models`/`repositories` imports (D22) — only `services` + repo types via Dishka. (The
`tg_chats` repo is a repository; the bot obtains it via Dishka injection of a **service** in M2,
but for M1 the tg_chats upsert is done through a tiny `TgChatService.bind(...)` to keep the bot
free of direct repo imports — add `TgChatService` to satisfy D22 cleanly.)

#### 3. Boot
`__main__.py`/`main.py`: build Dishka async container, `setup_dishka(container, router=dp)`,
include `commands_router`, `configure_observability`, `dp.start_polling(bot)`.

### Success Criteria
#### Automated
- [ ] Handler unit test (mocked `Bot`): `/start` from a new user → `user_service` called →
      `tg_chats` upserted with `active_book_id` → a message with a `web_app` button is sent.
- [ ] i18n: `start-welcome` resolves in both `en` and `ru`; locale selected from `users.language`.
- [ ] Grep-guard passes: `rg "from smart_accounting.(models|repositories)" apps/bot/` → **no hits**.
- [ ] `make typecheck` + `make lint` pass; `python -m smart_accounting_bot` boots (polls) against the test env.
#### Manual
- [ ] `/start` on the dev bot creates `users` + `tg_chats` + `books(kind=personal, owner=me)`; RU
      account shows the Russian welcome.

**Pause for manual confirmation before Phase 7 relies on the bot.**

---

## Phase 7: Mini-App (proxy, api-client, page, i18n, types:gen) + end-to-end

### Overview
The single authenticated page, the same-origin proxy, and the real-phone DoD.

### Changes Required

#### 1. `next.config.mjs` — the proxy (replaces Caddy locally)
```js
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [{ source: '/api/v1/:path*', destination: 'http://127.0.0.1:8000/api/v1/:path*' }];
  },
};
```

#### 2. `lib/telegram.ts` + `lib/api-client.ts`
`telegram.ts`: `retrieveRawInitData()` + `initDataUnsafe.user.language_code`. `api-client.ts`:
same-origin base `""` (paths already carry `/api/v1` from OpenAPI); `Authorization: Bearer` on
authed calls; JWT in-memory + `sessionStorage` mirror; on 401 → clear + re-post fresh initData →
retry; translate `ErrorOut` to a thrown `ApiError`.

#### 3. `app/page.tsx` + providers
`QueryClientProvider` + `LocalizationProvider` (@fluent/react, bundle from `/me`'s
`user.language`, pre-auth fallback to Telegram `language_code`). On mount: post initData →
`TokenOut` → `useQuery(['me'])` → render `<Card>{ftl('card-greeting', {name, book})}</Card>`.

#### 4. `packages/api-types` regen
With the API running: `pnpm run types:gen` (`openapi-typescript http://localhost:8000/openapi.json
-o packages/api-types/src/api.d.ts`). Replaces the empty `Record<string,never>` stub.

#### 5. `.env` finalization
Set `NEXT_PUBLIC_API_BASE_URL` **relative** (`/api/v1`) so tunnel restarts don't force a rebuild.

### Success Criteria
#### Automated
- [ ] `pnpm run types:gen` produces real `paths`/`components` in `api-types/src/api.d.ts`.
- [ ] `pnpm -F @smart-accounting/miniapp typecheck` + `lint` + `build` pass (`.next` artifact).
- [ ] `make check` green across the whole workspace.
#### Manual (the M1 DoD, on a real phone)
- [ ] Tap the WebApp button → Mini-App authenticates via initData and shows `Hello {name}, book "{name}"` (RU account → Russian).
- [ ] Tampered JWT → `/api/v1/me` 401; tampered initData → `/api/v1/auth/telegram` 403 (observable via devtools).

---

## Testing Strategy

- **Unit / property (no DB):** `verify_init_data` + `decode_token` under hypothesis (tamper,
  expiry, reordering, missing fields, `none`-alg).
- **Integration (testcontainers PG16 + ltree, per-test rollback):** `ensure_user_and_default_book`
  atomicity + idempotency; `auth_service.authenticate` → valid JWT; the three router paths +
  401/403. httpx `AsyncClient` against the app; Dishka container overridden to the test DB.
- **Bot:** mocked-`Bot` handler test for `/start`; grep-guard assertion for D22.
- **Manual:** the real-phone DoD (Phase 6/7 manual gates). Test fixtures sign initData with a
  dedicated `TEST_BOT_TOKEN` so no bypass code exists in the app.
- Add test deps to the uv workspace dev group: `pytest`, `pytest-asyncio`, `hypothesis`,
  `testcontainers[postgres]`, `httpx`.

## Local-Dev Runbook & @BotFather Checklist (human-in-the-loop)

These gate the real-phone check and are **yours to do** (I can't create a Telegram bot):
1. `@BotFather` → `/newbot` → copy `BOT_TOKEN`; set `BOT_TOKEN`/`BOT_USERNAME` in `.env` (chmod 600).
2. `make bootstrap` (done), `mkdir -p db && python3 -c "import secrets;print(secrets.token_urlsafe(24))" > db/password.txt && chmod 600 db/password.txt` (sync with `POSTGRES_DSN`).
3. `make up` → `make migrate`.
4. Terminals: `make dev-api`, `make dev-bot`, `make dev-miniapp`, `make tunnel`.
5. Paste the `https://*.trycloudflare.com` URL into `DOMAIN` in `.env` **and** `@BotFather` →
   `/myapps` → Edit Web App URL. Re-paste on every tunnel restart (`NEXT_PUBLIC_API_BASE_URL`
   stays `/api/v1`, so no Mini-App rebuild is needed).

## Definition of Done (M1 — corrected for local-dev pivot)

Automated: `make check` green · `make migrate` applies `0001` + `alembic check` clean ·
`curl localhost:8000/healthz` ok · `pnpm -F @smart-accounting/miniapp build` artifact · golden-path
+ 401 + 403 integration tests pass. Manual: `/start` creates user+tg_chat+book(owner) ·
Mini-App renders the greeting (RU→Russian) · tampered JWT→401 · tampered initData→403.
*(Superseded from the milestone DoD: 5-container/Caddy `curl https://localhost`, eslint, Sentry
smoke, JSON `docker logs`, CI-green — all deferred.)*

## Performance Considerations
Negligible at M1 (single auth path). `ensure_user_and_default_book` is one short transaction;
`verify_init_data` HMAC is ~sub-ms. The weighted-avg `<10ms @ 100k rows` target is an M3 concern.

## Migration Notes
Single `0001_initial` on an empty DB — no data migration, no rollback of user data. `downgrade()`
drops tables in reverse FK order and `DROP TYPE` the two enums. Currency seeding is a separate
`0002` in M2.

## Decision Log (from `/grill-me`, 2026-07-02)
Scope: full M1 end-to-end · shared `user_service` core + API-only `auth_service` · Pydantic-DTO
service boundary · Next.js proxy (single tunnel, no CORS) · FastAPI owns `/api/v1` (health bare) ·
D24 envelope now · TanStack + memory/sessionStorage JWT · bot minimal button (no rolling UX) ·
**full EN+RU i18n now** · integration-first testcontainers testing · stdlib logging · surrogate
user PK (`JWT.sub=users.id`) · single `0001` (currency seed→M2) · invite deep-link→M2 · RBAC enum
now / matrix→M2 · no dev auth bypass. Residual asserts: `uk→en` language default; tz-aware
timestamp fix.

## References
- Research: [thoughts/shared/research/2026-07-02-first-runnable-slice-m1-gap.md](thoughts/shared/research/2026-07-02-first-runnable-slice-m1-gap.md)
- Milestone plan (M1 source): [thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md](thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md) lines 134–475
- State baseline: [thoughts/shared/research/2026-06-10-current-implementation-state.md](thoughts/shared/research/2026-06-10-current-implementation-state.md)
- Cherry-pick source: [thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md](thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md)
