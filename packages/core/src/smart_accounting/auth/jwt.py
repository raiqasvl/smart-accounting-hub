# HS256 JWT issuance + verification (D12).
#
# Per plan §1.4 (M1) and §5.1 (M5 security pass):
#
#   issue_token(*, user_id: int, book_id: int | None, role: int | None,
#               secret: str, lifetime_seconds: int = 1800) -> str
#       Claims: {sub: user_id, book_id, role, exp: now + lifetime, iat: now,
#                jti: secrets.token_hex(8)}.
#       Signed HS256 with `secret` (env JWT_SECRET, ≥32 bytes).
#
#   decode_token(token: str, secret: str) -> Claims
#       Verifies signature + expiry. Raises JwtExpired / JwtInvalid.
#       Rejects 'none' alg, missing claims, mismatched algorithms.
#
# Refresh model: NO refresh-token endpoint at v1.0. Mini-App re-posts fresh initData on focus
# (cheap; ~50ms server-side HMAC) and gets a new JWT. Defers a refresh-token rotation table to v1.1.
#
# Revocation: best-effort in-memory `jti` blocklist for compromised tokens (added in M5 if needed).
