# Role-Based Access Control — the single source of truth for authorization, used by both the
# API (require(permission) dependency) and the bot (RbacService) so the matrix never diverges.
from __future__ import annotations

import enum

from smart_accounting.errors import Forbidden


class Role(enum.IntEnum):
    OWNER = 0
    ADMIN = 1
    EDITOR = 2
    VIEWER = 3


# Permission strings gated per role (milestone §2.1). Higher roles are supersets of lower ones.
PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.OWNER: frozenset(
        {
            "book.delete",
            "book.invite",
            "book.role.change",
            "book.read",
            "tx.write",
            "tx.read",
            "category.write",
            "account.write",
        }
    ),
    Role.ADMIN: frozenset(
        {
            "book.invite",
            "book.role.change",
            "book.read",
            "tx.write",
            "tx.read",
            "category.write",
            "account.write",
        }
    ),
    Role.EDITOR: frozenset({"book.read", "tx.write", "tx.read", "category.write", "account.write"}),
    Role.VIEWER: frozenset({"book.read", "tx.read"}),
}

# Every permission that appears anywhere in the matrix (for validation/tests).
ALL_PERMISSIONS: frozenset[str] = frozenset().union(*PERMISSIONS.values())


def has_permission(role: int, permission: str) -> bool:
    return permission in PERMISSIONS.get(Role(role), frozenset())


def require_permission(role: int, permission: str) -> None:
    """Raise Forbidden if `role` does not grant `permission`."""
    if not has_permission(role, permission):
        raise Forbidden({"permission": permission, "role": int(role)})
