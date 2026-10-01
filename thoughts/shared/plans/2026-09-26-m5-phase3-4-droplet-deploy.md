---
date: 2026-09-26
researcher: i.gorvier
branch: claude/telegram-bot-deploy-prep-bd7afd
repository: smart-accounting-hub
topic: "M5 Phase 3+4 — containers, shared edge proxy, CI/CD onto the existing droplet"
tags: [plan, m5, deploy, docker, caddy, ci, ghcr, droplet]
status: ready-for-dev
last_updated: 2026-09-26
last_updated_by: i.gorvier
based_on: thoughts/shared/plans/2026-07-21-m5-hardening-ops-release.md (Phases 3 and 4)
decisions_confirmed: "CONFIRMED 2026-09-26 — deploy the bvlk way (GHCR + SSH + compose); ship first, harden after; existing droplet shared with bvlk; secrets as a file on the droplet; new prod bot. AMENDED 2026-10-01 — no separate prod bot: production reuses the dev bot (stop the server's poller before `make dev-bot`); docs/bot-setup.md Step 9 is the current text. Domain: fxlog.app"
---

# M5 Phase 3+4 — Droplet Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make smart-accounting-hub deployable to the existing DigitalOcean droplet: two images published to GHCR by CI, a self-contained compose stack on the server, and a shared Caddy that serves both this project and bvlk.

**Architecture:** GitHub Actions verifies, builds `smart-accounting-app` (api + bot + migrate, one Python image) and `smart-accounting-miniapp` (Next standalone), pushes both to GHCR, then over SSH pulls them on the droplet, runs `alembic upgrade head` as a one-shot, and restarts the stack. Ingress on 80/443 moves out of bvlk's stack into a shared `/srv/edge` Caddy; each project installs one site file into `/srv/edge/sites/` and reloads.

**Tech Stack:** Docker (buildx, compose), uv 0.7.17, Python 3.12.3, Node 20.18.0 + pnpm 9.12.0, Next.js 15 standalone, Caddy 2, Postgres 16, Redis 7, GitHub Actions, GHCR.

**Spec:** the Design section below, which amends Phases 3 and 4 of [2026-07-21-m5-hardening-ops-release.md](2026-07-21-m5-hardening-ops-release.md). Phases 1, 2, 5, 6 of that plan are unchanged and come after this one.

## Global Constraints

- Runtime versions: Python `3.12.3`, uv `0.7.17`, Node `20.18.0`, pnpm `9.12.0` (from `.tool-versions`); images `postgres:16`, `redis:7-alpine`, `caddy:2-alpine`.
- Image names: `ghcr.io/raiqasvl/smart-accounting-app`, `ghcr.io/raiqasvl/smart-accounting-miniapp`; every build pushes `:latest` and `:<commit sha>`.
- Server paths: stack in `/srv/smart-accounting/`, shared proxy in `/srv/edge/`, site files in `/srv/edge/sites/`.
- Shared docker network `edge` (external). Aliases on it carry the project prefix: `sa-api`, `sa-miniapp`. Postgres and Redis are never attached to `edge`.
- Nothing in `deploy/compose.yml` publishes a host port. Only the edge Caddy binds 80/443.
- The bot runs exactly one replica; uvicorn runs one worker (`smart_accounting_api.main:run`).
- Secrets (`BOT_TOKEN`, `JWT_SECRET`, DB password) live only in `/srv/smart-accounting/.env` (chmod 600) and `/srv/smart-accounting/db/password.txt`. Never in the repo, never in GitHub secrets. The repository is public, so CI logs are public.
- Commits are authored solely as the user; **no `Co-Authored-By` trailer** (project memory rule).
- `make check` stays green after every task.

---

## Design

### Findings that shaped it

| Finding | Source | Consequence |
|---|---|---|
| Every `Settings` field has a default; `BOT_TOKEN`, `JWT_SECRET`, `DOMAIN` default to `""` | `config.py:24-33` | A missing `.env` boots production silently, and an empty `JWT_SECRET` signs forgeable tokens → fail-fast validation before first deploy |
| bvlk runs on the same droplet; its Caddy holds 80/443 | server inventory 2026-09-26 | A second Caddy cannot bind → shared edge proxy |
| bvlk's `deploy.yml` scp's its whole `Caddyfile` on every deploy | bvlk `.github/workflows/deploy.yml` | Adding our site to bvlk's Caddyfile would be erased by bvlk's next deploy → one file per project in `sites/` |
| Health endpoints are bare paths outside `/api/v1` | `health.py:14,19`, `main.py:100` | Caddy routes an explicit path list, not a prefix |
| No CORS middleware | `main.py:97-116` | API and Mini-App must share one origin |
| Mini-App reads zero env vars; all calls are relative `/api/v1/*` | `api-client.ts`, grep | The Mini-App image is domain-independent |
| `next.config.mjs` rewrite destination is the literal `http://127.0.0.1:8000` | `next.config.mjs:14` | Inside the container that is the Mini-App itself → make it build-time configurable, bake `http://sa-api:8000` |
| Migration `0001` runs `CREATE EXTENSION ltree, pgcrypto, btree_gist`; `0002` seeds currencies | `migrations/versions/` | Self-hosted Postgres (superuser); `upgrade head` is data as well as schema; run once before `up`, never from an entrypoint |
| Bot is long-poll, single replica; calls `set_my_commands` at boot | `__main__.py:30-31`, `apps/bot/pyproject.toml:7` | No port, one replica, `restart: unless-stopped` |
| Bot reads `.ftl` catalogues from the installed package | `i18n.py:17` | The image must ship them inside site-packages |
| `.dockerignore` patterns are root-anchored (`node_modules`, `.next`) | `.dockerignore` | Host `apps/miniapp/node_modules` (macOS binaries) would enter the build context → use `**/` patterns |
| Droplet: 3.8 GiB RAM (3.2 available), no swap, UFW inactive, compose installed | inventory | Capacity is fine; swap and Cloud Firewall are runbook items |

### Deviations from the M5 plan

1. **Self-contained `deploy/compose.yml`** instead of `ops/compose.yml` + `ops/compose.prod.yml`. The dev compose publishes Postgres (5433) and Redis (6380); layering a prod override on it leaves the database one forgotten `-f` away from the internet. The prod file has no `ports` at all, and the droplet receives two files, not the repository.
2. **Shared `/srv/edge` Caddy** instead of a Caddy inside our stack (D-M5-1 still holds: it is Caddy). Forced by bvlk occupying 80/443.
3. **Images built in CI, pulled on the droplet** (the bvlk pattern) instead of `up --build` on the server. The droplet never builds, so it needs no build toolchain and no headroom for `next build`.

### Topology

```
                         :80 :443
                            │
              /srv/edge ┌───▼───┐  import sites/*.caddy
                        │ caddy │
                        └┬──┬──┬┘
             bvlk.caddy  │  │  │  smart-accounting.caddy
          ┌──────────────┘  │  └────────────────┐
          ▼                 ▼                   ▼
      bvlk-web:3000     sa-api:8000        sa-miniapp:3000
                            │   (edge network ▲ above this line)
       ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┼─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                            │   (backend network ▼ below)
                  ┌─────────┼─────────┐
                ┌─▼─┐   ┌───▼──┐   ┌──▼──┐
                │db │   │redis │   │ bot │  outbound only
                └─▲─┘   └──────┘   └─────┘
                  └── migrate (one-shot)
```

Caddy routing for our site: `/api/v1/*`, `/healthz`, `/readyz`, `/docs`, `/redoc`, `/openapi.json` → `sa-api:8000`; everything else → `sa-miniapp:3000`. The docs surface stays public (D30).

### Deploy sequence (per push to `main`, once enabled)

