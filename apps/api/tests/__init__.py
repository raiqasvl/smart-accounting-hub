# Tests for the API surface. Per plan Testing Strategy:
#   - pytest-asyncio + httpx.AsyncClient against a real Postgres (testcontainers).
#   - Per-test transaction rolled back via fixture.
#   - Coverage targets in plan §M2 onwards: test_books.py, test_invites.py, test_accounts.py,
#     test_transactions.py, test_reports.py, test_internal_transfers.py.
