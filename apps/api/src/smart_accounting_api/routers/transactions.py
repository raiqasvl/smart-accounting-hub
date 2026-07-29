# FX transactions surface. No future-annotations import (DishkaRoute needs concrete response types).
import base64
import binascii
import csv
import io
import json
from collections.abc import Iterator
from datetime import datetime
from typing import Literal

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from smart_accounting.auth.jwt import JwtCodec
from smart_accounting.errors import InvalidCursor
from smart_accounting.schemas import (
    TransactionCreateIn,
    TransactionOut,
    TransactionPage,
    TransactionPatchIn,
)
from smart_accounting.services.transaction_service import TransactionService

from ..deps import extract_claims

router = APIRouter(tags=["transactions"], route_class=DishkaRoute)

# Stable column order — downstream spreadsheets/scripts rely on it, so append, never reorder.
_CSV_COLUMNS = (
    "id",
    "occurred_at",
    "kind",
    "direction",
    "base_currency_code",
    "quote_currency_code",
    "amount_quote",
    "rate",
    "amount_base",
    "fee",
    "fee_currency_code",
    "base_account",
    "quote_account",
    "category",
    "note",
)


def _encode_cursor(tx: TransactionOut) -> str:
    payload = json.dumps({"at": tx.occurred_at.isoformat(), "id": tx.id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        data = json.loads(raw)
        return datetime.fromisoformat(data["at"]), int(data["id"])
    except (binascii.Error, ValueError, KeyError, TypeError) as exc:
        raise InvalidCursor({"cursor": cursor}) from exc


@router.post("/books/{book_id}/transactions", status_code=201)
async def create_transaction(
    book_id: int,
    body: TransactionCreateIn,
    request: Request,
    response: Response,
    jwt: FromDishka[JwtCodec],
    transaction_service: FromDishka[TransactionService],
) -> TransactionOut:
    claims = extract_claims(request, jwt)
    tx, replayed = await transaction_service.record(book_id, claims.user_id, body)
    if replayed:
        response.status_code = 200  # D28: idempotent replay returns the existing row
        response.headers["Idempotent-Replayed"] = "true"
    return tx


@router.get("/books/{book_id}/transactions")
async def list_transactions(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    transaction_service: FromDishka[TransactionService],
    direction: Literal["buy", "sell"] | None = None,
    quote: str | None = None,
    account_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    archived: bool = False,
    cursor: str | None = None,
    page_size: int = 50,
) -> TransactionPage:
    claims = extract_claims(request, jwt)
    page_size = min(max(page_size, 1), 100)
    after = _decode_cursor(cursor) if cursor else None
    rows = await transaction_service.list_for_book(
        book_id,
        claims.user_id,
        direction=direction,
        quote_currency_code=quote,
        account_id=account_id,
        occurred_after=date_from,
        occurred_before=date_to,
        archived=archived,
        after=after,
        limit=page_size + 1,
    )
    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = _encode_cursor(items[-1]) if has_more and items else None
    return TransactionPage(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/books/{book_id}/transactions/export.csv")
async def export_transactions_csv(
    book_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    transaction_service: FromDishka[TransactionService],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> StreamingResponse:
    claims = extract_claims(request, jwt)
    rows = await transaction_service.export_rows(book_id, claims.user_id, date_from, date_to)

    def lines() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(_CSV_COLUMNS)
        yield _drain(buffer)
        for row in rows:
            # Money serializes to its decimal string (D23), so the CSV matches the API byte for byte.
            data = row.model_dump(mode="json")
            writer.writerow([data[column] if data[column] is not None else "" for column in _CSV_COLUMNS])
            yield _drain(buffer)

    return StreamingResponse(
        lines(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="transactions-book-{book_id}.csv"'},
    )


def _drain(buffer: io.StringIO) -> str:
    chunk = buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    return chunk


@router.patch("/transactions/{tx_id}")
async def patch_transaction(
    tx_id: int,
    body: TransactionPatchIn,
    request: Request,
    jwt: FromDishka[JwtCodec],
    transaction_service: FromDishka[TransactionService],
) -> TransactionOut:
    claims = extract_claims(request, jwt)
    return await transaction_service.patch(tx_id, claims.user_id, body)


@router.delete("/transactions/{tx_id}")
async def delete_transaction(
    tx_id: int,
    request: Request,
    jwt: FromDishka[JwtCodec],
    transaction_service: FromDishka[TransactionService],
) -> dict[str, int]:
    claims = extract_claims(request, jwt)
    await transaction_service.archive(tx_id, claims.user_id)
    return {"archived": tx_id}