```
verify (ci.yml) ──► build app ─────┐
                └─► build miniapp ─┴─► deploy:
                                        1. render site file from vars.SITE_ADDRESS
                                        2. scp compose.yml → /srv/smart-accounting/
                                           scp site file  → /tmp/
                                        3. docker login ghcr.io (per-run token) · compose pull · logout
                                        4. compose run --rm migrate
                                        5. compose up -d --remove-orphans
                                        6. install site file, caddy reload; restore previous on failure
                                        7. image prune
                                        8. curl https://$SITE_ADDRESS/readyz and / until 200
```

Build and deploy are gated on the repository variable `DEPLOY_ENABLED == 'true'`; until the droplet is prepared, a push to `main` runs CI only.

### Out of scope here (runbook items, each needs its own go-ahead)

Moving bvlk onto the edge proxy (touches a live site and another repository), adding swap, creating the deploy user, buying the domain, BotFather for the prod bot, the first deploy. All are written up in `docs/deploy.md` (Task 7). Phases 1, 2, 5 and 6 of M5 (security pass, Sentry/structlog, restic→B2 backups, smoke/demo) follow this plan.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `packages/core/src/smart_accounting/config.py` | modify | Fail-fast validation of production secrets |
| `packages/core/tests/test_config.py` | create | Tests for that validation |
| `apps/miniapp/next.config.mjs` | modify | Rewrite destination from `API_PROXY_TARGET` (build time) |
| `turbo.json` | modify | `globalEnv`: drop dead `NEXT_PUBLIC_*`, add `API_PROXY_TARGET` (changes build output → must key the cache) |
| `.env.example` | modify | Drop the dead Mini-App section |
| `Makefile` | modify | Fix the stale `up` port echo; drop the "deferred" header line |
| `.dockerignore` | modify | `**/` patterns so nested `node_modules`/`.next`/caches never enter the context |
| `Dockerfile` | create | Python image: api, bot, migrate |
| `apps/miniapp/Dockerfile` | create | Next standalone image |
| `deploy/compose.yml` | create | The stack on the droplet (no caddy, no published ports) |
| `deploy/smart-accounting.caddy` | create | Our site block, `__SITE_ADDRESS__` placeholder |
| `deploy/.env.example` | create | Production `.env` template |
| `deploy/edge/compose.yml` | create | Shared Caddy stack (installed once) |
| `deploy/edge/Caddyfile` | create | `import sites/*.caddy` only |
| `.github/workflows/ci.yml` | create | Python + Node gates, architecture guards |
| `.github/workflows/deploy.yml` | create | verify → build ×2 → deploy |
| `docs/deploy.md` | create | Runbook: server prep, bvlk → edge, secrets, GitHub config, first deploy, rollback |
| `docs/bot-setup.md` | modify | Step 9 (production); drop `NEXT_PUBLIC_*` |
| `CLAUDE.md`, `README.md`, `STRUCTURE.md` | modify | "Deployment deferred" wording → point at `docs/deploy.md` |
| `thoughts/shared/plans/2026-07-21-m5-hardening-ops-release.md` | modify | Note that Phases 3–4 are executed by this plan |

---

### Task 1: Fail-fast production config

**Files:**
- Modify: `packages/core/src/smart_accounting/config.py`
- Test: `packages/core/tests/test_config.py`

**Interfaces:**
- Produces: `Settings` raises `pydantic.ValidationError` at construction when `ENVIRONMENT == "production"` and any of `BOT_TOKEN`, `JWT_SECRET`, `DOMAIN` is empty, or `len(JWT_SECRET) < 32`. The message names every missing field. Non-production behaviour is unchanged (test suites build `Settings(...)` without `ENVIRONMENT`).

- [ ] **Step 1: Write the failing test**

Create `packages/core/tests/test_config.py`:

```python
# Production must refuse to boot with an unset secret. Every Settings field has a default so local
# dev runs from an empty .env; in production that same default is a silent hole.
from __future__ import annotations

import pytest
from pydantic import ValidationError

from smart_accounting.config import Settings

PRODUCTION = {
    "ENVIRONMENT": "production",
    "BOT_TOKEN": "123456:prod-bot-token",
    "JWT_SECRET": "x" * 32,
    "DOMAIN": "accounting.example.com",
}


def settings(**overrides: object) -> Settings:
    # _env_file=None: a developer's local .env must not leak into these cases.
    return Settings(_env_file=None, **{**PRODUCTION, **overrides})  # type: ignore[arg-type]


def test_development_boots_with_empty_secrets() -> None:
    s = Settings(_env_file=None, ENVIRONMENT="development", BOT_TOKEN="", JWT_SECRET="", DOMAIN="")
    assert s.JWT_SECRET == ""


def test_production_boots_when_complete() -> None:
    assert settings().ENVIRONMENT == "production"


@pytest.mark.parametrize("field", ["BOT_TOKEN", "JWT_SECRET", "DOMAIN"])
def test_production_rejects_missing_secret(field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        settings(**{field: ""})


def test_production_names_every_missing_field_at_once() -> None:
    with pytest.raises(ValidationError) as excinfo:
        settings(BOT_TOKEN="", DOMAIN="")
    assert "BOT_TOKEN" in str(excinfo.value)
    assert "DOMAIN" in str(excinfo.value)


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        settings(JWT_SECRET="x" * 31)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_config.py -v`
Expected: `test_development_boots_with_empty_secrets` and `test_production_boots_when_complete` PASS; the five rejection cases FAIL with `DID NOT RAISE`.

- [ ] **Step 3: Write minimal implementation**

In `packages/core/src/smart_accounting/config.py`, change the import line and add the constants and validator:

```python
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secrets production cannot run without. Each defaults to "" so local dev boots from an empty .env.
_PRODUCTION_REQUIRED = ("BOT_TOKEN", "JWT_SECRET", "DOMAIN")
_MIN_JWT_SECRET_LENGTH = 32
```

and at the end of the `Settings` class body, after `FX_REFRESH_ENABLED`:

```python
    @model_validator(mode="after")
    def _require_production_secrets(self) -> Settings:
        # A .env that never reached the server would otherwise boot silently, and an empty
        # JWT_SECRET signs tokens anyone can forge. A container that refuses to start is the
        # better failure.
        if self.ENVIRONMENT != "production":
            return self
        missing = [name for name in _PRODUCTION_REQUIRED if not getattr(self, name)]
        if missing:
            raise ValueError(f"production requires {', '.join(missing)}")
        if len(self.JWT_SECRET) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"production requires JWT_SECRET of at least {_MIN_JWT_SECRET_LENGTH} characters"
            )
        return self
```

Also update the header comment (lines 6–7) — the `NEXT_PUBLIC_*` vars are removed in Task 2:

```python
# Env var list mirrors `.env.example`. Fields not read by Python (RESTIC/B2) are ignored via
# `extra="ignore"`. Production refuses to boot without its secrets (see the validator below).
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_config.py -v`
Expected: 7 passed.

Run: `uv run mypy packages/core && uv run ruff check packages/core && uv run ruff format --check packages/core`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/smart_accounting/config.py packages/core/tests/test_config.py
git commit -m "feat(m5): refuse to boot production without its secrets"
```

---

### Task 2: Build-time API proxy target and dead env cleanup

**Files:**
- Modify: `apps/miniapp/next.config.mjs`
- Modify: `turbo.json`
- Modify: `.env.example:36-40`
- Modify: `Makefile:1-2, 25`

**Interfaces:**
- Produces: env var `API_PROXY_TARGET`, read by `next.config.mjs` **at `next build`** (rewrites are compiled into `.next/routes-manifest.json`). Default `http://127.0.0.1:8000`; Task 4's Dockerfile sets `http://sa-api:8000`.

- [ ] **Step 1: Make the rewrite destination configurable**

Replace `apps/miniapp/next.config.mjs` with:

