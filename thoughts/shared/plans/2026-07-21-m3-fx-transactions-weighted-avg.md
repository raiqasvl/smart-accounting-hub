---
date: 2026-07-21
researcher: i.gorvier
git_commit: 1f62277
branch: main
repository: smart-accounting-hub
topic: "M3 — FX transactions + weighted-average headline"
tags: [plan, m3, fx, transactions, weighted-average, frankfurter, aiogram-dialog, miniapp, recharts, alembic]
status: ready-for-dev
last_updated: 2026-07-21
last_updated_by: i.gorvier
decisions_confirmed: "CONFIRMED 2026-07-21 — D-M3-1..7 accepted as written; commands /trade + /avg; single-leg in M3, two-leg → M4"
based_on: thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md §3 (M3)
grounded_in: "post-M2 codebase research (2026-07-21 sub-agent pass) — see Current State"
---

# M3 — FX transactions + weighted-average headline

## Overview

**The product's headline ships at the end of this milestone.** On top of M2's accounts we add the
`fx_transactions` write path, the **weighted-average rate** aggregate
(`SUM(amount_quote·rate) / SUM(amount_quote)`, D16), an hourly **Frankfurter** FX-rate fetcher (rate
hints only, informational), and the two user surfaces: a bot `RecordTradeDialog` + `/avg`, and the
Mini-App **Trades** and **Reports** tabs (Recharts + `big.js`).

M3 ends with: two trades recorded on either surface → `/avg sell USD` and the Reports card both print
`₽90.27 (2 trades, $11,000)`, with a chart of individual rates vs. the weighted average.

## Current State (post-M2, commit 1f62277)

Research pass (2026-07-21) established the actual ground truth — richer than the milestone doc assumed:

- **Schema already exists.** `fx_transactions` and `exchange_rates` are **fully present in
  `0001_initial`** (`migrations/versions/2026_07_11_0001_initial_initial.py`), including the enums
  `transaction_kind{plain_cash,internal_transfer,fx_conversion}` / `transaction_direction{buy,sell}`
  (native PG types, `create_type=False`), `archived`, `linked_transaction_id` (self-FK), `fee`,
  `category_id`, and all three report indexes (`(book_id, quote, direction, occurred_at DESC)`,
  `(book_id, occurred_at DESC)`, partial on `linked_transaction_id`). **The one gap: no
  `idempotency_key` column** (D28) → needs a new migration `0003`.
- **Models present**: `models/fx_transaction.py` (`FxTransaction` + both StrEnums, exported from
  `models/__init__.py`), `models/exchange_rate.py`. `models/fields.py` provides `money_amount`
  (`Numeric(20,8)`), `currency_code` (`String(8)`), `bigserial_pk`, `timestamptz`. `Base` carries the
  `created_at/updated_at` mixin.
- **`fx/` is comment-stubs only**: `fx/clients.py` (intended `FxClient` Protocol + `FrankfurterClient`)
  and `fx/refresh.py` (`refresh_loop`) have no code. `.env.example` + `Settings` already carry
  `FRANKFURTER_BASE_URL=https://api.frankfurter.dev/v1` and `FX_REFRESH_INTERVAL_SECONDS=3600`.
- **No `exchange_rates` or `transactions` repository yet.** Repos follow `__init__(self, uow)` →
  `self._session = uow.session`, queries-only, `add`+`flush` on insert, post-flush `refresh` for
  NUMERIC scale (`AccountsRepo.insert`).
- **Service pattern** (mirror `AccountService`): ctor `(uow, ...repos, BookMembersRepo)`; every method
  `async with self._uow:` (tx boundary) → `role = await resolve_role(self._members, book_id, user_id)`
  → `require_permission(role, "...")` → returns `*Out.model_validate(row)`.
- **RBAC** (`auth/rbac.py`) already grants `tx.write` (OWNER/ADMIN/EDITOR) and `tx.read` (all) — **no
  matrix change needed.**
- **API** (`apps/api/.../main.py`): routers nested under `APIRouter(prefix="/api/v1")`; `DishkaRoute`
  + `FromDishka[T]`; `extract_claims(request, jwt)` first line; authz is **service-layer**, not a dep;
  D24 handler + `RequestIdMiddleware` present. **`FastAPI(...)` has NO `lifespan=`** — must add for the
  refresh task. Routers must **not** `from __future__ import annotations`.
