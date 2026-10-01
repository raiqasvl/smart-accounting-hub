---
date: 2026-07-29
author: i.gorvier (GitHub raiqasvl)
repository: smart-accounting-hub
branch: main
topic: "Handoff — M3 + M4 shipped; MVP (M1–M4) is feature-complete. Next: device test, then M5."
status: current
supersedes: 2026-07-21-m2-manual-test-triage.md
---

# Handoff — MVP feature-complete (M1–M4 shipped)

**M1–M4 are code-complete, committed, and pushed to `origin/main`.** The MVP scope defined in the
milestone plan is done: auth, books/invites/accounts/currencies, the weighted-average FX headline,
and the categories/transfers/charts/EN-RU/CSV round-out.

**The single most important open item: none of M3 or M4 has been exercised on a real phone.**
Everything is verified by automated gates only. This is exactly the gap that made M2 feel "raw" the
first time. **Do the device pass before starting M5.**

---

## Hard rules (do not violate)

- **Commits: author is the user** (`i.gorvier <raiqasvl@users.noreply.github.com>`). **NEVER** add
  `Co-Authored-By`, "Generated with", or any AI trailer. **Commit only when the user asks.**
- **Work directly on `main`** — no worktrees, no feature branches.
- **Preserve `thoughts/`** — plans/research/handoffs are the project's design history. Keep and
  commit them, never delete. (The user was burned by this once.)
- **D22**: `apps/bot` calls `smart_accounting.services.*` directly and **never** imports
  `smart_accounting.{models,repositories}`, never HTTPs to `apps/api`. Enforced by a grep-guard.
- **Authz is service-layer**, not a FastAPI dependency: `services/authz.resolve_role(...)` then
  `auth.rbac.require_permission(...)`, inside the service's `async with self._uow` block.
- **Money**: `NUMERIC(20,8)` in PG / `Decimal` in Python / **decimal string** in JSON (D23).
- **API routers must NOT** `from __future__ import annotations` (DishkaRoute needs concrete types).
- `.claude/settings.json`, `CLAUDE.md`, `AGENTS.md` are agent config → commit separately from product.

---

## Commit ledger (`main`, all pushed)

| Commit | What |
|---|---|
| `1acfbe9` | M1 — auth slice |
| `9dde440` · `41c2f17` · `dd9604e` | M2 — backend, bot dialogs, Mini-App shell |
| `b9f8d25` | agent guide + settings (config, not product) |
| `30eaca3` | **M3 — FX transactions + weighted-average** across API, bot, Mini-App |
| `33a9698` | M3/M4/M5 plans, MVP product guide, M2 triage resolved |
| `65c8b07` | **M4 — categories, movements, balance chart, EN/RU parity, CSV export** |
| `72a3fdc` | records the D-M4-5 single-row movement decision |

**Gates at commit time:** 144 pytest · 3 vitest · mypy (107 files) · ruff · `alembic check` · D22
grep-guard · `make i18n-check` · Mini-App tsc + oxlint + `next build` + prettier.

---

## What exists now

**Core** (`packages/core/src/smart_accounting/`) — services: `account, auth, authz, book, category,
currency, fx, invite, report, tg_chat, transaction, user`. Repos mirror them plus `transactions,
exchange_rates, reports, categories`. `fx/{clients,refresh}.py` hold the Frankfurter client and the
hourly refresh loop.

**API** (`apps/api/.../routers/`) — `auth, me, books, invites, accounts, currencies, transactions,
reports, fx, categories, transfers, health`. Highlights:
`POST/GET /books/{id}/transactions` · `GET /books/{id}/reports/weighted-avg-rate` ·
`GET /books/{id}/reports/account-balance` · `GET /books/{id}/fx/latest` ·
`POST /books/{id}/transfers` · `POST /books/{id}/fx-conversions` ·
`GET/POST /books/{id}/categories` + `PATCH/DELETE /categories/{id}` + `POST /categories/{id}/move` ·
`GET /books/{id}/transactions/export.csv`.