```js
// Next.js 15 config.
//
// The rewrite makes the API same-origin with the Mini-App in local dev (Caddy does it in
// production): the browser calls /api/v1/* on the Next origin and Next proxies to FastAPI. This
// keeps a single tunnel and avoids CORS entirely — the API has no CORS middleware.
//
// API_PROXY_TARGET is read when `next build` runs, not per request: rewrites are compiled into
// .next/routes-manifest.json. The container build sets it to the API's alias on the shared edge
// network, because 127.0.0.1 inside the Mini-App container is the Mini-App itself. In production
// Caddy routes /api/v1/* before a request reaches Next, so this is only the fallback.
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 2: Key turbo's cache on it and drop the dead vars**

In `turbo.json`, replace the `globalEnv` array with:

```json
  "globalEnv": ["NODE_ENV", "API_PROXY_TARGET"],
```

- [ ] **Step 3: Drop the dead Mini-App section from `.env.example`**

Delete these lines (no source file reads either variable; the Mini-App calls relative `/api/v1/*`):

```dotenv
# --- mini-app ---
# Resolve ${DOMAIN} to your actual cloudflared subdomain (Next.js doesn't shell-interpolate on read).
NEXT_PUBLIC_API_BASE_URL=https://YOUR-TUNNEL.trycloudflare.com/api/v1
NEXT_PUBLIC_BOT_USERNAME=
```

- [ ] **Step 4: Fix the Makefile**

Line 2, replace `# Deployment + CI targets are deferred (see plan §0).` with:

```make
# Production deploy is CI-driven (.github/workflows/deploy.yml); runbook in docs/deploy.md.
```

Line 25, replace the stale echo:

```make
	@echo "DB: localhost:5433 · Redis: localhost:6380"
```

- [ ] **Step 5: Verify the dev default and the override both land in the manifest**

Run: `pnpm --filter @smart-accounting/miniapp build && grep -o '127.0.0.1:8000' apps/miniapp/.next/routes-manifest.json | head -1`
Expected: build succeeds; prints `127.0.0.1:8000`.

Run: `API_PROXY_TARGET=http://sa-api:8000 pnpm --filter @smart-accounting/miniapp build && grep -o 'sa-api:8000' apps/miniapp/.next/routes-manifest.json | head -1`
Expected: prints `sa-api:8000`. (This proves the value is baked at build time, which is what Task 4 relies on.)

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add apps/miniapp/next.config.mjs turbo.json .env.example Makefile
git commit -m "feat(m5): configurable API proxy target; drop dead NEXT_PUBLIC env"
```

---

### Task 3: Python image (api, bot, migrate)

**Files:**
- Modify: `.dockerignore`
- Create: `Dockerfile`

**Interfaces:**
- Consumes: `smart-accounting-api` script (`apps/api/pyproject.toml:25`), `smart_accounting_bot.__main__`, `alembic.ini` + `migrations/`, Task 1's validator.
- Produces: image with `/app/.venv/bin` on `PATH`, workdir `/app` containing `alembic.ini` and `migrations/`, non-root user `app` (uid 1001), no default command. Commands used by Task 5: `smart-accounting-api`, `python -m smart_accounting_bot`, `alembic upgrade head`.

- [ ] **Step 1: Replace `.dockerignore`**

```gitignore
# Keeps the build context lean and, more importantly, keeps host artefacts out of the image:
# a macOS node_modules copied into a Linux build breaks native modules. Patterns are `**/`-prefixed
# because a bare `node_modules` only matches at the context root.
#
# Both Dockerfiles build from the repository root (the workspaces span packages/ and apps/).

.git
.github
.claude
.cursor
.agents
.thoughts*
thoughts
research
docs
deploy
ops/.local-data

**/node_modules
**/.next
**/.turbo
**/.venv
**/__pycache__
**/*.pyc
**/.pytest_cache
**/.mypy_cache
**/.ruff_cache
**/*.tsbuildinfo

.env
.env.*
!.env.example
db/password.txt
*.pem
*.key

*.md
!THIRD_PARTY_NOTICES.md
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1

# One image for both Python processes; deploy/compose.yml picks the command per service:
#   api      smart-accounting-api            uvicorn on 0.0.0.0:8000, one worker
#   bot      python -m smart_accounting_bot  long polling, exactly one replica
#   migrate  alembic upgrade head            one-shot, run by the deploy before `up`
#
# The build context is the repository root: the uv workspace spans packages/core and apps/*,
# and alembic.ini + migrations/ sit at the root.
#
#   docker build -t smart-accounting-app .

# ---------------------------------------------------------------- build stage

FROM python:3.12.3-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7.17 /uv /usr/local/bin/uv

# Bytecode is compiled once here rather than on every cold start. Copy mode because the cache
# mount is a different filesystem from /app. The slim image's own Python is the one to use.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies before source, so a code change does not invalidate the dependency layer.
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/bot/pyproject.toml apps/bot/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --all-packages --no-install-workspace

COPY packages/core packages/core
COPY apps/api apps/api
COPY apps/bot apps/bot
# --no-editable installs the workspace packages as real wheels in site-packages, so the runtime
# stage needs only the venv. It also puts the bot's .ftl catalogues where i18n.py:17 looks for
# them: next to the installed smart_accounting package.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --all-packages --no-editable

# --------------------------------------------------------------- runtime stage

FROM python:3.12.3-slim AS runtime

# A process that only reads its own code has no reason to be root.
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --no-create-home app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
# alembic resolves `script_location = migrations` relative to the working directory.
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations migrations

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

# No CMD on purpose: every service in deploy/compose.yml names its own. An image that quietly
# started the API when a service forgot its command would hide the mistake.
```

- [ ] **Step 3: Build it**

Run: `docker build -t ghcr.io/raiqasvl/smart-accounting-app:local .`
Expected: build succeeds.

- [ ] **Step 4: Verify imports, catalogues, migrations and the fail-fast config inside the image**

Run: `docker run --rm ghcr.io/raiqasvl/smart-accounting-app:local python -c "import smart_accounting_api.main, smart_accounting_bot.main; print('imports ok')"`
Expected: `imports ok`

Run: `docker run --rm ghcr.io/raiqasvl/smart-accounting-app:local python -c "from pathlib import Path; import smart_accounting as s; p = Path(s.__file__).parent / 'i18n'; print(sorted(x.relative_to(p).as_posix() for x in p.rglob('*.ftl')))"`
Expected: `['en/main.ftl', 'ru/main.ftl']`

Run: `docker run --rm ghcr.io/raiqasvl/smart-accounting-app:local alembic history`
Expected: three revisions, head `0003_tx_idempotency`.

Run: `docker run --rm -e ENVIRONMENT=production ghcr.io/raiqasvl/smart-accounting-app:local python -c "from smart_accounting.config import get_config; get_config()"`
Expected: non-zero exit, `ValidationError` naming `BOT_TOKEN, JWT_SECRET, DOMAIN`.

Run: `docker run --rm ghcr.io/raiqasvl/smart-accounting-app:local id -u`
Expected: `1001`

- [ ] **Step 5: Commit**

```bash
git add .dockerignore Dockerfile
git commit -m "feat(m5): python image for api, bot and migrate"
```

---

### Task 4: Mini-App image

**Files:**
- Create: `apps/miniapp/Dockerfile`

**Interfaces:**
- Consumes: `API_PROXY_TARGET` (Task 2); pnpm workspace (`apps/miniapp`, `packages/api-types`).
- Produces: image serving Next standalone on `0.0.0.0:3000`, non-root, with a `HEALTHCHECK` on `/`. Its rewrite fallback points at `http://sa-api:8000`.

