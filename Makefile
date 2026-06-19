# Top-level developer entry points — local development only.
# Deployment + CI targets are deferred (see plan §0).
#
# `apps/api` and `apps/bot` run on the host via uv; `apps/miniapp` via pnpm.
# Only Postgres + Redis run in Docker (ops/compose.yml).

.PHONY: help bootstrap up down restart logs migrate revision \
        dev-api dev-bot dev-miniapp tunnel \
        test lint format typecheck check clean

help:                      ## Print this help.
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | awk -F':.*?## ' '{printf "  %-12s  %s\n", $$1, $$2}'

# --- one-time setup ---

bootstrap:                 ## One-time setup on a fresh clone.
	uv sync --all-packages
	pnpm install

# --- compose stack (postgres + redis only) ---

up:                        ## Start postgres + redis containers.
	docker compose -f ops/compose.yml up -d
	@echo "DB: localhost:5432 · Redis: localhost:6379"

down:                      ## Stop the compose stack.
	docker compose -f ops/compose.yml down

restart: down up           ## Restart compose stack.

logs:                      ## Tail compose logs.
	docker compose -f ops/compose.yml logs -f

# --- alembic ---

migrate:                   ## Apply migrations against the running DB.
	uv run alembic upgrade head

revision:                  ## Create a new auto-generated migration. Usage: make revision M="add foo column"
	uv run alembic revision --autogenerate -m "$(M)"

# --- run services on host (separate terminals) ---

dev-api:                   ## Run apps/api with uvicorn --reload.
	uv run uvicorn smart_accounting_api.main:app --reload --host 0.0.0.0 --port 8000

dev-bot:                   ## Run apps/bot polling.
	uv run python -m smart_accounting_bot

dev-miniapp:               ## Run apps/miniapp Next.js dev server on :3000.
	pnpm --filter '@smart-accounting/miniapp' dev

tunnel:                    ## Cloudflared tunnel to expose miniapp:3000 over HTTPS for Telegram.
	cloudflared tunnel --url http://localhost:3000

# --- quality gates ---

test:                      ## Run the full test suite (Python + TS).
	uv run pytest
	pnpm -r test

lint:                      ## Lint without modifying files.
	uv run ruff check
	pnpm lint

format:                    ## Apply formatting fixes in place.
	uv run ruff format
	pnpm format

typecheck:                 ## mypy + tsc.
	uv run mypy packages/core apps/api apps/bot
	pnpm typecheck

check: lint format typecheck test  ## Full pre-commit gate.

# --- cleanup ---

clean:                     ## Remove caches and venvs.
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache .turbo node_modules
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
