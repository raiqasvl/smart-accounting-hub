---
date: 2026-07-21
researcher: i.gorvier
git_commit: 1f62277
branch: main
repository: smart-accounting-hub
topic: "M4 — Categories, transfers, charts, EN/RU, CSV (round out to v1)"
tags: [plan, m4, categories, ltree, transfers, charts, recharts, i18n, fluent, csv, aiogram-dialog, miniapp]
status: ready-for-dev
last_updated: 2026-07-21
last_updated_by: i.gorvier
decisions_confirmed: "CONFIRMED 2026-07-21 — D-M4-1..7 accepted; ltree id-labels; Mini-App i18n stays strings.ts (drop unused @fluent); CSV=tx.read; P&L→v1.1; locale auto-detect (no /lang)"
based_on: thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md §4 (M4)
grounded_in: "post-M2 codebase research (2026-07-21 sub-agent pass) — see Current State"
depends_on: thoughts/shared/plans/2026-07-21-m3-fx-transactions-weighted-avg.md
---

# M4 — Categories, transfers, charts, EN/RU, CSV

## Overview

M4 makes the product feel like a real v1: hierarchical **categories** (`ltree` + cascade reparent,
D14), **two-leg transactions** (internal transfers + FX conversions, deferred from M3), Mini-App
**charts** (account-balance line, P&L-by-currency bar — the latter a stretch), a **full EN/RU** pass
across bot + Mini-App (with a CI guard against hardcoded Russian), and **CSV export**.

M4 ends with: a category tree you can build and reparent (descendants follow), transactions filed
under categories, an internal transfer that moves money between two accounts as one linked pair,
balance charts, both languages complete, and a CSV download.

## Current State (post-M2 + assumes M3 merged, commit 1f62277)

Research pass (2026-07-21) ground truth:

- **Category schema already exists in `0001`.** `models/category.py::Category` = `{id, book_id,
  parents_tree: LtreeType (NOT NULL), kind: SmallInteger (0=income,1=expense,2=both), name, description,
  archived}`, with the GIST index `ix_categories_book_id_parents_tree` on `(book_id, parents_tree)`.
  The `ltree`, `btree_gist`, `pgcrypto` extensions are **all created in `0001`**. So **M4 needs no
  migration for the categories schema** — only service/repo/API/UI. `models/fields.py` exposes
  `ltree_path = Annotated[Ltree, mapped_column(LtreeType)]` (`sqlalchemy_utils`).
- **`linked_transaction_id` (self-FK) + `transaction_kind{internal_transfer,fx_conversion}` already
  exist** on `fx_transactions` — the two-leg flows need no schema change, only service logic.
- **No `categories` repo / service / router / dialog yet.** RBAC already grants `category.write`
  (OWNER/ADMIN/EDITOR); `tx.read`/`tx.write` cover transfers and export.
- **Bot i18n** = aiogram-i18n Fluent, catalogues `packages/core/.../i18n/{en,ru}/main.ftl`
  (hand-maintained, section-commented). `mypy` already ignores `aiogram_i18n.*`/`fluent.*`.
- **Mini-App i18n** = **hand-rolled `lib/strings.ts`** (EN/RU `Record<string,string>` dicts +
  `makeTranslate`), **not Fluent** — even though `@fluent/bundle`/`@fluent/react` are installed but
  unused. Per the "code is right, fix the doc" rule this deviates from D13; see D-M4-4.
- **Mini-App charts**: Recharts `^2.13` installed. Tab system is `useState` in `app-shell.tsx`; UI kit
  in `components/ui.tsx` (no `Tabs` primitive; there is a `Drawer`). Money via `big.js` (added in M3).
- **CSV**: nothing yet. FastAPI can stream via `StreamingResponse`.

## Desired End State

`make check` green. A category tree builds/renames/moves with `ltree` cascade integrity; transactions
carry a `category_id`; an internal transfer creates two linked `internal_transfer` rows; the Mini-App
renders a balance chart and a category tree; **EN and RU key sets are identical** (enforced) and a CI
grep blocks hardcoded Russian; `GET …/transactions/export.csv` streams a stable-column file. Verification
= §Definition of Done.

## What We're NOT Doing (M4 out of scope → v1.1)

- **Bank/CSV import** (reading external files), recurring transactions, push/alerts, GPT/NL parsing,
  PDF/Excel — all v1.1.
- **P&L-by-currency chart** is a **stretch** (D-M4-7); ship the account-balance chart first, defer P&L
  if it risks the milestone.
- **Category-scoped reports** (per-category weighted-avg / totals endpoints) — nice-to-have; only the
  tree + assignment + a simple per-category total in the UI are in scope.

## Implementation Approach