- [ ] **Step 1: Create `apps/miniapp/Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1

# The build context is the repository root, not this directory: the install needs the workspace
# lockfile, and tsconfig.json resolves @shared/* to ../../packages/api-types/src. Those imports
# are type-only and nothing from that package reaches the bundle, but `next build` type-checks,
# so the files must be on disk.
#
#   docker build -f apps/miniapp/Dockerfile -t smart-accounting-miniapp .

# ---------------------------------------------------------------- build stage

FROM node:20.18.0-alpine AS builder

# Corepack prompts before downloading a pnpm it does not have, and a prompt in a
# non-interactive build is a hang, not a question.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1

# Baked into .next/routes-manifest.json by `next build` (see next.config.mjs). `sa-api` is the
# API's alias on the shared edge network. Caddy routes /api/v1/* before a request reaches Next,
# so this matters only for a path the Caddy matcher misses — and then it answers instead of 502.
ENV API_PROXY_TARGET=http://sa-api:8000

# The corepack bundled with Node 20.18 verifies pnpm against npm registry signing keys that npm
# has since rotated, and fails with "Cannot find matching keyid". A newer corepack carries the
# current keys. Pinned, so a future corepack release cannot change the build under us.
RUN npm install -g corepack@0.36.0 \
 && corepack enable

WORKDIR /app

# Manifests before source, so a code change does not invalidate the install layer.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/miniapp/package.json apps/miniapp/package.json
COPY packages/api-types/package.json packages/api-types/package.json
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY apps/miniapp apps/miniapp
COPY packages/api-types packages/api-types
RUN pnpm turbo run build --filter=@smart-accounting/miniapp

# --------------------------------------------------------------- runtime stage

FROM node:20.18.0-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1

# A process that only reads its own bundle has no reason to be root.
RUN addgroup -S -g 1001 nodejs \
 && adduser -S -u 1001 -G nodejs nextjs

# `output: "standalone"` emits traced node_modules at the bundle root and the app under its
# workspace path, so server.js lands at /app/apps/miniapp/server.js with its dependencies beside
# it. Static assets are not traced and are copied separately. The app has no public/ directory.
COPY --from=builder --chown=nextjs:nodejs /app/apps/miniapp/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/miniapp/.next/static ./apps/miniapp/.next/static

USER nextjs

EXPOSE 3000

# Lets compose wait for the server to answer rather than merely exist.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:3000/ || exit 1

CMD ["node", "apps/miniapp/server.js"]
```

- [ ] **Step 2: Build it**

Run: `docker build -f apps/miniapp/Dockerfile -t ghcr.io/raiqasvl/smart-accounting-miniapp:local .`
Expected: build succeeds. If the runtime `COPY` of `server.js` fails, list the standalone tree in the builder (`docker build --target builder -t sa-mini-builder -f apps/miniapp/Dockerfile . && docker run --rm sa-mini-builder find apps/miniapp/.next/standalone -maxdepth 3 -name server.js`) and fix the `CMD` path to match.

- [ ] **Step 3: Verify it serves and carries the right fallback**

Run: `docker run --rm -d --name sa-miniapp-check -p 3100:3000 ghcr.io/raiqasvl/smart-accounting-miniapp:local && sleep 5 && curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3100/`
Expected: `200`

Run: `docker exec sa-miniapp-check grep -o 'sa-api:8000' apps/miniapp/.next/routes-manifest.json | head -1`
Expected: `sa-api:8000`

Run: `docker exec sa-miniapp-check id -u; docker rm -f sa-miniapp-check`
Expected: `1001`, then the container name.

- [ ] **Step 4: Commit**

```bash
git add apps/miniapp/Dockerfile
git commit -m "feat(m5): mini-app standalone image"
```

---

### Task 5: Deploy stack and shared edge proxy

**Files:**
- Create: `deploy/compose.yml`
- Create: `deploy/smart-accounting.caddy`
- Create: `deploy/.env.example`
- Create: `deploy/edge/compose.yml`
- Create: `deploy/edge/Caddyfile`

**Interfaces:**
- Consumes: both images (Tasks 3–4); `/readyz` (`health.py:19-27`).
- Produces: services `db`, `redis`, `migrate`, `api`, `bot`, `miniapp` in compose project `smart-accounting`; aliases `sa-api`, `sa-miniapp` on external network `edge`; site file with placeholder `__SITE_ADDRESS__` (Task 7 renders it); `APP_TAG` variable (default `latest`) for pinning/rollback.

- [ ] **Step 1: Create `deploy/compose.yml`**

```yaml
# Deployed to /srv/smart-accounting/ on the droplet, beside .env and db/password.txt.
#
# The droplet never builds: GitHub Actions publishes both images to GHCR and this file only
# pulls them. Nothing here publishes a host port. The shared Caddy in /srv/edge (deploy/edge/)
# reaches `sa-api` and `sa-miniapp` over the external `edge` network; Postgres and Redis sit on
# `backend`, which Caddy is not attached to.
#
# Order, as .github/workflows/deploy.yml runs it:
#   docker compose pull
#   docker compose run --rm migrate
#   docker compose up -d --remove-orphans
#
# Roll back by pinning an earlier build: APP_TAG=<commit sha> in .env, then `up -d`.

name: smart-accounting

x-app: &app
  image: ghcr.io/raiqasvl/smart-accounting-app:${APP_TAG:-latest}
  env_file: .env
  restart: unless-stopped

services:
  db:
    image: postgres:16
    user: postgres
    restart: unless-stopped
    # No `ports`, unlike ops/compose.yml. On a public machine a published 5432 is Postgres on the
    # internet, and Docker writes its own iptables rules that bypass UFW.
    secrets: [db-password]
    environment:
      POSTGRES_DB: smart_accounting
      POSTGRES_USER: smart_accounting
      POSTGRES_PASSWORD_FILE: /run/secrets/db-password
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD', 'pg_isready', '-U', 'smart_accounting']
      interval: 5s
      retries: 10
    networks: [backend]

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
      interval: 5s
      retries: 10
    networks: [backend]

  # One-shot. The deploy runs it with `run --rm` between pull and up, never from an entrypoint:
  # api and bot start together and would race for alembic's lock. Revision 0002 seeds the
  # currency table, so skipping this leaves an empty app, not just a missing schema.
  # The profile keeps `up` from starting it a second time; `run migrate` still finds it.
  migrate:
    <<: *app
    command: ['alembic', 'upgrade', 'head']
    restart: 'no'
    profiles: [tools]
    depends_on:
      db:
        condition: service_healthy
    networks: [backend]

  api:
    <<: *app
    command: ['smart-accounting-api']
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      # /readyz runs SELECT 1 and answers 503 when the database is gone; /healthz is always 200
      # and would report a healthy API with no database. urlopen raises on 503. The slim image
      # has no curl, hence the standard library.
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=3)"
      interval: 15s
      timeout: 5s
      start_period: 20s
      retries: 3
    networks:
      backend:
      edge:
        # Prefixed: `edge` is shared with other projects, and two services answering to the same
        # name there would be load-balanced across unrelated apps.
        aliases: [sa-api]

  bot:
    <<: *app
    command: ['python', '-m', 'smart_accounting_bot']
    # Exactly one replica: Telegram serves getUpdates to one consumer per token, and a second
    # poller gets TelegramConflictError. set_my_commands runs at boot, so a moment without
    # egress to api.telegram.org exits the process — restart covers it.
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks: [backend]

  miniapp:
    # Healthcheck comes from the image (apps/miniapp/Dockerfile).
    image: ghcr.io/raiqasvl/smart-accounting-miniapp:${APP_TAG:-latest}
    restart: unless-stopped
    networks:
      edge:
        aliases: [sa-miniapp]

networks:
  backend:
  edge:
    external: true

volumes:
  db-data:
  redis-data:

secrets:
  db-password:
    file: ./db/password.txt
```

- [ ] **Step 2: Create `deploy/smart-accounting.caddy`**

