"""
@file steam_client.py
@description Steam Web API client and OpenID 2.0 authentication verification
@module backend/src
"""

import logging
import re
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException, status
from backend.src.config import settings

logger = logging.getLogger(__name__)

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
STEAM_API_BASE_URL = "https://api.steampowered.com"
STEAM_ID_REGEX = re.compile(r"^https:\/\/steamcommunity\.com\/openid\/id\/(\d{17})$")


def build_openid_login_url(state_nonce: str) -> str:
    """
    Constructs the Steam OpenID 2.0 redirect URL including the CSRF state nonce.
    """
    return_to = f"{settings.STEAM_OPENID_RETURN_TO}?state={state_nonce}"
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": settings.STEAM_OPENID_REALM,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return f"{STEAM_OPENID_URL}?{urlencode(params)}"


async def verify_openid_response(query_params: dict[str, str]) -> str:
    """
    Verifies OpenID 2.0 response parameters against Steam's authentication server.
    Validates claimed_id structure and returns verified 17-digit steam_id64.
    """
    claimed_id = query_params.get("openid.claimed_id", "")
    match = STEAM_ID_REGEX.match(claimed_id)
    if not match:
        logger.warning(
            "OpenID callback received invalid claimed_id format: %s", claimed_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Steam OpenID claimed identity format.",
        )

    steam_id64 = match.group(1)

    # Build verification payload
    payload: dict[str, str] = {}
    for k, v in query_params.items():
        if k.startswith("openid."):
            payload[k] = v

    payload["openid.mode"] = "check_authentication"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(STEAM_OPENID_URL, data=payload)
        if response.status_code != 200:
            logger.error(
                "Steam OpenID verification HTTP failed: status %d, body: %s",
                response.status_code,
                response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to communicate with Steam OpenID server.",
            )

        response_text = response.text
        if "is_valid:true" not in response_text:
            logger.warning("Steam OpenID verification rejected: %s", response_text)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Steam OpenID signature verification failed.",
            )

    return steam_id64


async def get_player_summaries(steam_ids: list[str]) -> list[dict]:
    """
    Calls ISteamUser/GetPlayerSummaries to fetch persona details and profile visibility.
    """
    if not steam_ids:
        return []

    url = f"{STEAM_API_BASE_URL}/ISteamUser/GetPlayerSummaries/v0002/"
    params = {
        "key": settings.STEAM_API_KEY,
        "steamids": ",".join(steam_ids),
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
        if response.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Steam API rate limit exceeded.",
                headers={"Retry-After": "60"},
            )
        if response.status_code != 200:
            logger.error(
                "GetPlayerSummaries failed with status %d: %s",
                response.status_code,
                response.text,
            )
            return []

        data = response.json()
        return data.get("response", {}).get("players", [])


async def get_owned_games(steam_id64: str) -> list[dict]:
    """
    Calls IPlayerService/GetOwnedGames to fetch owned games and lifetime playtime.
    """
    url = f"{STEAM_API_BASE_URL}/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": settings.STEAM_API_KEY,
        "steamid": steam_id64,
        "include_appinfo": 1,
        "include_played_free_games": 1,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)
        if response.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Steam API rate limit exceeded.",
                headers={"Retry-After": "60"},
            )
        if response.status_code != 200:
            logger.error(
                "GetOwnedGames failed for %s with status %d: %s",
                steam_id64,
                response.status_code,
                response.text,
            )
            return []

        data = response.json()
        return data.get("response", {}).get("games", [])