Six phases, bottom-up. Conventions unchanged (services own tx via UoW; typed errors → D24/Fluent; Money
= string). Two M4-specific conventions:

- **ltree labels = numeric category id (D-M4-1):** insert the row, `flush` to get `id`, then set
  `parents_tree`: root → `Ltree(str(id))`, child → `parent.parents_tree + Ltree(str(id))`. `move`
  (D14) recomputes every descendant's path in one tx via a `subpath`/`text2ltree` UPDATE over
  `parents_tree <@ old_path`.
- **Movements are single rows (D-M4-5, revised at build time):** a transfer/conversion is **ONE
  `fx_transactions` row touching both accounts** (`quote_account_id` = money out, `base_account_id` =
  money in). See the Decision Log for why the original two-leg design was dropped.

---

## Phase 1: Categories — service + repo + API (ltree)

### Changes Required

#### 1. `schemas/category.py` + errors
`CategoryOut{id, book_id, parents_tree: str, depth: int, kind, name, description, archived}`
(`from_attributes`; serialize `parents_tree` via `str(ltree)`; `depth` = label count).
`CategoryCreateIn{parent_id: int | None, kind: int, name, description: str | None = None}`.
`CategoryPatchIn{name?, description?, parent_id?: int | None (move), archived?}`. New errors:
`CategoryNotFound`(404), `CategoryHasChildren`(409, `category_has_children`),
`CategoryInUse`(409, `category_in_use`), `InvalidCategoryParent`(422, cross-book/self/descendant parent).

#### 2. `repositories/categories.py`
`insert(book_id, kind, name, description) -> Category` (add+flush, caller sets path), `set_path(id,
ltree)`, `get(id)`, `list_for_book(book_id, include_archived) -> list[Category]` (ORDER BY
`parents_tree`), `children_count(id)`, `has_transactions(id)` (count `fx_transactions.category_id`),
`move_subtree(old_path, new_path)` — the D14 cascade:
`UPDATE categories SET parents_tree = text2ltree(:new || subpath(parents_tree, nlabel(:old)))
WHERE parents_tree <@ :old` (one statement).

#### 3. `services/category_service.py`
Ctor `(uow, CategoriesRepo, BookMembersRepo)`. `create` (`category.write`; if `parent_id`, load+assert
same book, build child path), `list`, `rename`/`patch`, `move` (validate new parent in-book and not a
descendant of the node → `InvalidCategoryParent`; recompute node path then `move_subtree` for
descendants), `archive`/`delete` (`delete` refuses if `children_count>0` → `CategoryHasChildren` or
`has_transactions` → `CategoryInUse`; offer archive). Register repo+service in `ioc.py`, export DTOs.

#### 4. API `routers/categories.py`
`POST /books/{book_id}/categories` · `GET /books/{book_id}/categories?include_archived=` ·
`PATCH /categories/{id}` (rename/move/archive, bare-id) · `DELETE /categories/{id}`. Register in `main.py`.

### Success Criteria — Automated
- [ ] Create root "Food" then child "Lunch" → `Lunch.parents_tree` = `<food_id>.<lunch_id>`.
- [ ] Rename "Food"→"Daily" keeps paths; **move** "Food" under "Daily2" → every descendant path is
      rewritten in one tx (`Lunch` now under the new prefix).
- [ ] Delete blocked by child → 409; delete blocked by a referencing tx (stub `has_transactions=True`)
      → 409; archive always allowed.
- [ ] Cross-book/self/descendant parent → 422. `make check` (Python) green.

---

## Phase 2: Two-leg transactions — internal transfer + FX conversion

### Changes Required

#### 1. `services/transaction_service.py` (extend the M3 service)
- `record_transfer(book_id, user_id, from_account_id, to_account_id, amount: Decimal, occurred_at,
  note) -> tuple[TransactionOut, TransactionOut]` — `tx.write`; both accounts in-book + **same
  currency** (else `AccountCurrencyMismatch`); insert two `kind="internal_transfer"` rows (out leg
  `direction="sell"`, in leg `"buy"`, `rate=1`, `amount_base=amount`), then set each row's
  `linked_transaction_id` to the other (second pass) — all in one `async with self._uow`.
- `record_fx_conversion(...)` — like transfer but two **different** currencies, user-supplied `rate`,
  `kind="fx_conversion"`; leg amounts are `amount_quote` and `amount_quote·rate`.
- `archive`/`patch` cascade to `linked_transaction_id` when set.

#### 2. Schemas + API
`TransferCreateIn{from_account_id, to_account_id, amount: Money, occurred_at?, note?}`;
`FxConversionCreateIn{from_account_id, to_account_id, amount_quote: Money, rate: Money, occurred_at?,
note?}`. `routers/transfers.py`: `POST /books/{book_id}/transfers`, `POST /books/{book_id}/fx-conversions`
→ return the linked pair. Register in `main.py`.

