# Telegram WebApp initData HMAC verification.
# https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl

from smart_accounting.errors import InitDataExpired, InitDataInvalid


def verify_init_data(
    init_data: str, bot_token: str, max_age_seconds: int = 86400
) -> dict[str, Any]:
    """Verify a Telegram Mini-App `initData` string against the bot token.

    Raises InitDataInvalid on a missing/bad hash or malformed payload, InitDataExpired when
    `auth_date` is older than `max_age_seconds`. Returns the parsed fields with `user` decoded
    from its JSON string.
    """
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise InitDataInvalid({"reason": "missing_hash"})

    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataInvalid({"reason": "bad_hash"})

    try:
        auth_date = int(data.get("auth_date", "0"))
    except ValueError:
        raise InitDataInvalid({"reason": "bad_auth_date"}) from None
    if auth_date <= 0 or (int(time.time()) - auth_date) > max_age_seconds:
        raise InitDataExpired({"reason": "auth_date_expired"})

    result: dict[str, Any] = dict(data)
    if "user" in data:
        try:
            result["user"] = json.loads(data["user"])
        except json.JSONDecodeError:
            raise InitDataInvalid({"reason": "bad_user_json"}) from None
    return result
