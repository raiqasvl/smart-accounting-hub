---
date: 2026-07-21
researcher: i.gorvier
git_commit: 1f62277
branch: main
repository: smart-accounting-hub
topic: "M5 — Hardening, ops, deploy, release (un-defer deployment)"
tags: [plan, m5, security, observability, docker, caddy, ci, backups, release, post-mvp]
status: in-progress
last_updated: 2026-07-21
last_updated_by: i.gorvier
decisions_confirmed: "CONFIRMED 2026-07-21 — D-M5-1..6 accepted; PLAN NOW / EXECUTE LATER (hold until a real deploy decision); Backblaze B2; re-instates deferred D17/D18/D19"
based_on: thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md §5 (M5, deferred)
grounded_in: "post-M2 codebase research (2026-07-21 sub-agent pass) — see Current State"
scope_note: "M5 was DEFERRED by the 2026-05-04 local-dev pivot. Planning it here per your 'up to M5' request; it is the post-MVP ship-it milestone — start only when we decide to go to production."
---

# M5 — Hardening, ops, deploy, release

## Overview

> **2026-09-26:** Phases 3 and 4 are executed by
> [2026-09-26-m5-phase3-4-droplet-deploy.md](2026-09-26-m5-phase3-4-droplet-deploy.md), with three
> deviations recorded there: a self-contained `deploy/compose.yml` instead of the prod-override
> pair, a shared `/srv/edge` Caddy (bvlk already holds 80/443 on the droplet), and images built in
> CI rather than on the server. Phases 1, 2, 5, 6 are unchanged and still pending.

**No new user features.** M5 turns the local-dev MVP (M1–M4) into a deployable v1.0: security pass,
observability back on (D17), containerization + reverse proxy, CI (D19), backups (D18), smoke/demo
automation, docs, and the release. This milestone **re-instates the three items the 2026-05-04 pivot
deferred** — it is explicitly **post-MVP** and should begin only once we choose to ship.

## Current State (post-M4, commit 1f62277)

Research pass (2026-07-21) — everything deployment-related is greenfield:

- **`ops/` has only `compose.yml`** (Postgres `:5433` + Redis `:6380`, with a `db-password` docker
  secret at `db/password.txt`). **No `compose.prod.yml`, no `Caddyfile`, no backup script.**
- **No `Dockerfile` anywhere.** No `.github/workflows/` — **CI does not exist** (the "grep-guard" that
  CLAUDE.md references is not yet implemented as a workflow).
- **`Makefile`** has local-dev targets only (`up/down/migrate/dev-api/dev-bot/dev-miniapp/tunnel/
  lint/format/typecheck/test/check`). No `smoke`/`demo`/`deploy`.
- **Observability**: `Settings.SENTRY_DSN: str | None = None` **exists** (`config.py`, tagged D17) but
  is **not in `.env.example` and not wired**. No `configure_observability`/structlog module. Bot calls
  a `configure_observability(...)` at boot (`__main__.py`) — confirm/expand its current body.
- **Auth surface to harden**: `auth/initdata.py::verify_init_data` (HMAC), `auth/jwt.py`
  (`JwtCodec.decode`), service-layer authz (`services/authz.resolve_role` + `auth/rbac`). JWT is
  `Authorization: Bearer` (no cookies). `respx`/`hypothesis` are already dev-deps.
- **DSN/host ports** are non-default (`5433`/`6380`) and the compose `up` echo string is stale (says
  5432/6379) — fix in the M5 ops cleanup.
- **Config**: `pyproject.toml` uv workspace (`apps/api`, `apps/bot`, `packages/core`); `pnpm` +
  `turbo` for `apps/miniapp` + `packages/api-types`; `output: "standalone"` already set in
  `next.config.mjs` (Next standalone build ready for a container).

## Desired End State (after M5)

One VM runs `caddy` + `postgres:16` + `redis:7` + `api` + `bot` + `miniapp` via
`docker compose -f ops/compose.yml -f ops/compose.prod.yml up -d`. HTTPS via Caddy auto-TLS at
`https://${DOMAIN}`; `/api/*` → api, everything else → the miniapp container. Sentry receives errors
with `request_id`/`book_id`/`user_id` breadcrumbs; JSON logs to stdout. CI runs the full gate + the
D22 grep-guard on every push. A nightly `pg_dump`+restic snapshot lands in B2 with a verified restore
drill. `make smoke`/`make demo` pass. `v1.0.0` tagged and deployed. Verification = §Definition of Done.

