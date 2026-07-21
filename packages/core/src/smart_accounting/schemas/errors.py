# ErrorOut — the D24 error envelope wire shape.
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    params: dict[str, Any] = Field(default_factory=dict)


class ErrorOut(BaseModel):
    error: ErrorDetail
    request_id: str
