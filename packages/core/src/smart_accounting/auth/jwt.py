# HS256 JWT issuance + verification (D12). JWT.sub = users.id.
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

import jwt as pyjwt

from smart_accounting.errors import JwtExpired, JwtInvalid


@dataclass(frozen=True)
class Claims:
    user_id: int
    book_id: int | None
    role: int | None
    jti: str
    iat: int
    exp: int


def issue_token(
    *,
    user_id: int,
    book_id: int | None,
    role: int | None,
    secret: str,
    lifetime_seconds: int = 1800,
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "book_id": book_id,
        "role": role,
        "iat": now,
        "exp": now + lifetime_seconds,
        "jti": secrets.token_hex(8),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> Claims:
    """Decode + verify an HS256 token. Rejects the 'none' alg (algorithms allow-list), bad
    signatures, and missing claims. Raises JwtExpired on expiry, JwtInvalid otherwise."""
    try:
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError as exc:
        raise JwtExpired() from exc
    except pyjwt.InvalidTokenError as exc:
        raise JwtInvalid() from exc
    try:
        return Claims(
            user_id=int(payload["sub"]),
            book_id=payload.get("book_id"),
            role=payload.get("role"),
            jti=payload["jti"],
            iat=int(payload["iat"]),
            exp=int(payload["exp"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise JwtInvalid() from exc


class JwtCodec:
    """Holds JWT_SECRET + lifetime; injected as an APP-scope singleton via Dishka."""

    def __init__(self, secret: str, lifetime_seconds: int = 1800) -> None:
        self._secret = secret
        self._lifetime = lifetime_seconds

    def issue(self, *, user_id: int, book_id: int | None, role: int | None) -> str:
        return issue_token(
            user_id=user_id,
            book_id=book_id,
            role=role,
            secret=self._secret,
            lifetime_seconds=self._lifetime,
        )

    def decode(self, token: str) -> Claims:
        return decode_token(token, self._secret)
