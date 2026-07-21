# FastAPI request helpers. M1 has one auth gate: extract + verify the Bearer JWT into Claims.
# (current_user / current_book_member / require(permission) land in M2 with more endpoints.)
from __future__ import annotations

from fastapi import Request

from smart_accounting.auth.jwt import Claims, JwtCodec
from smart_accounting.errors import JwtInvalid


def extract_claims(request: Request, jwt: JwtCodec) -> Claims:
    """Parse `Authorization: Bearer <jwt>` and verify it. Raises JwtInvalid/JwtExpired (→401)."""
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise JwtInvalid({"reason": "missing_bearer"})
    claims = jwt.decode(token)
    if claims.book_id is None:
        raise JwtInvalid({"reason": "no_book_in_token"})
    return claims