- **Bot**: dialogs mirror `dialogs/create_account.py` (`Dialog`/`Window`/`Select`/`TextInput`/`Button`,
  getter takes `dialog_manager` by keyword, on-success pulls a service via
  `service(manager, Cls)` = `manager.middleware_data["dishka_container"].get(Cls)`). `.ftl` catalogues
  live at `packages/core/.../i18n/{en,ru}/main.ftl`. Commands in `handlers/commands.py`;
  **`set_my_commands` is not called anywhere** (M2-triage item — see Dependencies).
- **Mini-App**: single route, tab state in `components/app-shell.tsx`; hand-rolled UI kit
  `components/ui.tsx` (`Card/Button/Badge/Input/Select/Field/Spinner/Drawer`, no `Tabs` primitive);
  typed fetch client `lib/api-client.ts` (JWT in sessionStorage, 401→re-auth retry, `switchBook`
  re-mints JWT), TanStack hooks `lib/hooks.ts`, hand-rolled i18n `lib/strings.ts` (EN/RU dicts).
  **Recharts `^2.13` installed; `big.js` NOT installed.** `packages/api-types/src/money.ts` is a
  `type Money = string` placeholder awaiting big.js helpers.
- **Tests**: compose PG + savepoint rollback. `apps/api/tests/conftest.py` provides `client`, `login`
  (real `/auth/telegram` onboarding → bearer), `db` (seed rows the HTTP surface can't). `respx` is a
  dev-dep for mocking the FX HTTP client.

## Desired End State

`make check` green. Migration `0003` adds `idempotency_key` (+ partial unique). A trade recorded via
API/bot/Mini-App persists exactly `(amount_quote, rate, amount_base=amount_quote·rate, fee, occurred_at)`
(D16). `GET /books/{id}/reports/weighted-avg-rate?quote=USD&direction=sell` returns the aggregate with
`sample_count`/`sum_amount_quote`. The Frankfurter loop populates `exchange_rates` on startup. Bot
`/avg` and the Mini-App Reports card render the same number; the Reports chart plots each trade's rate
with the weighted-average line. Verification = §Definition of Done.

## What We're NOT Doing (M3 out of scope → M4/v1.1)

- **Two-leg transactions** — `internal_transfer` and `fx_conversion` (the `linked_transaction_id`
  pairing) move to **M4** with the transfer flow. M3 records **single-leg `plain_cash` trades only**
  (that is all the weighted-average headline needs). *(D-M3-1)*
- **Categories on trades** — the `category_id` FK exists but stays NULL until M4 categories land.
- **CSV export, charts beyond the one Reports line chart, EN/RU polish** — M4.
- **Multiple FX sources / crypto spot** — Frankfurter (fiat, ECB) only; CoinGecko etc. are v1.1.
- **Editing that rewrites history semantics** — `PATCH` recomputes `amount_base`; `DELETE` is
  soft-archive (D29), never hard delete.

## Implementation Approach

Bottom-up along the locked layering, six phases; each ends with automated verification, the two
surfaces add manual gates. Conventions unchanged from M1/M2 (services own the tx via UoW; typed domain
errors → D24 / Fluent; Money crosses as a decimal string, D23). Two M3-specific conventions:

- **Rate semantics (D16, D-M3-3):** `quote_currency_code` = the traded/foreign currency (USD),
  `base_currency_code` = the settlement/home currency (RUB). `rate` = **base per one quote** (RUB per
  USD). `amount_base = amount_quote · rate`. The weighted average over persisted rows is
  `SUM(amount_quote · rate) / SUM(amount_quote)`; `exchange_rates` is **informational only** (a hint).
- **Idempotency (D28, D-M3-2):** a client mints a UUID per Confirm; server upserts on
  `(book_id, idempotency_key)` and returns the existing row (200 + `Idempotent-Replayed: true`) on repeat.

---

## Phase 1: Schemas + errors + repos + migration `0003`

### Changes Required

#### 1. `schemas/transaction.py` (new) + `schemas/report.py` (new)
- `TransactionCreateIn{direction: Literal["buy","sell"], base_currency_code, quote_currency_code,
  amount_quote: Money, rate: Money, base_account_id: int | None = None,
  quote_account_id: int | None = None, fee: Money = Decimal("0"), fee_currency_code: str | None = None,
  occurred_at: datetime | None = None, note: str | None = None, idempotency_key: str | None = None}`.
  `amount_quote`/`rate` use `Field(gt=0)`; `fee` `Field(ge=0)`.
- `TransactionPatchIn{rate?: Money, amount_quote?: Money, note?: str, occurred_at?: datetime,
  archived?: bool}` — patching `rate`/`amount_quote` recomputes `amount_base` in the service.
- `TransactionOut{id, book_id, created_by_user_id, kind, direction, base_currency_code,
  quote_currency_code, amount_quote: Money, rate: Money, amount_base: Money, fee: Money,
  fee_currency_code, base_account_id, quote_account_id, occurred_at, note, archived}`
  (`ConfigDict(from_attributes=True)`).
- `schemas/report.py`: `WeightedAvgReportOut{book_id, quote_currency_code, direction,
  weighted_avg_rate: Money | None, sample_count: int, sum_amount_quote: Money, period_from: datetime |
  None, period_to: datetime | None}`. Add both to `schemas/__init__.py`.

#### 2. New domain errors (`errors.py`)
`TransactionNotFound`(extends `NotFound`, `transaction_not_found`, 404),
`AccountNotInBook`(422, `account_not_in_book`), `AccountCurrencyMismatch`(422,
`account_currency_mismatch`), `InvalidAmount`(422, `invalid_amount`). Same class-attr pattern as the
existing 16 errors; caught by the single `AppError` handler.

#### 3. `repositories/transactions.py` (new)
`__init__(self, uow)`; methods: `insert(**fields) -> FxTransaction` (add+flush+**refresh** for NUMERIC
scale), `get(tx_id) -> FxTransaction | None`, `get_by_idempotency(book_id, key) -> FxTransaction |
None`, `list_for_book(book_id, *, direction=None, quote_currency_code=None, account_id=None,
occurred_after=None, occurred_before=None, archived=False, cursor=None, limit=50) -> list[...]`
(D25 cursor `(occurred_at DESC, id)`), `update(tx_id, **fields) -> FxTransaction | None`.

#### 4. `repositories/exchange_rates.py` (new)
`insert_many(rows)` (bulk INSERT of `(base, quote, rate, source, fetched_at)`),
`latest(base, quote) -> ExchangeRate | None` (most recent by `fetched_at`),
`latest_cross(base, quote) -> Decimal | None` — cross-rate via the USD pivot the fetcher stores:
`base_per_quote = (USD→base) / (USD→quote)` from the two latest USD-based rows (returns `None` if
either leg is missing). Used only for the informational hint.

#### 5. `repositories/reports.py` (new)
`weighted_avg_rate(book_id, quote_currency_code, direction, occurred_after=None,
occurred_before=None) -> tuple[Decimal | None, int, Decimal]` returning
`(SUM(amount_quote·rate)/SUM(amount_quote), COUNT(*), SUM(amount_quote))` in one query over the
`(book_id, quote, direction, occurred_at DESC)` index, filtered `archived = false`.

#### 6. Migration `0003_add_tx_idempotency` (`down_revision="0002_seed_currencies"`)
`op.add_column("fx_transactions", sa.Column("idempotency_key", sa.Text(), nullable=True))` +
`op.create_index("uq_fx_transactions_book_idempotency", "fx_transactions",
["book_id", "idempotency_key"], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))`.
Add `idempotency_key` to `FxTransaction` model. `downgrade` drops both. Follow the
`YYYY_MM_DD_0003_*` filename convention + `op.f(...)` naming.

#### 7. Register repos in `ioc.py`
`transactions_repo = provide(TransactionsRepo, Scope.REQUEST)`,
`exchange_rates_repo = provide(ExchangeRatesRepo, Scope.REQUEST)`,
`reports_repo = provide(ReportsRepo, Scope.REQUEST)` (+ imports).

### Success Criteria — Automated
- [ ] `make migrate` applies `0003`; `alembic check` clean; `alembic downgrade -1` drops the column+index.
- [ ] `Money` round-trips `amount_base = "993000.00000000"` with no precision loss.
- [ ] `pytest` unit: `reports.weighted_avg_rate` on fixture `[(1000, 90.0), (10000, 90.3)]` →
      `Decimal("90.27272727…")` within ε; empty set → `(None, 0, 0)`.
- [ ] `make typecheck` + `make lint` pass.

---

## Phase 2: TransactionService + ReportService

### Changes Required

#### 1. `services/transaction_service.py`
Ctor `(uow, TransactionsRepo, AccountsRepo, CurrenciesRepo, BookMembersRepo)`.
- `record(book_id, user_id, dto) -> TransactionOut` — `require_permission(role, "tx.write")`; if
  `dto.idempotency_key` and `get_by_idempotency` hits → return existing (flag replay to the router);
  validate `base_currency_code`/`quote_currency_code` visible → `CurrencyUnknown`; if
  `base_account_id`/`quote_account_id` given, load & assert `account.book_id == book_id`
  (`AccountNotInBook`) and `account.currency_code == *_currency_code` (`AccountCurrencyMismatch`);
  compute `amount_base = amount_quote * rate`; `occurred_at = dto.occurred_at or now()`; insert
  `kind="plain_cash"`.
- `list(book_id, user_id, filters, cursor, limit) -> list[TransactionOut]` (`tx.read`).
- `get(tx_id, user_id) -> TransactionOut` — load, resolve role for `tx.book_id`, `tx.read`.
- `patch(tx_id, user_id, dto) -> TransactionOut` — bare-id pattern; `tx.write`; recompute `amount_base`
  when `rate`/`amount_quote` change.
- `archive(tx_id, user_id) -> None` — `tx.write`; sets `archived=True` (soft delete, D29).

#### 2. `services/report_service.py`
Ctor `(uow, ReportsRepo, BookMembersRepo)`. `weighted_avg(book_id, user_id, quote_currency_code,
direction, period_from=None, period_to=None) -> WeightedAvgReportOut` — `tx.read`; wraps the repo
tuple into the DTO.

#### 3. Register services in `ioc.py` + export from `services/__init__.py`.

### Success Criteria — Automated
- [ ] `record` persists `amount_base = amount_quote·rate`; returned as string with NUMERIC scale.
- [ ] Idempotent replay: same `idempotency_key` twice → one row, both calls return it.
- [ ] Unknown currency → 422; account from another book → 422; account currency mismatch → 422.
- [ ] `patch` rate recomputes `amount_base`; VIEWER `record` → 403; non-member → 403.
- [ ] `weighted_avg` end-to-end over seeded rows equals the Phase-1 unit result.

---

## Phase 3: Frankfurter fetcher + lifespan wiring

### Changes Required

#### 1. `fx/clients.py`
`class FxClient(Protocol): async def fetch_latest(self, base: str) -> dict[str, Decimal]`.
`class FrankfurterClient` — ctor `(http: httpx.AsyncClient, base_url: str)`; `fetch_latest(base)` GETs
`{base_url}/latest?base={base}`, returns `{code: Decimal(str(v))}`. No API key.

#### 2. `fx/refresh.py`
`async def refresh_loop(*, sessionmaker, client, interval_seconds, base="USD") -> None` — loop:
`rates = await client.fetch_latest(base)`; open a session, `ExchangeRatesRepo.insert_many([...
source="frankfurter", fetched_at=now()])`, commit; `except Exception: log.exception(...)`;
`await asyncio.sleep(interval_seconds)`.

#### 3. DI + lifespan
Register `httpx.AsyncClient` (APP scope, closed on shutdown) and `FrankfurterClient` in `ioc.py`. In
`apps/api/.../main.py` add `lifespan=` to `FastAPI(...)`: on startup
`asyncio.create_task(refresh_loop(sessionmaker=..., client=..., interval_seconds=settings...))`; on
shutdown cancel it. Guard with a `settings.FX_REFRESH_ENABLED`-style flag so tests don't hit the net.

#### 4. `GET /api/v1/books/{book_id}/fx/latest?base=&quote=` (informational hint)
`routers/fx.py` → `ExchangeRatesRepo.latest_cross` via a thin `FxService` (or reuse ReportService);
`tx.read`. Returns `{base, quote, rate: Money | None, as_of: datetime | None, source}`.

### Success Criteria — Automated
- [ ] `pytest fx/test_frankfurter.py` (respx-mocked): `fetch_latest("USD")` parses to `Decimal`.
- [ ] `refresh_loop` one iteration (respx + real test DB) inserts ≥1 `exchange_rates` row.
- [ ] `latest_cross("RUB","USD")` from seeded USD rows returns RUB-per-USD; missing leg → `None`.
- [ ] Lifespan task is created/cancelled cleanly (no warning on shutdown); disabled under test settings.

---

## Phase 4: API — transactions + reports routers

### Changes Required

#### 1. `routers/transactions.py` (mirror `accounts.py`, `route_class=DishkaRoute`, no future-annotations)
`POST /books/{book_id}/transactions` → `record`; on idempotent replay set response header
`Idempotent-Replayed: true`. `GET /books/{book_id}/transactions` (query filters + `?cursor=&page_size=`,
D25 envelope `{items, next_cursor, has_more}`). `PATCH /transactions/{tx_id}` → `patch`.
`DELETE /transactions/{tx_id}` → `archive` (returns `{"archived": tx_id}`).

#### 2. `routers/reports.py`
`GET /books/{book_id}/reports/weighted-avg-rate?quote=&direction=&from=&to=` → `WeightedAvgReportOut`.

#### 3. Register both in `main.py`; regenerate `packages/api-types` (`pnpm types:gen`).

### Success Criteria — Automated
- [ ] `pytest apps/api/tests/test_transactions.py`: create→list→patch→archive happy path + 403s
      (VIEWER write, non-member) + idempotent replay header.
- [ ] `test_reports.py`: two trades → endpoint returns `90.272727…`, `sample_count=2`,
      `sum_amount_quote="11000.00000000"`.
- [ ] `types:gen` includes the new paths/schemas; `make check` (Python) green.

---

## Phase 5: Bot — RecordTradeDialog + `/avg`

### Changes Required

#### 1. States (`dialogs/states.py`): `RecordTrade{direction, base_currency, quote_currency,
base_account, quote_account, amount, rate, occurred_at, note, confirm, done}`;
`AvgReport{direction, quote_currency, period, result}`.

#### 2. `dialogs/record_trade.py` (mirror `create_account.py`)
`Select` for direction (buy/sell) and for currency picks (items from `CurrencyService.list_for_book`
— fixes the M2 free-text-typo problem), account picks filtered by chosen currency
(`AccountService.list_for_book`), `TextInput` for amount/rate/note, a `Rate` window that shows the
Frankfurter hint (`fx/latest`) as a `Format` line, `Confirm` → `TransactionService.record` (mint a
fresh `idempotency_key` in `dialog_data`). Standard error handling (`error-bad-amount`,
`error-generic`).

#### 3. `dialogs/avg_report.py`
Direction → quote currency → period (last-30d / this-month / all-time) → renders
`ReportService.weighted_avg` inline (`avg-result` key, interpolating rate/count/sum).

#### 4. `handlers/commands.py`: `/trade` → `RecordTrade.direction`, `/avg` → `AvgReport.direction`
(mirror `/newaccount`). Register both dialogs in `dialogs/__init__.py::all_dialogs()`.

#### 5. i18n: add `# --- record trade ---` / `# --- avg report ---` sections to **both**
`i18n/{en,ru}/main.ftl` (`trade-*`, `avg-*`); reuse shared `btn-*`/`error-*` keys.

