# D24: every error the API returns is the envelope {"error": {"code", "params"}, "request_id"},
# including FastAPI's own request-validation failures, which bypassed it until 2026-09.
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from httpx import AsyncClient


async def test_missing_query_param_is_a_d24_envelope(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/currencies")
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert set(body) == {"error", "request_id"}
    assert body["request_id"].startswith("req_")
    assert body["error"] == {
        "code": "validation_error",
        "params": {"errors": [{"loc": ["query", "book_id"], "type": "missing"}]},
    }


async def test_invalid_body_lists_every_failing_field(
    client: AsyncClient, login: Callable[..., Any]
) -> None:
    session = await login(993000001)
    resp = await client.post(
        "/api/v1/books", headers=session["headers"], json={"kind": "not-a-number"}
    )
    assert resp.status_code == 422, resp.text
    errors = resp.json()["error"]["params"]["errors"]
    assert {"loc": ["body", "name"], "type": "missing"} in errors
    assert {"loc": ["body", "base_currency_code"], "type": "missing"} in errors
    assert {"loc": ["body", "kind"], "type": "int_parsing"} in errors


async def test_validation_errors_carry_no_english_text(client: AsyncClient) -> None:
    # FastAPI's `msg` is English prose and `ctx` can embed exception text; wording belongs to the
    # Mini-App and bot, so only `loc` and `type` may travel.
    resp = await client.get("/api/v1/currencies")
    assert "Field required" not in resp.text
    for error in resp.json()["error"]["params"]["errors"]:
        assert set(error) == {"loc", "type"}


async def test_openapi_documents_422_as_the_envelope(client: AsyncClient) -> None:
    # The generated TS types (packages/api-types) come from this spec; it must not keep promising
    # FastAPI's {"detail": [...]} shape.
    spec = (await client.get("/openapi.json")).json()
    response = spec["paths"]["/api/v1/currencies"]["get"]["responses"]["422"]
    assert response["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorOut")
    assert "HTTPValidationError" not in spec["components"]["schemas"]
