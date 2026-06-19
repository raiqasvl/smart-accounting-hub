# FastAPI dependencies that wrap Dishka providers + RBAC enforcement.
#
# Per plan §1.4 (M1) and §2.1 (M2):
#   - `current_jwt_claims()`: Depends-able function that extracts and verifies the
#     `Authorization: Bearer <jwt>` header against JWT_SECRET (D12).
#     Returns the decoded Claims (sub=user_id, book_id, role, exp, iat, jti).
#   - `current_user()`: Loads the User model for the verified claims.sub.
#   - `current_book_member()`: Loads the (book, role) for claims.book_id + claims.sub.
#     Raises 401 if claims.book_id is null (user still onboarding) when a route requires it.
#   - `require(permission: str)`: Factory that returns a Depends() asserting the caller's
#     role grants `permission` per the matrix in smart_accounting.auth.rbac.PERMISSIONS.
#
# These three are the gates every non-/health, non-/auth route must use.