```caddy
# Installed as /srv/edge/sites/smart-accounting.caddy by .github/workflows/deploy.yml, which
# replaces __SITE_ADDRESS__ with the SITE_ADDRESS repository variable (the bare domain) first.
#
# Routes an explicit path list rather than a prefix: /healthz and /readyz live at bare paths
# outside /api/v1 (apps/api/src/smart_accounting_api/routers/health.py). /docs, /redoc and
# /openapi.json stay public on purpose (D30). The API has no CORS middleware, so it and the
# Mini-App must keep sharing this one origin.

__SITE_ADDRESS__ {
	encode zstd gzip

	@api path /api/v1/* /healthz /readyz /docs /redoc /openapi.json
	handle @api {
		reverse_proxy sa-api:8000
	}

	handle {
		reverse_proxy sa-miniapp:3000
	}

	log {
		output stdout
		format console
	}
}
```

- [ ] **Step 3: Create `deploy/.env.example`**

```dotenv
# Template for /srv/smart-accounting/.env on the droplet: chmod 600, never committed.
# Generate every secret fresh for production; never copy one from a development .env.
# Comments stay on their own lines: an inline `# ...` after a value can end up inside it.

ENVIRONMENT=production
LOG_LEVEL=INFO

# Bare hostname, no https:// — the bot builds the Mini-App button URL from it.
DOMAIN=

# The production bot from @BotFather, not the dev bot: two pollers on one token conflict.
BOT_TOKEN=
# Without the leading @.
BOT_USERNAME=

# python3 -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET=
JWT_LIFETIME_SECONDS=1800

# The password must equal db/password.txt beside this file: Postgres reads that file, the app
# reads this DSN. `db` and `redis` are compose service names.
POSTGRES_DSN=postgresql+asyncpg://smart_accounting:PASSWORD@db:5432/smart_accounting
REDIS_DSN=redis://redis:6379/0

FRANKFURTER_BASE_URL=https://api.frankfurter.dev/v1
FX_REFRESH_INTERVAL_SECONDS=3600
FX_REFRESH_ENABLED=True

# Pin an earlier build to roll back (a commit sha from the GHCR tags). Unset means latest.
# APP_TAG=
```

- [ ] **Step 4: Create `deploy/edge/compose.yml`**

```yaml
# The shared reverse proxy for every project on the droplet. Installed once, by hand, at
# /srv/edge/ (docs/deploy.md, "Moving bvlk onto the edge").
#
# Each project owns exactly one file in sites/ and reloads Caddy after replacing it. Nobody edits
# this Caddyfile or another project's site file, so no deploy can erase a neighbour's routes.
#
#   docker network create edge       # once, before the first `up`
#   docker compose up -d

name: edge

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
      - '443:443/udp' # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./sites:/etc/caddy/sites:ro
      # Certificates. Losing this volume means re-issuing every certificate, and Let's Encrypt
      # rate-limits that, so it is a named volume rather than a bind mount.
      - caddy-data:/data
      - caddy-config:/config
    networks: [edge]

networks:
  edge:
    external: true

volumes:
  caddy-data:
  caddy-config:
```

- [ ] **Step 5: Create `deploy/edge/Caddyfile`**

```caddy
# /srv/edge/Caddyfile — deliberately nothing but the import. Each project installs its own site
# file into sites/ and runs `caddy reload`; a file that fails to load is rejected and the running
# config stays in place.

