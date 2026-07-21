# FastAPI request helpers. `extract_claims` is the auth gate (Bearer JWT -> Claims).
#
# M2 authorization is enforced in the SERVICE layer, not here: each book-scoped service method
# takes the actor's user_id, resolves their role for the *path* book_id via book_members
# (raising NotAMember if absent), and calls auth.rbac.require_permission. This keeps tenancy
# checks next to the DB access and avoids a FastAPI dependency that must reach into Dishka.
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
