# Role-Based Access Control. M1 defines the Role enum only; the PERMISSIONS matrix +
# require_or_raise() land in M2.
from __future__ import annotations

import enum


class Role(enum.IntEnum):
    OWNER = 0
    ADMIN = 1
    EDITOR = 2
    VIEWER = 3