### Success Criteria — Automated
- [ ] Dialog unit tests (mocked Bot + `BgManager`): record-trade persists a `plain_cash` row;
      avg-report reads back the weighted average. D22 grep-guard clean.
#### Manual
- [ ] `/trade` records "sell 1000 USD @ 90.0" then "sell 10000 USD @ 90.3"; `/avg sell USD all-time`
      prints `Weighted avg sell USD: ₽90.272727 (2 trades, $11,000)`. Currency pickers (no free text).

**Pause for manual confirmation before Phase 6 relies on the bot data.**

---

## Phase 6: Mini-App — Trades + Reports tabs (big.js + Recharts)

### Changes Required

#### 1. Dependencies + types
`pnpm -F @smart-accounting/miniapp add big.js && add -D @types/big.js`. Implement
`packages/api-types/src/money.ts` (`toBig`, `add`, `mul`, `format` helpers over the `Money` string).
Regenerate `api.d.ts`; add `TransactionOut/TransactionCreateIn/WeightedAvgReportOut` aliases to
`packages/api-types/src/index.ts`.

#### 2. Client + hooks
`lib/api-client.ts`: `fetchTransactions(bookId, filters)`, `createTransaction(bookId, body)`,
`fetchWeightedAvg(bookId, params)`, `fetchFxLatest(bookId, base, quote)`. `lib/hooks.ts`:
`useTransactions(bookId, filters)` key `['trades', bookId, filters]`, `useCreateTransaction`
(invalidate `['trades', bookId]` + `['report', bookId]`), `useWeightedAvg(bookId, params)`
key `['report', bookId, params]`.

