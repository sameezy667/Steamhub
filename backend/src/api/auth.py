"""
@file auth.py
@description Authentication endpoints for Steam OpenID login, callback, and session management
@module backend/src/api
"""

import logging
from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.config import settings
from backend.src.database import get_db
from backend.src.models import User
from backend.src.schemas import UserRead
from backend.src.security import (
    create_access_token,
    create_openid_nonce,
    get_current_user,
    verify_openid_nonce,
)
from backend.src.steam_client import (
    build_openid_login_url,
    get_player_summaries,
    verify_openid_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.get("/auth/steam/login")
async def steam_login() -> Response:
    """
    Initiates Steam OpenID 2.0 login.
    Issues a signed CSRF nonce in an HttpOnly cookie and redirects to Steam.
    """
    raw_nonce, signed_token = create_openid_nonce()
    redirect_url = build_openid_login_url(raw_nonce)

    response = RedirectResponse(
        url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
    response.set_cookie(
        key=settings.NONCE_COOKIE_NAME,
        value=signed_token,
        max_age=300,  # 5 minutes
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/auth/steam/callback")
async def steam_callback(
    request: Request,
    state: str | None = None,
    steamhub_openid_nonce: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Handles Steam OpenID 2.0 callback.
    Validates CSRF state nonce, validates OpenID signature against Steam,
    upserts User record, sets HttpOnly session cookie, and redirects to frontend.
    """
    # 1. Verify CSRF nonce
    if not steamhub_openid_nonce or not state:
        logger.warning(
            "Steam callback rejected: missing nonce cookie or state parameter"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: missing CSRF token. Please restart login.",
        )

    if not verify_openid_nonce(steamhub_openid_nonce, state):
        logger.warning("Steam callback rejected: invalid or tampered CSRF nonce")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: invalid CSRF token.",
        )

    # 2. Verify OpenID signature against Steam
    query_params = dict(request.query_params)
    steam_id64 = await verify_openid_response(query_params)

    # 3. Fetch player summaries from Steam Web API
    summaries = await get_player_summaries([steam_id64])
    persona_name = ""
    avatar_url = ""
    visibility_state: int | None = None

    if summaries:
        player = summaries[0]
        persona_name = player.get("personaname", "")
        avatar_url = player.get("avatarfull", "")
        visibility_state = player.get("communityvisibilitystate")

    # 4. Upsert User in database
    result = await db.execute(select(User).where(User.steam_id64 == steam_id64))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            steam_id64=steam_id64,
            persona_name=persona_name,
            avatar_url=avatar_url,
            profile_visibility_state=visibility_state,
        )
        db.add(user)
    else:
        user.persona_name = persona_name or user.persona_name
        user.avatar_url = avatar_url or user.avatar_url
        user.profile_visibility_state = visibility_state

    await db.commit()
    await db.refresh(user)

    # 5. Issue session JWT cookie and clear nonce cookie
    access_token = create_access_token(user.id)
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard?user_id={user.id}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )

    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=access_token,
        max_age=settings.JWT_EXPIRATION_DAYS * 86400,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(key=settings.NONCE_COOKIE_NAME, path="/")

    return response


@router.get("/api/auth/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns profile information for the authenticated user session.
    """
    return current_user


@router.post("/api/auth/logout")
async def logout(response: Response) -> dict[str, bool]:
    """
    Terminates user session by clearing the HttpOnly cookie.
    """
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")
    return {"success": True}
