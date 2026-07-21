# RBAC permission matrix — the authorization source of truth.
from __future__ import annotations

import pytest

from smart_accounting.auth.rbac import (
    ALL_PERMISSIONS,
    PERMISSIONS,
    Role,
    has_permission,
    require_permission,
)
from smart_accounting.errors import Forbidden


def test_viewer_and_owner_extremes() -> None:
    assert PERMISSIONS[Role.VIEWER] == frozenset({"book.read", "tx.read"})
    assert "book.delete" in PERMISSIONS[Role.OWNER]
    for permission in ALL_PERMISSIONS:
        assert has_permission(Role.OWNER, permission)  # owner grants everything


def test_roles_are_nested_supersets() -> None:
    assert (
        PERMISSIONS[Role.VIEWER]
        <= PERMISSIONS[Role.EDITOR]
        <= PERMISSIONS[Role.ADMIN]
        <= PERMISSIONS[Role.OWNER]
    )


def test_only_owner_can_delete_book() -> None:
    assert has_permission(Role.OWNER, "book.delete")
    for role in (Role.ADMIN, Role.EDITOR, Role.VIEWER):
        assert not has_permission(role, "book.delete")


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("permission", sorted(ALL_PERMISSIONS))
def test_every_role_permission_pair(role: Role, permission: str) -> None:
    granted = has_permission(role, permission)
    assert granted == (permission in PERMISSIONS[role])
    if granted:
        require_permission(role, permission)  # must not raise
    else:
        with pytest.raises(Forbidden):
            require_permission(role, permission)