## What We're NOT Doing

- Multi-region / HA / k8s (single VM, docker compose). · Prometheus/Grafana/OTel (Sentry + JSON logs
  only). · A dedicated `apps/worker` (FX refresh + outbox drain stay asyncio tasks in the API
  lifespan). · Webhook bot (polling stays; webhook is a later 1-line switch). · Auth-gating `/docs`
  (stays public, D30).

## Implementation Approach

Six phases. Phases 1–2 (security + observability) touch code and can land while still local-dev; phases
3–6 (containers, CI, backups, release) are the actual go-live and should be gated on a real deploy
decision. Nothing here changes the domain contract.

---

## Phase 1: Security pass

### Changes Required
- **initData**: re-audit `verify_init_data` vs. current Telegram WebApp docs; add `hypothesis`
  property tests for HMAC tampering (flip any byte → `InitDataInvalid`), expiry (`max_age`), and
  field-injection. 
- **JWT**: assert `JwtCodec.decode` rejects expired, wrong-signature, `alg:none`, and tampered
  `book_id`/`role`; add a **`jti` revocation** check (D-M5-3: Redis set `revoked_jti`, TTL = token
  lifetime) with a `revoke(jti)` service used on logout/compromise.
- **Authz coverage meta-test**: since authz is service-layer (not a FastAPI dep), add a test that every
  book-scoped service method calls `resolve_role` + `require_permission` (introspect or a checklist
  test per service), and an API-level test that each non-`/auth`/non-`/health` route returns 401/403
  without a valid membership.
- **Deps audit**: `bandit` (add dev-dep) over `packages/core apps/api apps/bot` (0 highs);
  `pnpm audit --prod` (0 highs).
- **Headers**: Caddy sends `Strict-Transport-Security`, `X-Frame-Options: DENY` **except** allow
  Telegram to iframe the Mini-App — use `Content-Security-Policy: frame-ancestors https://web.telegram.org`
  (verify the exact ancestor set Telegram needs).

### Success Criteria
- [ ] `pytest` hypothesis suites for initData + JWT pass; revoked `jti` → 401.
- [ ] Authz meta-test green; `bandit`/`pnpm audit` clean of highs.

---

## Phase 2: Observability (re-instate D17)

### Changes Required
- `packages/core/.../observability.py`: `configure_observability(*, sentry_dsn, environment,
  log_level)` — structlog JSON processors to stdout + `sentry_sdk.init` (FastAPI + asyncio
  integrations) when DSN set. Bind `request_id` (from `RequestIdMiddleware`) into
  `structlog.contextvars`; enrich Sentry scope with `book_id`/`user_id` from claims.
- Wire into API lifespan and bot boot (`__main__.py` already calls a `configure_observability`; expand
  it). Add `SENTRY_DSN` + `ENVIRONMENT` to `.env.example`.

### Success Criteria
- [ ] A deliberate `RuntimeError` in a dev-only `/__obs-test__` route reaches Sentry with `request_id`.
- [ ] `docker logs api|bot` are JSON lines; local runs with no DSN degrade to plain stdlib logging.

---

## Phase 3: Containerization + reverse proxy

### Changes Required
- **`Dockerfile`** (root, Python, two CMDs via compose) — uv-based multi-stage per the M1 milestone
  sketch (`uv sync --frozen`); serves both `api` (uvicorn) and `bot` (`python -m smart_accounting_bot`).
- **`apps/miniapp/Dockerfile`** — Next.js **standalone** build (`output: "standalone"` already set),
  `node` runtime on `:3000`.
- **`ops/compose.prod.yml`** — adds `api`, `bot`, `miniapp`, `caddy`; overrides dev port exposure;
  `depends_on` healthchecks; `env_file: ../.env`. Keeps `db`/`redis` from base compose.
- **`ops/Caddyfile`** — `{$DOMAIN}` → `@api path /api/* /openapi.json /docs /healthz` `reverse_proxy
  api:8000`; default `reverse_proxy miniapp:3000`; `encode gzip`; security headers from Phase 1.
- Fix the stale `make up` echo (5433/6380); add `make deploy` per the runbook.

### Success Criteria
- [ ] `docker compose -f ops/compose.yml -f ops/compose.prod.yml up -d --build` → all services healthy
      within 90s locally; `curl -k https://localhost/healthz` ok; Mini-App loads through Caddy.

---

## Phase 4: CI (re-instate D19)