### Success Criteria — Automated
- [ ] Transfer creates exactly two rows, mutually `linked_transaction_id`, same currency, net-zero across
      the pair; archiving one archives both.
- [ ] FX conversion: two legs, distinct currencies, `amount_base` consistent with `rate`.
- [ ] Mismatched-currency transfer → 422; cross-book account → 422; VIEWER → 403.

---

## Phase 3: Bot — category picker + transfer dialog + category step

### Changes Required

- **Reusable category picker widget** (`dialogs/widgets/category_picker.py`): paginated
  `ScrollingGroup`/`Select` over `CategoryService.list` (≤8 per page), indented by `depth`. Used by the
  trade dialog and the transfer dialog.
- **`RecordTrade` gets an optional `category` step** (skippable) before `confirm`, storing
  `category_id` into `dialog_data`; `TransactionService.record` accepts it.
- **`InternalTransferDialog`** (`dialogs/internal_transfer.py`): `FromAccount → ToAccount → Amount →
  Note → Confirm` → `record_transfer`. States in `states.py`; register in `all_dialogs()`; `/transfer`
  command in `handlers/commands.py` (+ `set_my_commands`).
- **i18n**: `# --- categories ---` / `# --- transfer ---` sections in both `i18n/{en,ru}/main.ftl`.

### Success Criteria
- [ ] Dialog tests: transfer persists two linked rows; trade-with-category sets `category_id`. D22 clean.
- [ ] Manual: build a category in-app, file a trade under it via the bot, run a transfer between two
      accounts; rolling message stays coherent.

---

## Phase 4: Mini-App — categories UI, category assignment, charts

### Changes Required

#### 1. Types/client/hooks
Regenerate `api.d.ts`; add `CategoryOut/CategoryCreateIn/TransferCreateIn` aliases. Client:
`fetchCategories/createCategory/patchCategory/deleteCategory`, `createTransfer`,
`fetchAccountBalanceSeries`. Hooks keyed `['categories', bookId]`, `['balance', bookId, accountId, range]`.

#### 2. Categories settings page
New `components/categories-tab.tsx` (or a Settings subsection): recursive `<TreeNode>` (hand-rolled;
no shadcn-extension) rendering `list_for_book` ordered by `parents_tree`, indent by `depth`; create
(pick parent) / rename / move (parent `Select`) / archive via the `ui.tsx` kit + `Drawer`. Add
`tab-categories` (EN/RU) to `strings.ts`.

#### 3. Category assignment
Add a category `Select` to the Trades create `Drawer` (from M3).

#### 4. Charts
- `ReportService.account_balance_series(book_id, user_id, account_id, from, to) -> [{at, balance}]`
  (opening_balance + running signed sum of legs touching the account) + `GET
  …/reports/account-balance`. `components/charts/account-balance-chart.tsx` — Recharts `LineChart`,
  theme colors (`var(--accent)`).
- **Stretch** `PnLByCurrencyChart` (bar) — build only if schedule allows (D-M4-7).

### Success Criteria
- [ ] `typecheck && lint && build` pass. Manual: tree renders + reparents; a trade shows its category;
      the balance chart draws a sensible curve for an account with ≥5 legs.

---

## Phase 5: Full EN/RU i18n pass + CI guard

### Changes Required

- **Bot**: complete every `trade-*/avg-*/category-*/transfer-*` key in **both** `.ftl` files; add
  `pytest packages/core/tests/test_fluent_keys.py` asserting `en` and `ru` key sets are identical.
- **Mini-App**: complete the `RU` dict in `strings.ts` for all M3/M4 keys; add a small vitest asserting
  `Object.keys(EN)` ⊇ `Object.keys(RU)` (key parity). **Decision D-M4-4: keep hand-rolled `strings.ts`**
  (do not adopt `@fluent` in the app for MVP) — optionally drop the unused `@fluent/*` deps.
- **CI grep guard** (wired for real in M5, but the check is authored here): shell step
  `! grep -rE 'Const\("[А-Яа-я]|>[^<]*[А-Яа-я]' apps/bot/src apps/miniapp/src` to forbid hardcoded
  Cyrillic outside i18n catalogues. Add as a `make i18n-check` target now.
- **Bot locale**: **auto-detect only** (from `language_code` via `TelegramLocaleManager`) — **no
  `/lang` command in MVP** (D-M4-8). A manual override can be a v1.1 nicety.

