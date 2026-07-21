---
date: 2026-07-21
author: i.gorvier (GitHub raiqasvl)
repository: smart-accounting-hub
branch: main
topic: "Handoff — M2 shipped (all 7 phases committed); M3 is next"
status: complete
---

# Handoff — M2 shipped

M2 (books, invites, accounts, currencies + bot dialogs + Mini-App shell) is **code-complete and
committed on `main`**. Only manual real-phone verification remains. Next milestone: **M3** (the
headline weighted-average FX feature). Read this + the M2 plan for context.

## Hard rules (do not violate)
- **Commits: NO AI signatures.** Never add `Co-Authored-By: Claude …` or any AI trailer. Author is
  the user (`raiqasvl@users.noreply.github.com`). Commit ONLY when the user asks.
- **Preserve `thoughts/`** — plans/research/handoffs are the project's design history; keep + commit,
  never delete. (User was burned by this once.)

## Commit ledger (`main`)
- `1acfbe9` — M1 auth slice · `670fc95` — M2 plan doc.
- `9dde440` — **M2 backend** (Phases 1–5): RBAC matrix + `Money` wire type + service-layer authz;
  47-currency seed `0002` + currency service/API; book CRUD + `switch` (JWT re-mint); invites
  (create/accept/revoke) + state machine; accounts CRUD + FK-protected delete.
- `41c2f17` — **M2 bot** (Phase 6): aiogram-dialog create-book / create-account / join-invite /
  books-switcher; `/start invite_<token>` deep-link; `/books`, `/newbook`, `/newaccount`.
- `dd9604e` — **M2 Mini-App** (Phase 7): hand-rolled Tailwind shell — book picker, accounts,
  invites; TanStack Query over the M2 endpoints; api-types regenerated.
- `b9f8d25` — agent guide + `AGENTS.md` symlink + Claude Code settings (config, not product).

**Gates (all green):** Python **102 tests** + mypy(86 files) + ruff + `alembic check` + D22
grep-guard; Mini-App tsc + oxlint + `next build` + prettier.

## Key implementation notes (design history)
- **Authz lives in the SERVICE layer** — `services/authz.py::resolve_role(members, book_id, user_id)`
  (raises `NotAMember`) + `auth.rbac.require_permission`. NOT a FastAPI dependency. Bare
  `/accounts/{id}` routes load the account first, then resolve role for *its* book_id.
- **Book authz split (D-M2-2):** rename → `book.role.change` (admin+), archive → `book.delete` (owner).
- **Invite accept (D-M2-4):** unknown→404, expired→410, used+member→200 no-op, used+non-member→409
  already_used, fresh+member→409 already_member, fresh+non-member→join+mark. Owner role not invitable.
- **Money on the wire:** decimal string (D23). `AccountsRepo.insert` does a post-flush `refresh` so
  `opening_balance` carries the NUMERIC(20,8) scale, keeping create/list responses byte-identical.
- **Bot ↔ core:** `services/__init__` exports the M2 services; `TgChatService.context(chat_id)` →
  (user_id, active_book_id); `InviteService.preview(token)` (non-consuming, for the join prompt).
  Dialogs pull services from the per-update Dishka container (`middleware_data["dishka_container"]`).
- **Mini-App:** globals.css maps Telegram `--tg-theme-*` → CSS-var tokens; `components/ui.tsx` is the
  hand-rolled primitive set (cva); RBAC-gated UI (delete=owner, write=editor+, invites=owner/admin).

## Gotchas learned
- **aiogram-dialog getters** receive `dialog_manager` **by keyword**, not `manager` (positional) —
  wrong name → "Cannot get window data" TypeError at render.
- The command router + `Dialog` objects are **module-level singletons**; a given instance attaches to
  one Dispatcher at a time. Bot conftest has an autouse fixture that detaches `_parent_router` between
  tests so multiple dispatch-test fixtures can each build their own Dispatcher.
- API routers **must NOT** `from __future__ import annotations` (DishkaRoute needs concrete response
  types). Register every new repo/service in `packages/core/.../ioc.py` (REQUEST) + routers in
  `apps/api/.../main.py`.
- Working DIRECTLY on `main` (user removed all worktrees; no branches).
- `.claude/settings.json`, `CLAUDE.md`, `AGENTS.md` are agent config — committed separately (`b9f8d25`),
  not mixed into product commits.

## Conventions (M1/M2)
- Services return Pydantic DTOs; transactions begin/end in a service via `UoW` (`async with self._uow`
  commits on success). Bot never imports `models`/`repositories` (D22 grep-guard).
- Tests: compose DB + per-test **savepoint rollback**; API tests use the `client` + `login` fixtures
  in `apps/api/tests/conftest.py` (shared `conn` + a `db` session for seeding). mypy excludes `tests/`;
  pytest uses `--import-mode=importlib`.

## Running the local stack (real-phone verification)
- `make up` (Postgres **:5433**, Redis **:6380** — non-default host ports; migrations at
  `0002_seed_currencies` head).
- `make dev-api` (:8000) · `make dev-bot` (polling) · `make dev-miniapp` (:3000) · `make tunnel`
  (cloudflared → set `.env` DOMAIN to the printed `*.trycloudflare.com` host, **restart the bot** so
  `get_config` picks it up). NOTE: the tunnel URL is **ephemeral** — a fresh one each `make tunnel`.
- Checks without prettier churn: `uv run ruff check … && uv run mypy packages/core apps/api apps/bot
  && uv run pytest -q && uv run alembic check`; Mini-App: `pnpm -F @smart-accounting/miniapp build`.

## What's next — M3 (headline)
Weighted-average exchange-rate over stored FX transactions: `fx_transactions` service/repo, the
`SUM(amount_base)/SUM(amount_quote)` report, `/trade` + `/avg` bot flows (`RecordTradeDialog`),
`big.js` in the Mini-App, FX rate provider (Frankfurter). Write the plan to
`thoughts/shared/plans/YYYY-MM-DD-m3-*.md` first (per workflow rules), then build bottom-up.
