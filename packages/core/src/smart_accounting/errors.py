# Typed domain exceptions. The API renders these as the D24 envelope
# {"error": {"code", "params"}, "request_id"}; the bot maps them to Fluent text. Codes are
# language-agnostic (i18n lives in the presentation layers, never here).
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base for all domain errors. `code` is a stable machine string; `http_status` is how the
    API surfaces it. `params` carries structured context for i18n interpolation."""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params: dict[str, Any] = params or {}
        super().__init__(self.code)


class InitDataInvalid(AppError):
    code = "init_data_invalid"
    http_status = 403


class InitDataExpired(AppError):
    code = "init_data_expired"
    http_status = 403


class JwtInvalid(AppError):
    code = "jwt_invalid"
    http_status = 401


class JwtExpired(AppError):
    code = "jwt_expired"
    http_status = 401
