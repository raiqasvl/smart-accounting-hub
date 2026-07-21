# Unit + property tests for Telegram initData HMAC verification (DB-free).
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from smart_accounting.auth.initdata import verify_init_data
from smart_accounting.errors import InitDataExpired, InitDataInvalid

BOT_TOKEN = "123456:TEST-bot-token-for-initdata-signing"


def _sign(fields: dict[str, str], bot_token: str = BOT_TOKEN) -> str:
    """Build a correctly-signed initData query string from raw fields."""
    data_check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": computed})


def _valid_fields(auth_date: int | None = None) -> dict[str, str]:
    return {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAEabc",
        "user": json.dumps({"id": 555, "first_name": "Ada", "language_code": "en"}),
    }


def test_valid_payload_accepted() -> None:
    parsed = verify_init_data(_sign(_valid_fields()), BOT_TOKEN)
    assert parsed["user"]["id"] == 555
    assert parsed["user"]["first_name"] == "Ada"


def test_missing_hash_rejected() -> None:
    fields = _valid_fields()
    with pytest.raises(InitDataInvalid):
        verify_init_data(urlencode(fields), BOT_TOKEN)  # no hash appended


def test_tampered_hash_rejected() -> None:
    signed = _sign(_valid_fields())
    tampered = signed[:-1] + ("a" if signed[-1] != "a" else "b")
    with pytest.raises(InitDataInvalid):
        verify_init_data(tampered, BOT_TOKEN)


def test_tampered_field_rejected() -> None:
    fields = _valid_fields()
    signed = _sign(fields)
    # Re-sign nothing; mutate a field value in the query string.
    forged = signed.replace("first_name", "first_nyme")
    with pytest.raises(InitDataInvalid):
        verify_init_data(forged, BOT_TOKEN)


def test_wrong_bot_token_rejected() -> None:
    with pytest.raises(InitDataInvalid):
        verify_init_data(_sign(_valid_fields()), "999:some-other-bot-token")


def test_expired_auth_date_rejected() -> None:
    old = int(time.time()) - 90_000  # > 86400 default max age
    with pytest.raises(InitDataExpired):
        verify_init_data(_sign(_valid_fields(auth_date=old)), BOT_TOKEN)


def test_field_order_independent() -> None:
    # Reordering the query string must not affect verification (spec sorts before hashing).
    fields = _valid_fields()
    signed = _sign(fields)
    pairs = signed.split("&")
    reordered = "&".join(reversed(pairs))
    assert verify_init_data(reordered, BOT_TOKEN)["user"]["id"] == 555


_safe_text = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122), min_size=1, max_size=12
)


@settings(max_examples=60)
@given(query_id=_safe_text, first_name=_safe_text, uid=st.integers(min_value=1, max_value=10**12))
def test_property_signed_accepts_tampered_rejects(query_id: str, first_name: str, uid: int) -> None:
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": query_id,
        "user": json.dumps({"id": uid, "first_name": first_name}),
    }
    signed = _sign(fields)
    parsed = verify_init_data(signed, BOT_TOKEN)
    assert parsed["user"]["id"] == uid

    # Flip one hex char of the hash -> must reject.
    flipped = signed[:-1] + ("0" if signed[-1] != "0" else "1")
    with pytest.raises(InitDataInvalid):
        verify_init_data(flipped, BOT_TOKEN)