#### 3. Tabs
Extend `Tab` union in `app-shell.tsx` with `'trades' | 'reports'`; add nav entries + `tab-trades`/
`tab-reports` keys to `strings.ts` (EN/RU). New `components/trades-tab.tsx` (list via `Card`s, money
via big.js `format`, `+` opens a `Drawer` create form reusing the M3 currency `Select`s) and
`components/reports-tab.tsx` (direction toggle + currency `Select` + period; big weighted-avg number,
sample count / sum; a Recharts `LineChart` of trade `rate` over `occurred_at` with a `ReferenceLine`
at the weighted average — colors from `var(--accent)`/`var(--muted)`).

### Success Criteria — Automated
- [ ] `pnpm -F @smart-accounting/miniapp typecheck && lint && build` pass; `make check` green workspace-wide.
#### Manual (real phone)
- [ ] Record a trade in the app → appears in Trades; Reports shows the same `₽90.27` as `/avg`; the
      chart plots two points at 90.0 / 90.3 with the average line; money formats cleanly (no
      `90.00000000`).

---

## Testing Strategy

- **Unit/DB-free**: weighted-avg arithmetic (`Decimal`, divide-by-zero, single row), `amount_base`
  computation, `latest_cross` math, Money round-trip, Frankfurter parse (respx).