### Success Criteria
- [ ] `test_fluent_keys` + the strings-parity vitest pass; `make i18n-check` green (no hardcoded Cyrillic).
- [ ] Manual: bot renders fully in RU for a `ru` user; Mini-App switches by `me.user.language`.

---

## Phase 6: CSV export

### Changes Required

- API `GET /books/{book_id}/transactions/export.csv?from=&to=` → `StreamingResponse` (text/csv), stable
  column order (all `fx_transactions` fields + resolved account/category names), `tx.read` (D-M4-6).
  Money rendered as the same decimal string (D23).
- Mini-App: a "Export CSV" button on the Trades tab (authenticated fetch → `Blob` download).

### Success Criteria
- [ ] `pytest`: export yields a valid CSV with a fixed header; date filter applied; opens in Excel/Sheets.
- [ ] Manual: button downloads the file with the current filters.

---

## Testing Strategy

- **Unit**: ltree path building + `move_subtree` cascade (property-ish over a few tree shapes),
  transfer net-zero / linkage, balance-series math, CSV row shaping, i18n key parity.
- **Integration (compose PG + savepoint)**: categories CRUD + cascade + delete-guards; transfers/
  conversions two-row + linkage; balance-series endpoint; CSV endpoint; RBAC denials.
- **Bot**: dialog tests for transfer + category-in-trade (extend M3 harness).
- **Mini-App**: `build` + `typecheck`; vitest for the tree render + strings parity.

## Decision Log (please confirm/override)

- **D-M4-1 (ltree labels):** numeric category id as the label (`insert → flush → set path`). Simple,
  collision-free, rename-stable (labels never change; only names do).
- **D-M4-2 (delete guard):** delete refused if children or referencing transactions exist → archive
  (D29). Archive always allowed.
- **D-M4-3 (move cascade):** D14 — one-statement `parents_tree` rewrite over `<@ old_path`, same tx.
- **D-M4-4 (Mini-App i18n) — CONFIRMED:** **keep hand-rolled `strings.ts`** (EN/RU dicts); do NOT
  migrate the app to Fluent for MVP (deviates from D13, but matches shipped code and is simpler). **Remove
  the unused `@fluent/bundle`/`@fluent/react` deps** to avoid confusion.
- **D-M4-5 (account-to-account movements) — REVISED DURING BUILD (2026-07-28):** a transfer or FX
  conversion is **ONE `fx_transactions` row touching both accounts** (`quote_account_id` = money out,
  `base_account_id` = money in), *not* two linked rows as originally planned.
  *Why:* the schema already carries both account FKs, and a mirror leg would corrupt the headline —
  the "buy" leg of a USD→EUR conversion reads as *"bought USD"* and would pollute the buy-USD
  weighted average. One economic event = one row: simpler and more correct.
  `linked_transaction_id` stays unused (reserved for v1.1 splits/refunds).
  *Consequence:* `internal_transfer` rows carry a synthetic `rate = 1`, so the weighted-average query
  **excludes `kind = internal_transfer`** (no FX happened); `fx_conversion` rows are real trades and
  ARE counted. Both are covered by tests in `apps/api/tests/test_transfers.py`.
- **D-M4-6 (CSV permission) — CONFIRMED:** export gated by `tx.read` (read-only data → viewers may
  export), deviating from the milestone's "Editor+". Simpler and correct for a read-only op.
- **D-M4-7 (P&L chart) — CONFIRMED:** account-balance chart is in scope; **P&L-by-currency is deferred
  to v1.1** (do not build in M4).
- **D-M4-8 (bot locale) — CONFIRMED:** auto-detect from `language_code` only; **no `/lang`** in MVP.

No open questions remain.

## Definition of Done (M4)

Automated: `make check` green · categories/transfers/CSV integration suites pass · `test_fluent_keys` +
strings-parity + `make i18n-check` pass · `types:gen` reflects the contract. Manual: build "Food →
Lunch/Groceries", assign a trade to "Lunch", rename "Food"→"Daily" (descendant path follows) · run an
internal transfer (two linked legs) · balance chart renders · bot + Mini-App fully in RU for a `ru`
user · CSV export opens cleanly in a spreadsheet.

## References
- Milestone source: [2026-05-01-mvp-scope-and-milestones.md](thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md) §4 (M4), D13/D14/D23/D29
- Depends on: [2026-07-21-m3-fx-transactions-weighted-avg.md](thoughts/shared/plans/2026-07-21-m3-fx-transactions-weighted-avg.md)
- Patterns to mirror: `services/account_service.py`, `apps/bot/.../dialogs/create_account.py`,
  `apps/miniapp/src/components/{app-shell,accounts-tab}.tsx`, `lib/strings.ts`, `i18n/{en,ru}/main.ftl`