**Bot** — dialogs `create_book, create_account, join_invite, books_menu, record_trade, avg_report,
internal_transfer` (+ `widgets.py` for shared category/account option lists). Commands, all
registered via `set_my_commands` in `menu.py` (en+ru): `/start /trade /avg /transfer /books /newbook
/newaccount`.

**Mini-App** — tabs Books · Accounts · Trades · Reports · Settings (Categories live *inside*
Settings). Reports carries the weighted-average card + rate chart **and** the account-balance chart.
`big.js` formats all money. `lib/strings.ts` is the EN/RU catalogue (hand-rolled, **not** Fluent).

**Migrations** — `0001_initial`, `0002_seed_currencies`, `0003_tx_idempotency`. Categories, ltree,
GIST, both tx enums, `archived`, `linked_transaction_id` were all already in `0001`.

---

## Design decisions worth knowing (and why)

- **D-M4-5 — a transfer/FX-conversion is ONE row, not two linked rows.** The row touches both
  accounts (`quote_account_id` = money out, `base_account_id` = money in). A mirror "buy" leg would
  register a USD→EUR conversion as *"bought USD"* and corrupt the headline average.
  → `linked_transaction_id` is currently **unused** (reserved for v1.1 splits/refunds).
- **Internal transfers are excluded from the weighted average** (`kind != internal_transfer`): they
  carry a synthetic `rate = 1`, so counting them would drag the average toward 1. FX conversions
  *are* counted — they are real trades.
- **Balance sign rule (uniform):** on `sell` the quote account pays out and the base account
  receives; `buy` is the mirror. Movements are recorded as `sell`, so one rule covers everything.
- **ltree labels are numeric category ids** (root `"5"`, child `"5.9"`). Renames never touch paths;
  a move is one `UPDATE ... subpath(...)` over the subtree.
- **`subpath(path, nlevel(path))` is an out-of-range offset in Postgres** — the move therefore
  rewrites strict descendants in one statement and sets the node's own path directly. (Also:
  the function is `nlevel`, not `nlabel`.)
- **`make i18n-check` is a Python script**, not grep: a byte-oriented `grep '[А-Я…]'` false-positives
  on em dashes, arrows and middle dots. Exempts `menu.py` (Telegram wants literal per-locale command
  strings) and the catalogues themselves.
- **D-M4-4** — Mini-App i18n stays the hand-rolled `strings.ts`; `@fluent/*` was dropped. Deviates
  from D13 but matches shipped code and is simpler.
- **D-M4-6** — CSV export is gated by `tx.read`, so viewers may export (read-only data).
- **Idempotency (D28)** — every write path takes an optional `idempotency_key`; a replay returns the
  original row with an `Idempotent-Replayed: true` header.

### Gotchas carried over
- aiogram-dialog getters receive `dialog_manager` **by keyword**, not `manager`.
- Bot routers/dialogs are module-level singletons; `apps/bot/tests/conftest.py` has an autouse
  fixture that detaches `_parent_router` between tests.
- Register every new repo/service in `packages/core/.../ioc.py` and every router in
  `apps/api/.../main.py`.
- Adding a constructor arg to a service breaks the hand-built instances in `packages/core/tests/` —
  update those helpers.

---

## Known gaps / deliberately deferred

- **Rolling single-message bot UX** (planned in M2) was never built; dialogs rely on
  aiogram-dialog's default message reuse. Flag it if the chat feels cluttered on device.
- **P&L-by-currency chart** → v1.1 (D-M4-7). Only the account-balance chart shipped.
- **Mini-App fetches only the first page of trades** — the API supports cursor pagination
  (`?cursor=&page_size=`), the UI does not page yet.
- **CSV export silently caps at 10 000 rows** (`EXPORT_LIMIT` in `transaction_service.py`). No
  warning is surfaced to the user.
- **`fee` is stored and exported but not applied** to the balance series or the weighted average.
- **No `/lang` command** — locale is auto-detected from Telegram's `language_code` (D-M4-8).
- **Categories have no bot-side management** (create/rename/move) — picker only; manage in the app.
- Archived categories are excluded from the tree unless `?include_archived=true`; the Mini-App never
  passes it, so archiving hides a category from the UI with no way back except the API.

