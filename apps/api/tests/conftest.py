# Shared pytest fixtures for the API test suite.
#
# Per plan Testing Strategy:
#   - `engine` / `sessionmaker` fixtures bound to a testcontainers-spun-up Postgres 16 instance.
#   - `client` fixture returns an httpx.AsyncClient bound to the FastAPI app with
#     dependency overrides for: settings, sessionmaker, current JWT claims (impersonation helper).
#   - `make_user` / `make_book` / `make_membership` factories for arrange-step convenience.
#   - All fixtures use `pytest_asyncio.fixture` and run with `asyncio_mode = "auto"` from
#     the root pyproject.toml's [tool.pytest.ini_options].
