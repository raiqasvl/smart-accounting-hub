---
date: 2026-07-21T00:00:00+07:00
researcher: i.gorvier
git_commit: 6d42358b1626a02f6a035878ec11a35d95fefe24
branch: main
repository: smart-accounting-hub
topic: "M2 — Books, invites, accounts, currencies (multi-tenant primitives)"
tags: [plan, m2, rbac, books, invites, accounts, currencies, aiogram-dialog, miniapp, alembic]
status: ready-for-dev
last_updated: 2026-07-21
last_updated_by: i.gorvier
decisions_confirmed: "full M2 incl. bot dialogs (Phase 6); hand-rolled Tailwind components (D-M2-1); D-M2-2..6 accepted"
based_on: thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md §2 (M2)
supersedes_in_part: "milestone plan §2.1-§2.5 UI/ops specifics (local-dev pivot; shadcn hand-rolled)"
---

# M2 — Books, Invites, Accounts, Currencies

## Overview

Layer the multi-tenant primitives on the M1 auth slice: **RBAC** (the permission matrix that
gates everything from here on), **book CRUD** + **book switching** (re-mints the JWT), the
**invite** flow (admin mints a magic-link → another user accepts via a `/start` deep-link),
the **currencies** system catalogue (seeded), and per-book **accounts**. The bot grows its first
`aiogram-dialog` flows (create-book, create-account, join-via-invite) and the rolling
single-message UX; the Mini-App grows from one greeting card into a small tabbed shell
(Books · Accounts · Settings).

M2 ends with two users sharing a book across roles, and an account with an opening balance —
the substrate M3's headline weighted-average feature needs.

## Current State (post-M1, commit 6d42358)

- **Core**: config/DI/UoW/engine, 11 models + `0001_initial`, `auth/{initdata,jwt,rbac(Role only)}`,
  `schemas/{user,book,auth,errors}`, `errors.AppError` (+ InitData*/Jwt*), repos
  `{users,books,book_members,tg_chats}`, services `{user_service,auth_service,tg_chat_service}`,
  Dishka wires them at REQUEST scope. `schemas/money.py` and `data/currencies_seed.py` are still
  comment-only stubs; `fx/*`, `services/*` beyond M1 are stubs.
- **API**: `create_app()`, bare `/healthz`+`/readyz`, `/api/v1/{auth/telegram,me}`, request-id
  middleware, D24 handler. `deps.extract_claims` only (no `current_book_member`/`require`).
- **Bot**: `/start` only, Fluent i18n (en/ru), no dialogs yet.
- **Mini-App**: single greeting page, same-origin `/api/v1` proxy, JWT client, no Tailwind/shadcn
  wired (inline styles), `api-types` generated from the M1 OpenAPI.
- **DB**: compose Postgres :5433 / Redis :6380, `0001_initial` at head. Tests: 31, compose-DB +
  per-test savepoint rollback.

## Desired End State

`make check` green; `0002_seed_currencies` applies (45+ system currencies); an integration suite
proves book CRUD + switch (JWT re-mint) + RBAC denial + invite lifecycle + account CRUD + FK
protection; the bot's create-book / create-account / join-via-invite dialogs work end-to-end; the
Mini-App shows a book picker, an accounts tab, and an invites section. Verification = §Definition
of Done.

## What We're NOT Doing (M2 out of scope)

- **FX transactions, the weighted-average report, `/avg`, `/trade`, `RecordTradeDialog`, `big.js`**
  — M3 (the headline). Accounts land now precisely so M3 has somewhere to hang trades.
- **Categories (ltree), internal transfers, CSV export, charts** — M4.
- **Deploy / webhook / prod ops** — deferred (local-dev pivot, D11/D19).
- **`notifications_outbox` drainer** — table only (v1.1).
- **Hard-delete of accounts with history** — M2 always allows delete (no transactions exist yet)
  but the FK-protection code lands now so M3 is safe.

## Implementation Approach

