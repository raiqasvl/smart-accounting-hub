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


# --- authorization / tenancy (M2) ---


class Forbidden(AppError):
    code = "forbidden"
    http_status = 403


class NotFound(AppError):
    code = "not_found"
    http_status = 404


class BookNotFound(NotFound):
    code = "book_not_found"


class NotAMember(AppError):
    code = "not_a_member"
    http_status = 403


class LastOwner(AppError):
    code = "last_owner"
    http_status = 409


# --- invites (M2) ---


class InviteInvalid(AppError):
    code = "invite_invalid"
    http_status = 404


class InviteExpired(AppError):
    code = "invite_expired"
    http_status = 410


class InviteAlreadyUsed(AppError):
    code = "invite_already_used"
    http_status = 409


class AlreadyMember(AppError):
    code = "already_member"
    http_status = 409


# --- accounts / currencies (M2) ---


class AccountInUse(AppError):
    code = "account_in_use"
    http_status = 409


class CurrencyUnknown(AppError):
    code = "currency_unknown"
    http_status = 422


class CurrencyExists(AppError):
    code = "currency_exists"
    http_status = 409


# --- transactions (M3) ---


class TransactionNotFound(NotFound):
    code = "transaction_not_found"


class AccountNotInBook(AppError):
    code = "account_not_in_book"
    http_status = 422


class AccountCurrencyMismatch(AppError):
    code = "account_currency_mismatch"
    http_status = 422


class InvalidAmount(AppError):
    code = "invalid_amount"
    http_status = 422


class InvalidCursor(AppError):
    code = "invalid_cursor"
    http_status = 422


class InvalidTransfer(AppError):
    code = "invalid_transfer"
    http_status = 422


# --- categories (M4) ---


class CategoryNotFound(NotFound):
    code = "category_not_found"


class CategoryHasChildren(AppError):
    code = "category_has_children"
    http_status = 409


class CategoryInUse(AppError):
    code = "category_in_use"
    http_status = 409


class InvalidCategoryParent(AppError):
    code = "invalid_category_parent"
    http_status = 422
