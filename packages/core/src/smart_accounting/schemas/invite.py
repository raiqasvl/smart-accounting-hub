# Invite + membership DTOs.
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .user import UserOut


class InviteCreateIn(BaseModel):
    role: int  # cannot be OWNER (0); validated in the service
    ttl_minutes: int = 1440


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    role: int
    token: str
    deep_link: str
    expires_at: datetime
    used_at: datetime | None = None


class MemberOut(BaseModel):
    user: UserOut
    role: int
    invited_at: datetime
    accepted_at: datetime | None = None
