"""
@file test_auth.py
@description Unit and integration tests for Steam OpenID CSRF protection, nonce verification, and JWT security
@module backend/tests
"""

import re
import uuid
import pytest
from fastapi import HTTPException
from backend.src.security import (
    create_access_token,
    create_openid_nonce,
    verify_access_token,
    verify_openid_nonce,
)
from backend.src.steam_client import STEAM_ID_REGEX, build_openid_login_url


def test_openid_nonce_generation_and_verification():
    """Validates that valid HMAC nonce pairs pass verification."""
    raw_nonce, signed_token = create_openid_nonce()
    assert verify_openid_nonce(signed_token, raw_nonce) is True


def test_openid_nonce_tampering_rejected():
    """Validates that altered nonces or signatures are strictly rejected."""
    raw_nonce, signed_token = create_openid_nonce()
    # Tamper with raw nonce
    assert verify_openid_nonce(signed_token, raw_nonce + "a") is False
    # Tamper with signature
    parts = signed_token.split(".")
    tampered_token = f"{parts[0]}.badsignature12345"
    assert verify_openid_nonce(tampered_token, raw_nonce) is False
    # Empty inputs
    assert verify_openid_nonce("", raw_nonce) is False
    assert verify_openid_nonce(signed_token, "") is False


def test_steam_claimed_id_regex_validation():
    """Validates strict 17-digit Steam ID format parsing."""
    valid_id = "https://steamcommunity.com/openid/id/76561198000000001"
    match = STEAM_ID_REGEX.match(valid_id)
    assert match is not None
    assert match.group(1) == "76561198000000001"

    invalid_ids = [
        "https://steamcommunity.com/openid/id/123",  # too short
        "https://evil.com/openid/id/76561198000000001",  # wrong domain
        "https://steamcommunity.com/openid/id/76561198000000001/extra",
        "javascript:alert(1)",
    ]
    for inv in invalid_ids:
        assert STEAM_ID_REGEX.match(inv) is None


def test_jwt_create_and_verify():
    """Validates JWT creation and decoding round-trip."""
    test_uid = uuid.uuid4()
    token = create_access_token(test_uid)
    assert isinstance(token, str)

    decoded_uid = verify_access_token(token)
    assert decoded_uid == test_uid


def test_jwt_invalid_token_raises_401():
    """Validates that invalid JWT raises 401 Unauthorized."""
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token("invalid.jwt.token")
    assert exc_info.value.status_code == 401


def test_build_openid_login_url():
    """Validates OpenID login redirect URL construction."""
    raw_nonce = "abc123nonce"
    url = build_openid_login_url(raw_nonce)
    assert "https://steamcommunity.com/openid/login" in url
    assert "checkid_setup" in url
    assert "state%3Dabc123nonce" in url or "state=abc123nonce" in url