Bottom-up along the locked layering, same as M1. Seven phases; each ends with automated
verification, and the two user-visible surfaces (bot, Mini-App) add manual gates. Cross-cutting
conventions unchanged from M1 (services return Pydantic DTOs; transactions begin/end in a service
via UoW; typed domain errors → D24 envelope / Fluent). Two new conventions this milestone:

- **Authorization** is enforced in the API `require(permission)` dependency, which resolves the
  caller's role for the **path** `book_id` (a DB lookup on `book_members`, not just the JWT claim)
  and checks `PERMISSIONS`. The bot enforces the same matrix via `RbacService` before each action.
- **Money** crosses the wire as a decimal **string** (D23); `schemas/money.py` defines the `Money`
  Annotated type, used by `accounts.opening_balance` (first money field in the product).

---

## Phase 1: RBAC matrix + Money type + shared schemas + API authz deps

### Changes Required

#### 1. `auth/rbac.py` — the permission matrix (extend the M1 Role enum)
Add `PERMISSIONS: dict[Role, frozenset[str]]` exactly per milestone §2.1 (8 permissions:
`book.delete/invite/role.change/read`, `tx.write/read`, `category.write`, `account.write`);
`has_permission(role, permission) -> bool`; `require_permission(role, permission) -> None`
(raises `Forbidden`). Pure, DB-free (single source of truth for API + bot).

#### 2. `schemas/money.py` — the `Money` wire type (D23)
`Money = Annotated[Decimal, BeforeValidator(_parse), PlainSerializer(_ser, when_used="json"),
WithJsonSchema({"type":"string", "pattern": r"^-?\d+(\.\d+)?$"})]` per the documented stub.
`_parse` accepts str/int/Decimal → Decimal; `_ser` = `format(v, "f")`.

#### 3. New domain errors (`errors.py`)
`Forbidden`(403, `forbidden`), `NotFound`(404, `not_found`), `BookNotFound`(404),
`NotAMember`(403), `LastOwner`(409, `last_owner`), `InviteInvalid`(404), `InviteExpired`(410),
`InviteAlreadyUsed`(409), `AlreadyMember`(409), `AccountInUse`(409, `account_in_use`),
`CurrencyUnknown`(422). All carry `params` for i18n.

#### 4. New DTO schemas
`schemas/book.py`: add `BookCreateIn{name, kind, base_currency_code, default_language="en"}`,
`BookPatchIn{name?, archived?}`. `schemas/account.py`: `AccountOut{id, book_id, currency_code,
name, kind, archived, opening_balance: Money}`, `AccountCreateIn{currency_code, name, kind,
opening_balance: Money = "0"}`, `AccountPatchIn{name?, archived?}`. `schemas/currency.py`:
`CurrencyOut{id, book_id, code, symbol, decimals, kind, archived}`, `CurrencyCreateIn{code,
symbol, decimals, kind}`. `schemas/invite.py`: `InviteCreateIn{role, ttl_minutes=1440}`,
`InviteOut{id, book_id, role, token, deep_link, expires_at, used_at}`, `MemberOut{user, role,
invited_at, accepted_at}`.

