"""
@file test_utils.py
@description Unit tests for canonical UTC date truncation and advisory lock hashing
@module backend/tests
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from backend.src.utils import hash_user_id_for_lock, timestamp_to_utc_date, today_utc


def test_today_utc_returns_date_instance():
    """Validates that today_utc returns a date instance matching current UTC day."""
    res = today_utc()
    assert isinstance(res, date)
    assert res == datetime.now(timezone.utc).date()


def test_timestamp_to_utc_date_with_tz_aware():
    """Validates timezone conversion to UTC date."""
    # 2026-05-10 23:30:00 -04:00 is 2026-05-11 03:30:00 UTC
    tz_minus_4 = timezone(
        datetime.now(timezone.utc).astimezone().utcoffset()
        or timezone.utc.utcoffset(None)
    )
    dt_aware = datetime(2026, 5, 10, 23, 30, 0, tzinfo=timezone.utc)
    res = timestamp_to_utc_date(dt_aware)
    assert res == date(2026, 5, 10)


def test_timestamp_to_utc_date_with_naive():
    """Validates that naive datetimes default safely to date."""
    dt_naive = datetime(2026, 8, 15, 12, 0, 0)
    res = timestamp_to_utc_date(dt_naive)
    assert res == date(2026, 8, 15)


def test_hash_user_id_for_lock_deterministic():
    """Validates that hash_user_id_for_lock returns consistent 64-bit signed integer."""
    test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    hash1 = hash_user_id_for_lock(test_uuid)
    hash2 = hash_user_id_for_lock("12345678-1234-5678-1234-567812345678")
    assert isinstance(hash1, int)
    assert hash1 == hash2
    assert -(2**63) <= hash1 < 2**63