- **Integration (compose PG + savepoint)**: transactions CRUD + idempotent replay + role gates + filter/
  cursor; reports endpoint; refresh_loop one-shot insert. Reuse `client`/`login`/`db` fixtures; seed a
  second (Editor) member via `db` + a `book_members` row.
- **Bot**: mocked-Bot dialog tests for record-trade + avg-report (extend the M2 dialog test harness;
  the autouse router-detach fixture already handles singleton routers).
- **Mini-App**: `build` + `typecheck`; optional vitest for the big.js money formatter.

## Decision Log (please confirm/override)

- **D-M3-1 (scope):** M3 records **single-leg `plain_cash`** trades only; `internal_transfer` +
  `fx_conversion` (two linked rows) defer to M4. The headline weighted-average needs only single legs.
- **D-M3-2 (idempotency):** add `idempotency_key` + partial unique `(book_id, idempotency_key)` via
  `0003`; client mints a UUID per Confirm; replay → existing row + `Idempotent-Replayed` header (D28).
- **D-M3-3 (rate semantics):** `quote`=traded currency, `base`=settlement currency, `rate`=base per
  quote, `amount_base = amount_quote·rate`; weighted avg `= Σ(amount_quote·rate)/Σ(amount_quote)` (D16).
- **D-M3-4 (FX fetcher):** hourly Frankfurter `base=USD`; cross-rate hints via USD pivot;
  `exchange_rates` informational only; guarded by a settings flag so tests/offline don't fetch.