#### 5. API authz deps (`apps/api/.../deps.py`)
`current_book_member(book_id, claims) -> (BookOut, role)`: loads membership for the **path**
`book_id` + `claims.sub`; raises `NotAMember` (403) if absent. `require(permission)`: returns a
dependency that resolves `current_book_member` and calls `require_permission`. (Both read the path
`book_id`, so a JWT minted for book A can't act on book B without a real membership.)

### Success Criteria — Automated
- [ ] `pytest .../test_rbac.py`: all 4 roles × 8 permissions match the matrix; `require_permission`
      raises `Forbidden` on deny.
- [ ] Unit: `Money` round-trips `"90.27000000"` (no precision loss), rejects garbage, serializes to string.
- [ ] `make typecheck` + `make lint` pass.

---

## Phase 2: Currencies seed + currency service/API

### Changes Required

#### 1. `data/currencies_seed.py`
`SEED_CURRENCIES: list[CurrencySeed]` — ~40 ISO-4217 fiat majors (USD/EUR/RUB/UAH/GBP/…, `decimals`
2, `kind` 0) + metals (XAU/XAG, decimals 4, kind 2) + 5 crypto (BTC/ETH/USDT/USDC/BNB, decimals 8,
kind 1), each `{code, symbol, decimals, kind}`.

#### 2. `0002_seed_currencies.py` (idempotent data migration)
`INSERT ... ON CONFLICT (book_id, code) DO NOTHING` for each seed row with `book_id NULL`.
`downgrade()` deletes the seeded system rows (`WHERE book_id IS NULL AND code IN (...)`).

#### 3. `repositories/currencies.py` + `services/currency_service.py`
Repo: `list_visible(book_id)` (`WHERE book_id IS NULL OR book_id = :book_id`), `insert(...)`,
`get_by_code(book_id, code)`. Service: `list_for_book(book_id) -> list[CurrencyOut]`,
`add_override(book_id, dto, actor_role)` (requires `account.write`; validates unique per book).

#### 4. API `routers/currencies.py`
`GET /api/v1/currencies?book_id=` → system + overrides. `POST /api/v1/books/{book_id}/currencies`
(require `account.write`). Register in `main.py`.

### Success Criteria — Automated
- [ ] `make migrate` applies `0002`; `SELECT count(*) FROM currencies WHERE book_id IS NULL` ≥ 45;
      re-running `0002` (idempotent) doesn't duplicate.
- [ ] `alembic downgrade -1` removes only system rows; `upgrade` re-seeds.
- [ ] `GET /currencies` returns system catalogue; per-book override appears only for that book.

---

## Phase 3: Book service + CRUD API + switch (JWT re-mint)

### Changes Required

#### 1. `repositories/books.py` (extend) + `services/book_service.py`
Repo add: `update(book_id, **fields)`, `set_active_book_all_chats(user_id, book_id)` (via
`tg_chats`). Service:
- `create(actor, dto) -> BookOut` — insert book (owner=actor) + OWNER membership, one tx.
- `list_for_user(user_id) -> list[BookOut]` (role per book).
- `get(book_id, user_id) -> BookOut` (member-gated).
- `update(book_id, actor_role, dto)` — rename/archive (requires `book.read`+admin; archive needs
  `book.delete`? → **rename = admin, archive = owner**; see Decision Log D-M2-2).
- `switch(user_id, book_id) -> TokenOut` — verify membership, set `tg_chats.active_book_id` for all
  the user's chats, re-mint a JWT with the new `book_id`+`role` claims, return `TokenOut`.

#### 2. API `routers/books.py`
`POST /books` · `GET /books` · `GET /books/{book_id}` (require member) ·
`PATCH /books/{book_id}` (require `book.delete` for archive / admin for rename) ·
`POST /books/{book_id}/switch` (require member) → `TokenOut`. Register in `main.py`.

### Success Criteria — Automated (httpx + savepoint DB)
- [ ] Create → caller is OWNER; appears in `GET /books`.
- [ ] Non-member `GET /books/{id}` → 403 (`not_a_member`); Editor `PATCH archive` → 403.
- [ ] `switch` sets `active_book_id` on all the user's `tg_chats` and returns a JWT decoding to the
      new `book_id`.
- [ ] `make check` (Python) green.

---

## Phase 4: Invites — service + API + accept

### Changes Required

#### 1. `repositories/book_invites.py` + `services/invite_service.py`
Repo: `insert`, `get_by_token`, `mark_used`, `list_pending(book_id)`, `revoke(invite_id)`.
Service:
- `create(book_id, actor_role, dto) -> InviteOut` — require `book.invite`; `token =
  secrets.token_urlsafe(24)`; `expires_at = now + ttl`; `deep_link =
  https://t.me/{BOT_USERNAME}?start=invite_{token}`. Role can't be OWNER.
- `accept(token, user_id) -> BookOut` — validate (not expired → `InviteExpired`; not used, or
  same user re-accept → **idempotent**; not already a member with ≥ role → `AlreadyMember`); create
  `book_members` row; `mark_used`. Returns the joined book.
- `revoke(book_id, invite_id, actor_role)` — require `book.invite`.

#### 2. API `routers/invites.py`
`POST /books/{book_id}/invites` (require `book.invite`) · `POST /invites/{token}/accept`
(auth'd, body empty) · `DELETE /books/{book_id}/invites/{invite_id}` (require `book.invite`) ·
`GET /books/{book_id}/invites` (list pending, require `book.invite`).

### Success Criteria — Automated
- [ ] Create → accept by a **different** user → they become a member (role as minted).
- [ ] Double-accept is idempotent (no duplicate membership, 200 both times).
- [ ] Expired token → 410; revoked token → 404; already-member → 409.

---

## Phase 5: Accounts — service + CRUD API + FK protection

### Changes Required

#### 1. `repositories/accounts.py` + `services/account_service.py`
Repo: `insert`, `list_for_book(book_id, include_archived)`, `get`, `update`, `delete`,
`has_transactions(account_id)` (query `fx_transactions` by base/quote account — 0 in M2).
Service:
- `create(book_id, actor_role, dto)` — require `account.write`; validate `currency_code` exists
  (system or override) → else `CurrencyUnknown`.
- `list(book_id, ...)`, `patch(account_id, actor_role, dto)` (archive = `account.write`).
- `delete(account_id, actor_role)` — owner-only hard delete; if `has_transactions` → `AccountInUse`
  (409, suggest archive).

#### 2. API `routers/accounts.py`
`POST /books/{book_id}/accounts` · `GET /books/{book_id}/accounts?archived=` ·
`PATCH /accounts/{id}` · `DELETE /accounts/{id}`. (For the bare `/accounts/{id}` routes, the
service loads the account's `book_id` then checks membership/role.)

### Success Criteria — Automated
- [ ] Create USD "Cash" opening_balance "500" → persisted as `NUMERIC`, returned as `"500.00000000"`.
- [ ] Unknown currency → 422. List filters `archived`. Delete works (no tx). FK-protection path is
      unit-tested with a stubbed `has_transactions=True` → 409.

**Pause: backend proven end-to-end before the bot/Mini-App externalities enter.**

---

## Phase 6: Bot — aiogram-dialog flows + invite deep-link + rolling UX

### Changes Required

#### 1. aiogram-dialog setup + rolling message
Wire `setup_dialogs(dp)` in `main.py`; add a `MainMenuService` that keeps the single rolling
message (`tg_chats.last_message_id`) via `bot.edit_message_text`. New Fluent keys (en+ru).

#### 2. Dialogs (`apps/bot/.../dialogs/`)
- `CreateBookDialog`: `Name → Kind → BaseCurrency → Confirm → Done` → `book_service.create`.
- `CreateAccountDialog`: `CurrencyPicker → KindPicker → Name → OpeningBalance → Confirm → Done`
  → `account_service.create`.
- `JoinViaInviteDialog`: "Join '{book}' as {role}?" → `invite_service.accept` → switch.

#### 3. Commands (`handlers/commands.py`)
`/start invite_{token}` deep-link (`CommandStart(deep_link=True)`) → resolve invite → start
`JoinViaInviteDialog`. `/books` → book-picker dialog → `book_service.switch`.

All via services only (D22 grep-guard stays green).

### Success Criteria — Automated
- [ ] Dialog unit tests (mocked Bot + `BgManager`): create-book persists a book; create-account
      persists an account; invite-accept adds a member.
- [ ] `/start invite_<token>` routes to the join dialog; `/books` switch updates `active_book_id`.
- [ ] D22 grep-guard clean; `make typecheck`+`lint` pass.
#### Manual
- [ ] `/newbook`-style flow creates a book; `/books` switches it; the rolling message updates.

**Pause for manual confirmation before Phase 7 relies on the bot.**

---

## Phase 7: Mini-App — Tailwind/shadcn shell, book picker, accounts, invites

### Changes Required

#### 1. Tailwind + hand-rolled shadcn-pattern components
Add `globals.css` (@tailwind directives), wire in `layout.tsx`; build a minimal component set
(`Card`, `Button`, `Tabs`, `Drawer`/sheet, `Select`, `Badge`) using Tailwind + `cva`/`clsx`/
`tailwind-merge` (deps already present). (No shadcn CLI/registry — hand-rolled to stay
self-contained.)

#### 2. App shell + tabs
Convert the single page into a shell with a **book picker** (header dropdown → `POST
/books/{id}/switch`, store new JWT) and tabs: **Books** (list + create), **Accounts** (list +
create Drawer), **Settings → Invites** (pending list + "Invite member" form with copy-link).

#### 3. Data + client
TanStack Query hooks over the new endpoints; extend `api-client` with the authed verbs;
regenerate `packages/api-types` (`pnpm types:gen` against the running API). Fluent strings for the
new UI (en/ru).

### Success Criteria — Automated
- [ ] `types:gen` includes the new paths/schemas; `pnpm -F miniapp typecheck`+`lint`+`build` pass.
- [ ] `make check` green across the whole workspace.
#### Manual (real phone)
- [ ] Create book → switch → header reflects it; create account → appears in Accounts tab; mint an
      invite → copy link → second account opens it → lands in the book; Editor can't delete (403).

---

## Testing Strategy

- **Unit/DB-free**: RBAC matrix (4×8), `Money` round-trip, invite state machine (pure parts).
- **Integration (compose PG + savepoint rollback, extends the M1 fixtures)**: books CRUD + switch,
  invites lifecycle (create/accept/double/expired/revoked/already-member), accounts CRUD + FK
  protection, currencies seed + override visibility, RBAC denial paths per endpoint.
- **API**: httpx `AsyncClient` with the test container (test settings + savepoint UoW) — reuse M1's
  fixture, add helpers to mint a JWT for an arbitrary `(user, book, role)` and to seed a second user.
- **Bot**: mocked-Bot dialog tests (aiogram-dialog `BgManager`), feed_update for the invite
  deep-link (extends M1's `test_start_dispatch`).
- **Mini-App**: build + typecheck; first vitest component tests optional.

## Decision Log (recommended — please confirm/override)

- **D-M2-1 (UI stack):** hand-roll shadcn-pattern components on Tailwind + `cva` (deps already
  declared) rather than run the shadcn CLI — keeps the repo self-contained and offline-buildable.
- **D-M2-2 (book authz split):** rename = **admin+**, archive/delete = **owner** (`book.delete`).
  Milestone text says "admin+" for PATCH; splitting archive to owner is safer for a destructive op.
- **D-M2-3 (switch surface):** `POST /books/{id}/switch` returns a fresh `TokenOut`; the Mini-App
  replaces its stored JWT. The bot's `/books` switch updates `tg_chats.active_book_id` server-side.
- **D-M2-4 (invite accept idempotency):** same user re-accepting a used token → 200 (no-op);
  different user on a used single-use token → 409 `already_used`. Tokens are single-use.
- **D-M2-5 (test isolation):** keep compose-DB + per-test savepoint (no testcontainers) — matches
  M1, fast, local-dev only.
- **D-M2-6 (money):** `opening_balance` is the first `Money` field; wire = decimal string; server
  stores `NUMERIC(20,8)`; no `big.js` in the Mini-App yet (display only until M3).

Open for your call: **(a)** include the full bot aiogram-dialog suite in M2 as written, or ship
API+Mini-App first and fast-follow the bot dialogs (Phase 6 could split); **(b)** any of D-M2-1..6.

## Definition of Done (M2)

Automated: `make check` green · `0002` applies (45+ system currencies, idempotent) · books/invites/
accounts/rbac integration suites pass · `types:gen` reflects the new contract. Manual: two users
share a book across roles (owner/editor) via an invite deep-link · book switch re-mints the JWT and
updates the bot's rolling message · a USD account with opening balance 500 exists · Editor is denied
book deletion (UI + 403).

## References
- Milestone source: [thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md](thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md) §2 (lines 479–573)
- M1 (built): commit 6d42358 · patterns for services/deps/tests to mirror