### Changes Required
- **`.github/workflows/ci.yml`** matrix: `ruff check` + `ruff format --check`; `mypy packages/core
  apps/api apps/bot`; `pytest` + `alembic upgrade head` + `alembic check` (postgres service container);
  the **D22 grep-guard** (`! grep -rE 'from smart_accounting\.(models|repositories)' apps/bot/src`);
  the **i18n Cyrillic guard** (from M4); `pnpm -r lint` (oxlint) + `pnpm -r typecheck` + `pnpm -r
  build`; an **api-types drift** check (`types:gen` against a spun-up API, `git diff --exit-code`).
- Optional `codeql.yml`.

### Success Criteria
- [ ] CI green on a no-op branch; the D22 guard fails a deliberately-violating branch.

---

## Phase 5: Backups (re-instate D18)

### Changes Required
- `ops/backup.sh` — `pg_dump -Fc` + `restic backup` to Backblaze B2; env `RESTIC_PASSWORD`, `B2_*`
  (add to `.env.example` as prod-only, gitignored). Schedule `0 4 * * *` UTC (systemd timer or a compose
  cron sidecar). `ops/restic-restore-runbook.md`.

### Success Criteria
- [ ] `backup.sh` produces a restic snapshot; **restore drill** on a second VM matches row counts.

---

## Phase 6: Smoke/demo + docs + release

### Changes Required
- `ops/smoke.sh` (compose up → poll `/healthz` → `/auth/telegram` with stubbed initData → `/me` →
  down); `ops/demo.sh` (seed 2 users + 1 book + 5 trades → print the weighted-avg). `make smoke`/`make
  demo`.
- Docs: `docs/architecture.md`, `docs/onboarding.md`, finalize `THIRD_PARTY_NOTICES.md`
  (AiogramBotTemplate MIT, FinWave). Refresh `README.md`.
- Release: tag `v1.0.0`, GitHub release + changelog, deploy from the tag, send the bot link to the
  first users with a feedback form.

### Success Criteria
- [ ] `make smoke`/`make demo` pass; deploy runbook executable by a second person; production URL serves
      the Mini-App over HTTPS; no `≥error` Sentry events in the first 24h.

---

## Testing Strategy
- **Security**: hypothesis (initData/JWT), authz meta-test, bandit, pnpm audit.
- **Ops**: `smoke.sh` in CI nightly; restore drill on a clean VM; a Caddy header check (curl `-I`).
- **Regression**: the full M1–M4 `make check` must stay green throughout.

## Decision Log (please confirm/override)
- **D-M5-1 (reverse proxy):** Caddy (D11) — single binary, auto-TLS. Keep unless we need an Nginx-only
  feature.
- **D-M5-2 (Mini-App serving):** its own `miniapp` container (Next standalone) behind Caddy; `/api/*`
  → api. (M1's Caddyfile left this split for later — resolved here.)
- **D-M5-3 (jti revocation):** Redis set (we already run Redis), TTL = token lifetime — multi-process
  safe, unlike an in-memory blocklist.
- **D-M5-4 (topology):** single VM, docker compose; no k8s/HA at v1.0.
- **D-M5-5 (CI guard authority):** CI implements the D22 bot-bypass grep-guard + the M4 i18n guard that
  CLAUDE.md assumes but no workflow yet enforces.
- **D-M5-6 (frame-ancestors):** relax `X-Frame-Options` to a CSP `frame-ancestors` that permits
  Telegram to embed the Mini-App (verify the exact host set); everything else `DENY`.

**CONFIRMED (2026-07-21):** M5 is **planned now but not executed** — it stays parked until we make an
actual production-deploy decision (M1–M4 are the shippable MVP). Backup backend is **Backblaze B2**.
D-M5-1..6 accepted as written. No open questions remain.

## Definition of Done (M5)
Automated: `make check` + `make smoke` + `make demo` green; CI green incl. D22 + i18n guards; bandit/
pnpm-audit clean; restore drill verified. Manual: production URL serves the Mini-App over HTTPS with
auto-TLS; first users complete onboarding unaided; no `≥error` Sentry events in 24h; a weekly B2
snapshot exists; `v1.0.0` tagged and deployed.

## References
- Milestone source (deferred body preserved): [2026-05-01-mvp-scope-and-milestones.md](thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md) §5, D11/D17/D18/D19/D20/D30
- Depends on M1–M4 shipped. Product overview: [2026-07-21-mvp-product-guide.md](thoughts/shared/reference/2026-07-21-mvp-product-guide.md)
