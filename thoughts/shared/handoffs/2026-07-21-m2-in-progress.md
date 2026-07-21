---
date: 2026-07-21
author: i.gorvier (GitHub raiqasvl)
repository: smart-accounting-hub
branch: main
topic: "Handoff — M2 in progress (Phases 1–2 done), pre-compaction state snapshot"
status: active
---

# Handoff — M2 in progress

Resume point for continuing M2 after a session compaction. Read this + the M2 plan, then pick up
at **Phase 3**.

## Hard rules (do not violate)
- **Commits: NO AI signatures.** Never add `Co-Authored-By: Claude …` or any AI trailer. Author is
  the user (`raiqasvl@users.noreply.github.com`). Commit ONLY when the user asks.
- **Preserve `thoughts/`** — plans/research/handoffs are the project's design history; keep + commit,
  never delete. (User was burned by this once.)

## Where we are
- **M1 shipped**: committed on `main` (`1acfbe9` feat: M1 …) + `670fc95` (docs: M2 plan). Bot live:
  **@smart_accounting_hub_bot**.
- **M2 in progress**, uncommitted working changes on `main`:
  - **Phase 1 done** — `auth/rbac.py` PERMISSIONS matrix + `has_permission`/`require_permission`;
    `schemas/money.py` `Money` (decimal-string wire type); new errors (Forbidden/NotFound/NotAMember/
    LastOwner/Invite*/AlreadyMember/AccountInUse/CurrencyUnknown/CurrencyExists); new DTOs
    (book Create/Patch, account, currency, invite, member); authz enforced in the SERVICE layer
    (`services/authz.py::resolve_role` + `require_permission`), NOT a FastAPI dep.
  - **Phase 2 done** — `data/currencies_seed.py` (47 system currencies) + `0002_seed_currencies`
    (idempotent via existence check; NULL book_id can't use the unique constraint); `CurrenciesRepo`,
    `CurrencyService`, `routers/currencies.py` (`GET /api/v1/currencies?book_id=`,
    `POST /api/v1/books/{id}/currencies`); registered in ioc + main.
  - **Phase 3 done** — `BooksRepo.update` + `default_language` on `insert`;
    `TgChatsRepo.set_active_book_for_user` (bulk repoint); `services/book_service.py` (create /
    list_for_user / get / update / switch); `routers/books.py` (`POST|GET /books`,
    `GET|PATCH /books/{id}`, `POST /books/{id}/switch` → `TokenOut`); registered in ioc + main.
    Authz split D-M2-2: rename → `book.role.change` (admin+), archive → `book.delete` (owner).
    Test harness refactored: `conn` fixture shared by the app `client` + a new `db` session so tests
    can seed non-owner memberships / chats before invites exist.
  - **Phase 4 done** — `BookInvitesRepo` (insert/get/get_by_token/list_pending/mark_used/delete);
    `BookMembersRepo.insert` grew `accepted_at`; `services/invite_service.py` (create/list_pending/
    revoke/accept). Accept state machine (D-M2-4): unknown→404, expired→410, used+member→200 no-op,
    used+non-member→409 already_used, fresh+member→409 already_member, fresh+non-member→join+mark.
    `routers/invites.py` (`POST|GET /books/{id}/invites`, `DELETE …/{invite_id}`,
    `POST /invites/{token}/accept`). Owner role can't be invited (403). deep_link uses BOT_USERNAME.
  - **Phase 5 done** — `AccountsRepo` (insert w/ post-flush `refresh` so opening_balance carries the
    NUMERIC(20,8) scale; list_for_book w/ archived filter; get/update/delete; `has_transactions`
    over both fx legs); `services/account_service.py` (create validates currency via
    `code_visible`→CurrencyUnknown 422; list; patch=account.write; delete=owner-only + AccountInUse
    409 when referenced). `routers/accounts.py` (`POST|GET /books/{id}/accounts?archived=`,
    `PATCH|DELETE /accounts/{id}` — bare routes load book_id from the account, then authz).
- **Gates: all green** — ruff + format + mypy (80 files), `alembic check` clean, **96 tests pass**,
  D22 grep-guard clean, DB residue-free. **M2 backend (Phases 1–5) is complete.**

## What's next (M2 Phases 6–7 — user-facing, manual gates)
Plan: `thoughts/shared/plans/2026-07-21-m2-books-invites-accounts.md` (ready-for-dev, decisions
confirmed: full M2 incl. bot dialogs; hand-rolled Tailwind UI).
- **Phase 6** — Bot aiogram-dialog flows + rolling message UX (manual gate).
- **Phase 7** — Mini-App Tailwind + hand-rolled shadcn shell, book picker, accounts, invites
  (real-phone gate).

## Conventions to keep (M1/M2)
- Services return Pydantic DTOs; transactions begin/end in a service via `UoW` (`async with self._uow`
  commits on success). Bot never imports `models`/`repositories` (D22 grep-guard).
- API routers use `DishkaRoute` + `FromDishka`, and **must NOT** `from __future__ import annotations`
  (concrete response types), and call `extract_claims(request, jwt)` for the auth gate.
- Tests: compose DB + per-test **savepoint rollback**; API tests use the `client` + `login` fixtures
  in `apps/api/tests/conftest.py`. mypy excludes `tests/`; pytest uses `--import-mode=importlib`.
- Register every new repo/service in `packages/core/.../ioc.py` (REQUEST scope) and new routers in
  `apps/api/.../main.py`.

## Running services (local dev) & how to verify
- DB/Redis: `make up` (Postgres **:5433**, Redis **:6380** — non-default host ports, in .env/compose).
  Migrations at `0002_seed_currencies` head.
- Run: `make dev-api` (:8000), `make dev-bot` (polling), `make dev-miniapp` (:3000), `make tunnel`
  (cloudflared → set `.env` DOMAIN to the tunnel host, restart the bot). NOTE: tunnel URL is
  ephemeral; the last one was `incorporate-summaries-descriptions-examined.trycloudflare.com`.
- Checks: `make check` (or `uv run ruff check`, `uv run mypy packages/core apps/api apps/bot`,
  `uv run pytest -q`, `uv run alembic check`). `make lint`/`check` is fully green now.

## Gotchas learned
- Working DIRECTLY on `main` (user removed all worktrees; no branches).
- `pnpm format` (prettier) reformats vendored `.agents/`, config JSON/YAML — revert that churn before
  committing (not part of our work).
- `make check` runs `pnpm format` which re-churns those files; use the individual `uv run …` checks to
  avoid it when you don't want the churn.
