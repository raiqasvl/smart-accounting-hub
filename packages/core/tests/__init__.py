# Tests for smart_accounting. Per plan Testing Strategy:
#   - Pure logic in services/ + repositories/ tested without DB (use in-memory SQLite for some).
#   - Integration tests use testcontainers Postgres 16 spun up via fixture.
#   - Property-based tests (hypothesis) for verify_init_data, decode_token, ltree cascade.
#   - RBAC matrix parametrised test.
#   - Weighted-avg arithmetic correctness test.
