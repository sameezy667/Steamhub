"""
@file security.py
@description Authentication, HMAC nonce generation, JWT session tokens, and rate limiters
@module backend/src
"""

from datetime import datetime, timedelta, timezone
import hmac
import hashlib
import secrets
from typing import Annotated
import uuid
from fastapi import Cookie, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.src.config import settings
from backend.src.database import get_db
from backend.src.models import User

# SlowAPI rate limiter configured by remote IP
limiter = Limiter(key_func=get_remote_address)


def create_openid_nonce() -> tuple[str, str]:
    """
    Generates a cryptographically secure random nonce and its HMAC signature.
    Returns (raw_nonce, signed_token).
    """
    raw_nonce = secrets.token_hex(24)
    sig = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        raw_nonce.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    signed_token = f"{raw_nonce}.{sig}"
    return raw_nonce, signed_token


def verify_openid_nonce(signed_token: str, received_nonce: str) -> bool:
    """
    Verifies that the received nonce matches the signed token from the pre-auth session cookie.
    Prevents CSRF and OpenID session fixation attacks.
    """
    if not signed_token or not received_nonce:
        return False

    parts = signed_token.split(".")
    if len(parts) != 2:
        return False

    cookie_nonce, cookie_sig = parts
    if not hmac.compare_digest(cookie_nonce, received_nonce):
        return False

    expected_sig = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        cookie_nonce.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, cookie_sig)


def create_access_token(user_id: uuid.UUID) -> str:
    """
    Generates an encrypted JWT session token for the user.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRATION_DAYS)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_access_token(token: str) -> uuid.UUID:
    """
    Decodes and validates a JWT session token.
    Raises HTTPException 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token: missing subject",
            )
        return uuid.UUID(user_id_str)
    except (JWTError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
        ) from err


async def get_current_user_optional(
    steamhub_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Optional user dependency. Returns User instance or None if not authenticated.
    """
    if not steamhub_session:
        return None
    try:
        user_id = verify_access_token(steamhub_session)
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except HTTPException:
        return None


async def get_current_user(
    steamhub_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Strict user dependency. Requires valid HttpOnly session cookie.
    Raises 401 Unauthorized if not authenticated.
    """
    if not steamhub_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in with Steam.",
        )

    user_id = verify_access_token(steamhub_session)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for this session.",
        )

    return user
