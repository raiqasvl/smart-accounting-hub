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