import sites/*.caddy
```

- [ ] **Step 6: Validate both compose files**

Run: `docker network create edge 2>/dev/null; touch deploy/.env && mkdir -p deploy/db && touch deploy/db/password.txt && docker compose -f deploy/compose.yml config --quiet && echo stack-ok; rm -rf deploy/.env deploy/db`
Expected: `stack-ok`

Run: `docker compose -f deploy/edge/compose.yml config --quiet && echo edge-ok`
Expected: `edge-ok`

- [ ] **Step 7: Bring the whole thing up locally, laid out as on the server**

The check lives in a scratch directory that mirrors `/srv/smart-accounting` and `/srv/edge`. Values are throwaway; the bot token is fake, so the bot is expected to exit at `set_my_commands` with `Unauthorized` (which proves image, imports, i18n and Redis wiring up to that point — the real token is exercised on the first prod deploy).

```bash
S=$(mktemp -d)
mkdir -p "$S/sa/db" "$S/edge/sites"
cp deploy/compose.yml "$S/sa/"
cp deploy/edge/compose.yml deploy/edge/Caddyfile "$S/edge/"
PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
printf '%s' "$PW" > "$S/sa/db/password.txt"
sed -e "s|^DOMAIN=.*|DOMAIN=localhost|" \
    -e "s|^BOT_TOKEN=.*|BOT_TOKEN=123456:local-check-not-a-real-token|" \
    -e "s|^BOT_USERNAME=.*|BOT_USERNAME=local_check_bot|" \
    -e "s|^JWT_SECRET=.*|JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" \
    -e "s|PASSWORD@db|$PW@db|" \
    -e "s|^# APP_TAG=.*|APP_TAG=local|" \
    deploy/.env.example > "$S/sa/.env"
sed 's|__SITE_ADDRESS__|http://localhost|' deploy/smart-accounting.caddy > "$S/edge/sites/smart-accounting.caddy"
docker network create edge 2>/dev/null || true
docker compose -f "$S/sa/compose.yml" run --rm migrate
docker compose -f "$S/sa/compose.yml" up -d
# The edge stack binds 80/443; locally we run the same image and files on 8088 instead.
docker run -d --name edge-check --network edge -p 8088:80 \
  -v "$S/edge/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$S/edge/sites:/etc/caddy/sites:ro" caddy:2-alpine
echo "$S"
```

Expected: `migrate` prints the three `Running upgrade` lines and exits 0; `up -d` starts five services.

- [ ] **Step 8: Verify health, routing and isolation**

Run: `sleep 25; docker compose -f "$S/sa/compose.yml" ps --format 'table {{.Service}}\t{{.Status}}'`
Expected: `api` and `miniapp` `healthy`; `db`, `redis` `healthy`; `bot` restarting (fake token, see Step 7).

Run: `docker compose -f "$S/sa/compose.yml" logs bot | grep -m1 -i unauthorized`
Expected: a Telegram `Unauthorized` line — and no import, i18n or Redis error before it.

Run: `for p in /healthz /readyz /openapi.json /docs /api/v1/me /; do printf '%-20s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8088$p)"; done`
Expected: `/healthz 200`, `/readyz 200`, `/openapi.json 200`, `/docs 200`, `/api/v1/me 401` (reached the API, rejected without a JWT), `/ 200`.

Run: `curl -s http://localhost:8088/api/v1/me`
Expected: `{"error":{"code":"jwt_invalid","params":{"reason":"missing_bearer"}},"request_id":"req_…"}` — the D24 envelope proves the path hit FastAPI, not Next. (Don't use an endpoint with a required query parameter such as `/currencies`: FastAPI validates it before auth and answers 422 in its default `{"detail": …}` shape, which bypasses D24 — a pre-existing API gap, tracked separately.)

Run: `docker compose -f "$S/sa/compose.yml" up -d --remove-orphans 2>&1 | grep -i migrate || echo "migrate not started by up"`
Expected: `migrate not started by up` — the `tools` profile keeps it out of `up`.

Run (edge safety — a broken site file must not take down the proxy):
`printf 'http://localhost {\n\treverse_proxy {\n' > "$S/edge/sites/smart-accounting.caddy" && docker exec edge-check caddy reload --config /etc/caddy/Caddyfile; echo "exit=$?"; curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8088/readyz`
Expected: `exit=1`, then `200` — the reload is rejected and the running config keeps serving.

Run: `docker compose -f "$S/sa/compose.yml" ps --format '{{.Service}} {{.Ports}}' | grep -E '0\.0\.0\.0|:::' || echo "no published ports"`
Expected: `no published ports`

Run: `docker run --rm --network edge alpine sh -c 'nslookup db 2>&1 | tail -2; nslookup sa-api 2>&1 | tail -2'`
Expected: `db` does not resolve on `edge`; `sa-api` does.

- [ ] **Step 9: Tear down**

```bash
docker rm -f edge-check
docker compose -f "$S/sa/compose.yml" --profile tools down -v
rm -rf "$S"
```

- [ ] **Step 10: Commit**

```bash
git add deploy/
git commit -m "feat(m5): deploy stack and shared edge proxy"
```

---

### Task 6: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: a workflow callable via `workflow_call` (Task 7 uses `uses: ./.github/workflows/ci.yml`), with jobs `python`, `node`, `guards`.

- [ ] **Step 1: Confirm every gate is green locally first** (CI that is red on day one teaches everyone to ignore it)

Run: `make check`
Expected: green. Additionally run the two gates CI adds that `make check` does not:

Run: `uv run alembic check`
Expected: `No new upgrade operations detected.` If it reports drift, stop and raise it — do not paper over it in CI.

Run: `pnpm format:check`
Expected: all files pass. If not, run `pnpm format` and commit that separately before this task.

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  pull_request:
  # Deploy calls this before it builds an image, so nothing ships without the checks a pull
  # request gets. There is deliberately no `push: main` trigger: it would start a second run in
  # the same concurrency group as the one Deploy calls, and the two would cancel each other.
  workflow_call:

# A second push to the same branch makes the first run irrelevant.
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  python:
    name: python — lint / types / migrations / tests
    runs-on: ubuntu-latest
    timeout-minutes: 15

    services:
      # The official image, because migration 0001 runs CREATE EXTENSION ltree / pgcrypto /
      # btree_gist, which needs the superuser a service container gives us.
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: smart_accounting
          POSTGRES_USER: smart_accounting
          POSTGRES_PASSWORD: ci
        ports: ['5432:5432']
        options: >-
          --health-cmd "pg_isready -U smart_accounting"
          --health-interval 5s --health-timeout 5s --health-retries 10
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s --health-timeout 5s --health-retries 10

    env:
      POSTGRES_DSN: postgresql+asyncpg://smart_accounting:ci@localhost:5432/smart_accounting
      REDIS_DSN: redis://localhost:6379/0
      FX_REFRESH_ENABLED: 'False'

    steps:
      - uses: actions/checkout@v5

      - uses: astral-sh/setup-uv@v6
        with:
          version: '0.7.17'
          enable-cache: true

      - name: Install
        run: uv sync --frozen --all-packages

      - name: Lint
        run: uv run ruff check

      - name: Format
        run: uv run ruff format --check

      - name: Types
        run: uv run mypy packages/core apps/api apps/bot

      # The test suites run against a migrated database (packages/core/tests/conftest.py).
      - name: Migrate
        run: uv run alembic upgrade head

      - name: Models match migrations
        run: uv run alembic check

      - name: Test
        run: uv run pytest

  node:
    name: node — lint / format / types / tests / build
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v5

      # Version comes from the packageManager field in package.json.
      - uses: pnpm/action-setup@v4

      - uses: actions/setup-node@v5
        with:
          node-version-file: .tool-versions
          cache: pnpm

      - name: Install
        run: pnpm install --frozen-lockfile

      - name: Lint
        run: pnpm lint

      - name: Format
        run: pnpm format:check

      - name: Types
        run: pnpm typecheck

      - name: Test
        run: pnpm test

      - name: Build
        run: pnpm build

  guards:
    name: architecture guards
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - uses: actions/checkout@v5

      # CLAUDE.md states both rules as enforced; until this job existed nothing enforced them.
      - name: Bot calls services only (D22)
        run: |
          if grep -rnE 'smart_accounting\.(models|repositories)' apps/bot/src; then
            echo "::error::apps/bot must call smart_accounting.services, never models or repositories (D22)"
            exit 1
          fi

      - name: Apps never import each other
        run: |
          if grep -rnE '\bsmart_accounting_api\b' apps/bot/src || grep -rnE '\bsmart_accounting_bot\b' apps/api/src; then
            echo "::error::apps/api and apps/bot must not import each other"
            exit 1
          fi

      - name: No hardcoded translated text
        run: python3 ops/i18n_check.py
```

- [ ] **Step 3: Prove the D22 guard actually fails on a violation**

Run: `echo 'from smart_accounting.models import User' >> apps/bot/src/smart_accounting_bot/__init__.py && (grep -rnE 'smart_accounting\.(models|repositories)' apps/bot/src && echo "guard would FAIL (correct)"); git checkout apps/bot/src/smart_accounting_bot/__init__.py`
Expected: prints the offending line and `guard would FAIL (correct)`; the file is restored.

- [ ] **Step 4: Lint the workflow**

Run: `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest -color .github/workflows/ci.yml`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci(m5): python and node gates plus architecture guards"
```

The first real run happens when this branch is opened as a pull request.

---

### Task 7: Deploy workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: `ci.yml` (Task 6); both Dockerfiles; `deploy/compose.yml`, `deploy/smart-accounting.caddy` (Task 5).
- Produces: requires repository **secrets** `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_HOST_KEY` and **variables** `SITE_ADDRESS`, `DEPLOY_ENABLED` (documented in Task 8).

- [ ] **Step 1: Create `.github/workflows/deploy.yml`**

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

# Never let two deploys race onto the droplet. Unlike CI, in-progress runs are not cancelled:
# a half-applied deploy is worse than a redundant one.
concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  # The same gates a pull request gets. A red test must not reach the server because it merged.
  verify:
    uses: ./.github/workflows/ci.yml

  build:
    name: build and publish ${{ matrix.name }}
    needs: verify
    # Off until the droplet is prepared (docs/deploy.md). Until then a push to main runs CI only.
    if: vars.DEPLOY_ENABLED == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: read
      packages: write

    strategy:
      matrix:
        include:
          - name: app
            dockerfile: Dockerfile
            image: smart-accounting-app
          - name: miniapp
            dockerfile: apps/miniapp/Dockerfile
            image: smart-accounting-miniapp

    steps:
      - uses: actions/checkout@v5

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          # Issued to this run by GitHub. There is no registry secret to rotate.
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ${{ matrix.dockerfile }}
          push: true
          # `latest` is what the droplet pulls; the sha tag says exactly which commit is serving
          # and is what APP_TAG pins to roll back.
          tags: |
            ghcr.io/${{ github.repository_owner }}/${{ matrix.image }}:latest
            ghcr.io/${{ github.repository_owner }}/${{ matrix.image }}:${{ github.sha }}
          cache-from: type=gha,scope=${{ matrix.name }}
          cache-to: type=gha,mode=max,scope=${{ matrix.name }}

  deploy:
    name: migrate and restart on the droplet
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v5

      - name: Prepare SSH
        env:
          SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          SSH_HOST_KEY: ${{ secrets.DEPLOY_HOST_KEY }}
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh && chmod 700 ~/.ssh
          printf '%s\n' "$SSH_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          # Pinned host key, not ssh-keyscan: trusting whatever answers on the first connection
          # would accept an impostor without complaint.
          printf '%s\n' "$SSH_HOST_KEY" > ~/.ssh/known_hosts
          chmod 644 ~/.ssh/known_hosts

      - name: Render the site file
        env:
          SITE_ADDRESS: ${{ vars.SITE_ADDRESS }}
        run: |
          set -euo pipefail
          if [ -z "$SITE_ADDRESS" ]; then
            echo "::error::set the SITE_ADDRESS repository variable to the bare domain"
            exit 1
          fi
          sed "s|__SITE_ADDRESS__|${SITE_ADDRESS}|" deploy/smart-accounting.caddy > smart-accounting.caddy
          if grep -q __SITE_ADDRESS__ smart-accounting.caddy; then
            echo "::error::placeholder survived rendering"
            exit 1
          fi

      # Without this the droplet keeps whatever compose file was last copied by hand, and a change
      # under deploy/ silently never ships.
      - name: Sync deployment config
        env:
          SSH_HOST: ${{ secrets.DEPLOY_HOST }}
          SSH_USER: ${{ secrets.DEPLOY_USER }}
        run: |
          set -euo pipefail
          scp -i ~/.ssh/deploy_key -o IdentitiesOnly=yes \
            deploy/compose.yml "$SSH_USER@$SSH_HOST:/srv/smart-accounting/compose.yml"
          scp -i ~/.ssh/deploy_key -o IdentitiesOnly=yes \
            smart-accounting.caddy "$SSH_USER@$SSH_HOST:/tmp/smart-accounting.caddy"

      # Secrets travel through the environment rather than being interpolated into the script,
      # so nothing in them can be read as shell. The script goes to the remote bash on stdin, so
      # the registry token never appears in the droplet's process list.
      - name: Deploy over SSH
        env:
          SSH_HOST: ${{ secrets.DEPLOY_HOST }}
          SSH_USER: ${{ secrets.DEPLOY_USER }}
          GHCR_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GHCR_USER: ${{ github.actor }}
        run: |
          set -euo pipefail
          # The heredoc is unquoted on purpose: GHCR_TOKEN and GHCR_USER must expand here, on the
          # runner, so the token reaches the droplet inside stdin. Nothing else in the script may
          # contain a `$`.
          # shellcheck disable=SC2087
          ssh -i ~/.ssh/deploy_key -o IdentitiesOnly=yes \
            "$SSH_USER@$SSH_HOST" 'bash -euo pipefail -s' <<REMOTE
          printf '%s' '${GHCR_TOKEN}' | docker login ghcr.io -u '${GHCR_USER}' --password-stdin
          cd /srv/smart-accounting
          docker compose pull
          docker logout ghcr.io

          # Before up, never from an entrypoint: api and bot start together and would race for
          # alembic's lock. Revision 0002 seeds currencies, so this is data as well as schema.
          docker compose run --rm -T migrate </dev/null
          docker compose up -d --remove-orphans

          # Install the site file only if Caddy accepts it. A rejected reload keeps the running
          # config, and restoring the previous file keeps the disk in step with it, so a later
          # restart of the edge cannot come up on a broken file.
          cd /srv/edge/sites
          if [ -f smart-accounting.caddy ]; then cp smart-accounting.caddy smart-accounting.caddy.prev; fi
          mv /tmp/smart-accounting.caddy smart-accounting.caddy
          if ! docker compose -f /srv/edge/compose.yml exec -T caddy caddy reload --config /etc/caddy/Caddyfile </dev/null; then
            if [ -f smart-accounting.caddy.prev ]; then mv smart-accounting.caddy.prev smart-accounting.caddy; else rm smart-accounting.caddy; fi
            exit 1
          fi
          rm -f smart-accounting.caddy.prev

          # Superseded layers accumulate fast.
          docker image prune -f
          REMOTE

      # /readyz crosses Caddy, the API and Postgres in one request; / proves the Mini-App.
      - name: Confirm the app answers
        env:
          SITE_ADDRESS: ${{ vars.SITE_ADDRESS }}
        run: |
          set -euo pipefail
          for path in /readyz /; do
            url="https://${SITE_ADDRESS}${path}"
            for i in $(seq 1 12); do
              code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || true)
              if [ "$code" = "200" ]; then
                echo "$url answered 200 after $((i * 5))s"
                continue 2
              fi
              echo "$url attempt $i: HTTP $code"
              sleep 5
            done
            echo "::error::$url did not return 200 within 60s"
            exit 1
          done
```

- [ ] **Step 2: Lint the workflow**

Run: `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest -color .github/workflows/deploy.yml`
Expected: no output.

- [ ] **Step 3: Check the remote script renders as intended**

The heredoc is unquoted, so the runner expands `${GHCR_TOKEN}` and `${GHCR_USER}` before sending; the script must contain no other `$`. Run: `sed -n '/<<REMOTE/,/^          REMOTE/p' .github/workflows/deploy.yml | grep -n '\$' | grep -vE 'GHCR_(TOKEN|USER)|SSH_(USER|HOST)'`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci(m5): deploy to the droplet via GHCR and SSH"
```

---

### Task 8: Runbook and docs

**Files:**
- Create: `docs/deploy.md`
- Modify: `docs/bot-setup.md` (credential table rows for `NEXT_PUBLIC_*`; Step 5 Option C env snippet; the "Production deployment is deferred" note at line 312)
- Modify: `CLAUDE.md:10-11`, "Where things live" table
- Modify: `README.md:9`
- Modify: `STRUCTURE.md:581`
- Modify: `thoughts/shared/plans/2026-07-21-m5-hardening-ops-release.md` (frontmatter `status`, one note under Overview)

- [ ] **Step 1: Create `docs/deploy.md`**

```markdown
# Deploying to production

The stack runs on one DigitalOcean droplet it shares with bvlk. GitHub Actions builds the images;
the droplet only pulls them. Design and reasoning:
[thoughts/shared/plans/2026-09-26-m5-phase3-4-droplet-deploy.md](../thoughts/shared/plans/2026-09-26-m5-phase3-4-droplet-deploy.md).

| What | Where |
|---|---|
| Droplet | `ubuntu-omnionelocal-droplet`, `167.172.137.214`, NYC1, Ubuntu 24.04, 4 GB / 2 vCPU |
| Our stack | `/srv/smart-accounting/` — `compose.yml`, `.env`, `db/password.txt` |
| Shared proxy | `/srv/edge/` — `compose.yml`, `Caddyfile`, `sites/*.caddy` |
| Images | `ghcr.io/raiqasvl/smart-accounting-app`, `ghcr.io/raiqasvl/smart-accounting-miniapp` |

Sections 1–5 are one-time. Section 6 is what every push to `main` does on its own.

## 1. Server preparation

**Swap.** The droplet has none; under memory pressure the OOM killer picks Postgres first.

    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab

**Cloud Firewall.** In the DigitalOcean panel, attach a firewall allowing inbound 22, 80, 443
only. It sits outside the droplet, so Docker's iptables rules cannot bypass it the way they
bypass UFW. Nothing in our compose publishes a port, but this is the guard against someone
adding one.

**Deploy user.** GitHub Actions must not log in as root. If bvlk's `DEPLOY_USER` is already a
non-root user in the `docker` group, reuse it; otherwise:

    adduser --disabled-password --gecos '' deploy
    usermod -aG docker deploy
    install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
    # paste the public half of a new key pair made for this repo:
    install -m 600 -o deploy -g deploy /dev/stdin /home/deploy/.ssh/authorized_keys

Use a separate key pair per repository so either can be revoked alone.

## 2. Moving bvlk onto the edge proxy

bvlk's Caddy owns 80/443 today. It moves into `/srv/edge` so both projects can be served. Do the
repository change first — if bvlk's old `deploy.yml` runs after the switch, it starts its own
Caddy again, which then fails on the taken ports.

**In the bvlk repository:**

1. `deploy/compose.yml`: delete the `caddy` service and its volumes; attach `web` to the external
   network with a prefixed alias:

       networks:
         edge:
           aliases: [bvlk-web]
       # top level:
       networks:
         edge:
           external: true

2. Create `deploy/bvlk.caddy` from the current `deploy/Caddyfile`, with the literal site address
   (the value of `SITE_ADDRESS` in `/srv/bvlk/.env`) and `reverse_proxy bvlk-web:3000`.
3. `deploy.yml`: scp `deploy/bvlk.caddy` to `/srv/edge/sites/bvlk.caddy` instead of the
   Caddyfile; after `up -d` add `--remove-orphans` once and
   `docker compose -f /srv/edge/compose.yml exec -T caddy caddy reload --config /etc/caddy/Caddyfile </dev/null`.

**On the droplet (a few seconds of bvlk downtime at step 5):**

    # 1. network and edge files (copy deploy/edge/{compose.yml,Caddyfile} from this repo)
    docker network create edge
    mkdir -p /srv/edge/sites
    # 2. bvlk's site file, as prepared above
    cp bvlk.caddy /srv/edge/sites/
    # 3. carry the certificates over so nothing is re-issued (Let's Encrypt rate-limits repeats)
    docker volume create edge_caddy-data
    docker run --rm -v bvlk_caddy_data:/from:ro -v edge_caddy-data:/to alpine cp -a /from/. /to/
    # 4. attach the running bvlk web to edge under its alias
    docker network connect --alias bvlk-web edge bvlk-web-1
    # 5. switch
    docker stop bvlk-caddy-1 && docker compose -f /srv/edge/compose.yml up -d
    # 6. check
    curl -sI https://<bvlk domain>/ | head -1

Then merge the bvlk change; its next deploy recreates `web` with the network from compose and
removes the stopped Caddy. Roll back before merging with
`docker compose -f /srv/edge/compose.yml down && docker start bvlk-caddy-1`.

## 3. Domain

Buy the domain, add an **A record** to `167.172.137.214`. If DNS is on Cloudflare, keep the record
**DNS only (grey cloud)**: Caddy must complete the ACME challenge itself. Wait until
`dig +short <domain>` returns the droplet's address before the first deploy — a failed challenge
is rate-limited for an hour.

## 4. Secrets on the droplet

    install -d -m 750 -o deploy -g deploy /srv/smart-accounting /srv/smart-accounting/db
    chown deploy:deploy /srv/edge/sites

From your machine, fill a copy of `deploy/.env.example` (new prod bot token, freshly generated
`JWT_SECRET` and DB password) and copy both files over:

    python3 -c "import secrets; print(secrets.token_urlsafe(24))" > password.txt
    scp .env deploy@167.172.137.214:/srv/smart-accounting/.env
    scp password.txt deploy@167.172.137.214:/srv/smart-accounting/db/password.txt
    ssh deploy@167.172.137.214 'chmod 600 /srv/smart-accounting/.env /srv/smart-accounting/db/password.txt'

The password inside `POSTGRES_DSN` must equal `db/password.txt`. The production config refuses to
boot without `BOT_TOKEN`, `JWT_SECRET` (≥ 32 chars) and `DOMAIN`, so a missing value shows up as a
restarting container with the missing names in its log, not as a silently insecure API.

## 5. GitHub configuration

Repository → Settings → Secrets and variables → Actions.

| Kind | Name | Value |
|---|---|---|
| Secret | `DEPLOY_SSH_KEY` | private half of the deploy key pair |
| Secret | `DEPLOY_HOST` | `167.172.137.214` |
| Secret | `DEPLOY_USER` | `deploy` |
| Secret | `DEPLOY_HOST_KEY` | output of `ssh-keyscan -t ed25519 167.172.137.214`, taken once and checked against the droplet console |
| Variable | `SITE_ADDRESS` | the bare domain, e.g. `accounting.example.com` |
| Variable | `DEPLOY_ENABLED` | `true` — last, once sections 1–4 are done |

The bot token, JWT secret and DB password never go into GitHub: the repository is public and so
are its Actions logs.

## 6. Deploying

Every push to `main` runs CI; with `DEPLOY_ENABLED=true` it then builds both images, pushes them
to GHCR as `latest` and `<sha>`, and on the droplet: pulls, runs `migrate`, `up -d`, installs the
site file and reloads Caddy, and finally polls `https://<domain>/readyz` and `/`. Re-run a deploy
by hand from the Actions tab (`workflow_dispatch`).

After the first successful deploy, point the prod bot at the site in @BotFather — see
[bot-setup.md Step 9](bot-setup.md#step-9--production).

## 7. Operating

    cd /srv/smart-accounting
    docker compose ps
    docker compose logs -f api bot
    docker compose restart bot

**Roll back:** set `APP_TAG=<earlier commit sha>` in `.env`, then `docker compose up -d`. Remove
the line to return to `latest`. Migrations are not rolled back by this — check the target
commit's head revision first.
```

- [ ] **Step 2: Update `docs/bot-setup.md`**

In the credentials table, delete the row:

```markdown
| `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_BOT_USERNAME` | Derived from above |
```

In Step 5 ("After picking one, **update `.env`**"), replace the three-line dotenv block with:

```dotenv
DOMAIN=<your-tunnel-or-prod-domain-without-https>
```

Replace the note at line 312 (`> **Production deployment is deferred** ...`) with:

```markdown
## Step 9 — Production

Production uses its **own** bot — never the dev bot: Telegram gives each token's updates to one
poller, so a local `make dev-bot` on the prod token would fight the server for them.

1. `/newbot` in @BotFather → e.g. `Smart Accounting Hub` / `smart_accounting_hub_bot`. The token
   goes straight into `/srv/smart-accounting/.env` on the droplet ([deploy.md §4](deploy.md#4-secrets-on-the-droplet)) — nowhere else.
2. Repeat Step 3 (description, commands, privacy) for the prod bot.
3. After the first deploy answers on `https://<domain>/`:
   - `/newapp` (or `/myapps` → Edit Web App URL) → `https://<domain>/`
   - `/setmenubutton` → `Open app` → `https://<domain>/`
4. `/start` the prod bot from your phone and open the Mini-App.
```

- [ ] **Step 3: Update the "deferred" wording**

`CLAUDE.md` lines 10–11 — replace `MVP is **local-dev only** — deployment + CI are deferred.` with:

```markdown
Daily work is local dev; production deploys from `main` via GitHub Actions — see `docs/deploy.md`.
```

and add a row to the "Where things live" table:

```markdown
| Production deploy (compose, edge proxy, runbook) | `deploy/`, `.github/workflows/`, `docs/deploy.md` |
```

`README.md` line 9 — replace with:

```markdown
🚧 **In implementation.** Local dev for daily work; production deploys from `main` — see [docs/deploy.md](docs/deploy.md).
```

`STRUCTURE.md` line 581 — replace with:

```markdown
- Not deployment instructions — see `docs/deploy.md`.
```

- [ ] **Step 4: Mark M5 Phases 3–4 as executed by this plan**

In `thoughts/shared/plans/2026-07-21-m5-hardening-ops-release.md`, set frontmatter
`status: in-progress` and add directly under `## Overview`:

```markdown
> **2026-09-26:** Phases 3 and 4 are executed by
> [2026-09-26-m5-phase3-4-droplet-deploy.md](2026-09-26-m5-phase3-4-droplet-deploy.md), with three
> deviations recorded there: a self-contained `deploy/compose.yml` instead of the prod-override
> pair, a shared `/srv/edge` Caddy (bvlk already holds 80/443 on the droplet), and images built in
> CI rather than on the server. Phases 1, 2, 5, 6 are unchanged and still pending.
```

- [ ] **Step 5: Verify**

Run: `grep -rnE 'NEXT_PUBLIC_(API_BASE_URL|BOT_USERNAME)' --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=thoughts . || echo "no dead env left"`
Expected: `no dead env left`

Run: `make check`
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add docs/ CLAUDE.md README.md STRUCTURE.md thoughts/shared/plans/
git commit -m "docs(m5): deploy runbook, prod bot setup, un-defer deployment wording"
```

---

## Definition of Done (this plan)

- Both images build locally; the Python image carries migrations and `.ftl` catalogues and refuses `ENVIRONMENT=production` without secrets.
- The stack comes up locally laid out as on the server: `api`, `miniapp`, `db`, `redis` healthy; routing through Caddy verified path by path; no published ports; `db` unreachable from `edge`.
- `make check`, `alembic check`, `pnpm format:check` green; both workflows pass actionlint; the D22 guard demonstrably fails on a violation.
- `docs/deploy.md` lets the remaining one-time steps (server prep, bvlk → edge, domain, secrets, GitHub config) be executed without this conversation.

Not done by this plan, each needing its own go-ahead: executing `docs/deploy.md` §1–5 on the droplet and in bvlk, the first deploy, BotFather for the prod bot.
