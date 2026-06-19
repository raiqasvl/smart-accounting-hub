# Shared fixtures consumed by all three Python test suites (apps/api, apps/bot, packages/core).
#
# Per plan Testing Strategy:
#   - `pg_container` (session scope): testcontainers Postgres 16 with ltree extension preloaded.
#   - `engine` (session): bound to pg_container's URL.
#   - `db_session` (function): opens a transaction at the start, ROLLBACKs at teardown — fast.
#   - `make_user`, `make_book`, `make_membership`, `make_account`, `make_transaction`: factories.
#   - `frozen_time` (function): freezegun helper for testing exchange-rate timestamps.