- **D-M3-5 (delete):** `DELETE` = soft `archived=true` (D29); reports filter `archived=false`.
- **D-M3-6 (account link optional):** `base/quote_account_id` optional; when present, must be in-book +
  currency-matching (else 422). Balances/ledger integrity land with M4 transfers.
- **D-M3-7 (Mini-App money):** add `big.js`; implement `api-types/money.ts` helpers; display via
  `format`, never raw. (Closes the M2 "raw `500.00000000`" gap for trade amounts.)

**CONFIRMED (2026-07-21):** D-M3-1 stands (two-leg `fx_conversion` deferred to M4); bot commands are
**`/trade`** and **`/avg`**; D-M3-2..7 accepted as written. No open questions remain.

## Dependencies / sequencing

- **Blocked by M2 runtime-UX fixes** (per handoff hard rule): M3 must not start until M2 is usable
  end-to-end on device. The M3 bot dialogs should be added to `set_my_commands` **as part of the M2
  command-menu fix** (`/trade`, `/avg` included) so they're discoverable.
- M3 currency **pickers** in `RecordTradeDialog` directly remedy the M2 "free-text currency typo"
  triage item for the trade path.

## Definition of Done (M3)

Automated: `make check` green · `0003` applies (idempotency, idempotent) · transactions/reports/fx
integration suites pass · `types:gen` reflects the contract. Manual: two trades recorded on either
surface · `/avg` and the Mini-App Reports card both print `₽90.272727 (2 trades, $11,000)` · the chart
shows two rate points + the average line · a second (Editor) user records a trade and sees consistent
results · the FX loop has populated `exchange_rates`.

## References
- Milestone source: [2026-05-01-mvp-scope-and-milestones.md](thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md) §3 (M3), D16/D23/D25/D28/D29
- Patterns to mirror: `packages/core/.../services/account_service.py`, `repositories/accounts.py`,
  `apps/api/.../routers/accounts.py`, `apps/bot/.../dialogs/create_account.py`,
  `apps/miniapp/src/components/accounts-tab.tsx`
- Product overview: [2026-07-21-mvp-product-guide.md](thoughts/shared/reference/2026-07-21-mvp-product-guide.md)