---

## Next works (in priority order)

### 1. Device pass on M3 + M4  ← do this first
Run the stack (below) and walk the whole flow on a real phone:
- Bot: `/trade` (direction → currency picker → amount → rate w/ hint → category → confirm),
  `/avg` (all three periods), `/transfer` (to-account list must be currency-filtered), `/books`.
  Confirm the command menu shows all seven commands, in Russian for a `ru` account.
- Mini-App: Trades list + record drawer + **Export CSV**; Reports (weighted-average number must match
  `/avg`, both charts render, theme colors follow Telegram); Settings → Categories (create, nest,
  move, archive, delete — deleting a parent must 409).
- Two-user check: invite a second account as Editor; both see the same trades; Viewer can export but
  not write.
Capture anything broken in a new triage doc and fix before M5.

### 2. Quick wins surfaced by the gaps list
Cheap, high-value, no new milestone needed: surface the CSV row cap, let the Mini-App page through
trades, expose archived categories in the UI, and decide on the rolling-message bot UX.

### 3. M5 — hardening, ops, release (post-MVP, currently parked)
Plan: `thoughts/shared/plans/2026-07-21-m5-hardening-ops-release.md`. Six phases: security pass
(initData/JWT property tests, `jti` revocation, authz meta-test, bandit/pnpm-audit) → observability
(re-instate D17: structlog + Sentry; `SENTRY_DSN` already exists in `Settings`, unwired) →
containers + Caddy → CI (must implement the D22 and i18n guards that only `make` runs today) →
backups + restore drill → smoke/demo, docs, `v1.0.0`.
**Start only when the deploy decision is actually made.**

### 4. v1.1 backlog (explicitly out of MVP)
Bank-statement import · recurring transactions · push/rate alerts · GPT/NL parsing · PDF/Excel
reports · P&L chart · outbox drainer · webhook bot.

---

## Running the stack

DB/Redis are the only containers: `make up` (Postgres **:5433**, Redis **:6380** — non-default host
ports). Then, each in its own terminal:

```bash
make dev-api      # :8000
make dev-bot      # polling
make dev-miniapp  # :3000
make tunnel       # cloudflared → copy the *.trycloudflare.com host into .env DOMAIN
```

The tunnel URL is **ephemeral** — after `make tunnel`, put the new host in `.env` `DOMAIN` and
**restart the bot** so `get_config()` picks it up. Bot: `@smart_accounting_hub_bot`.

Gates: `make check` (lint + format + typecheck + i18n-check + test). Without prettier churn:
`uv run ruff check && uv run mypy packages/core apps/api apps/bot && uv run pytest -q &&
uv run alembic check && make i18n-check`; Mini-App: `pnpm -F @smart-accounting/miniapp build`.
Regenerate TS types after any API change: `pnpm run types:gen` (needs the API running).

> **Environment note (2026-07-29):** Docker Desktop on the dev machine went down at the end of this
> session (`docker info` → EOF, `make up` → "unable to get image"). The 74 DB-backed tests error out
> until it is restarted — **this is environmental, not a code regression**: the tree is identical to
> the pushed commits, and ruff, mypy, i18n-check and all DB-free tests pass. Restart Docker Desktop,
> `make up`, and re-run `uv run pytest -q` to get back to 144 passed.

---

## Reference map

| What | Where |
|---|---|
| Product overview (what we're building, in RU) | `thoughts/shared/reference/2026-07-21-mvp-product-guide.md` |
| Milestones M1–M5 + decisions D1–D32 | `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` |
| M3 plan (built) | `thoughts/shared/plans/2026-07-21-m3-fx-transactions-weighted-avg.md` |
| M4 plan (built; D-M4-5 revised in-doc) | `thoughts/shared/plans/2026-07-21-m4-categories-charts-i18n.md` |
| M5 plan (parked) | `thoughts/shared/plans/2026-07-21-m5-hardening-ops-release.md` |
| Prior handoffs | `thoughts/shared/handoffs/2026-07-21-m2-*.md` |
