"""
@file utils.py
@description Canonical shared UTC date truncation and hashing utilities
@module backend/src
"""

from datetime import date, datetime, timezone
import hashlib
from uuid import UUID


def today_utc() -> date:
    """
    Returns the current date in UTC.
    Always use this canonical function across poller, backfill, and API queries.
    """
    return datetime.now(timezone.utc).date()


def timestamp_to_utc_date(dt: datetime) -> date:
    """
    Converts any datetime (tz-aware or tz-naive) to a UTC date object.
    If tz-naive, assumes UTC.
    """
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(timezone.utc).date()


def hash_user_id_for_lock(user_id: UUID | str) -> int:
    """
    Hashes a UUID or string user_id into a signed 64-bit integer suitable
    for PostgreSQL advisory locks (pg_try_advisory_xact_lock(bigint)).
    """
    raw_str = str(user_id).strip()
    # MD5 digest gives 16 bytes, take first 8 bytes for 64-bit integer
    digest = hashlib.md5(raw_str.encode("utf-8")).digest()[:8]
    val = int.from_bytes(digest, byteorder="big", signed=True)
    return val
