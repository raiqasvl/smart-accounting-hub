# Unit tests for HS256 JWT issuance/verification (DB-free).
from __future__ import annotations

import jwt as pyjwt
import pytest

from smart_accounting.auth.jwt import JwtCodec, decode_token, issue_token
from smart_accounting.errors import JwtExpired, JwtInvalid

SECRET = "test-secret-at-least-32-bytes-long-xxxxx"


def test_issue_decode_round_trip() -> None:
    token = issue_token(user_id=42, book_id=7, role=0, secret=SECRET)
    claims = decode_token(token, SECRET)
    assert claims.user_id == 42
    assert claims.book_id == 7
    assert claims.role == 0
    assert claims.exp > claims.iat
    assert claims.jti


def test_codec_round_trip() -> None:
    codec = JwtCodec(SECRET, lifetime_seconds=1800)
    claims = codec.decode(codec.issue(user_id=1, book_id=None, role=None))
    assert claims.user_id == 1
    assert claims.book_id is None
    assert claims.role is None


def test_expired_token_raises_jwt_expired() -> None:
    token = issue_token(user_id=1, book_id=1, role=0, secret=SECRET, lifetime_seconds=-10)
    with pytest.raises(JwtExpired):
        decode_token(token, SECRET)


def test_signature_tamper_raises_jwt_invalid() -> None:
    token = issue_token(user_id=1, book_id=1, role=0, secret=SECRET)
    head, _, sig = token.rpartition(".")
    tampered = (
        f"{head}.{'X' if sig[0] != 'X' else 'Y'}{sig[1:]}"  # first sig char always changes bytes
    )
    with pytest.raises(JwtInvalid):
        decode_token(tampered, SECRET)


def test_wrong_secret_raises_jwt_invalid() -> None:
    token = issue_token(user_id=1, book_id=1, role=0, secret=SECRET)
    with pytest.raises(JwtInvalid):
        decode_token(token, "a-different-secret-value-of-adequate-len")


def test_none_alg_rejected() -> None:
    forged = pyjwt.encode(
        {"sub": "1", "jti": "x", "iat": 0, "exp": 9999999999}, key="", algorithm="none"
    )
    with pytest.raises(JwtInvalid):
        decode_token(forged, SECRET)
