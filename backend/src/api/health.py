"""
@file health.py
@description Health check and system capacity endpoints
@module backend/src/api
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.config import settings
from backend.src.database import get_db
from backend.src.models import User
from backend.src.schemas import HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthStatus)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthStatus:
    """
    Returns system health status, DB connectivity, and Steam API capacity metrics.
    """
    db_connected = False
    registered_users = 0

    try:
        await db.execute(text("SELECT 1"))
        db_connected = True
        user_count_res = await db.execute(select(func.count(User.id)))
        registered_users = user_count_res.scalar() or 0
    except Exception as err:
        logger.error("Health check DB query failed: %s", err)

    max_users = settings.max_supported_users
    headroom = max(
        0.0,
        ((max_users - registered_users) / max(1, max_users)) * 100.0,
    )

    return HealthStatus(
        status="healthy" if db_connected else "degraded",
        environment=settings.ENVIRONMENT,
        database_connected=db_connected,
        steam_api_quota_daily=settings.STEAM_DAILY_QUOTA,
        max_supported_users=max_users,
        registered_users_count=registered_users,
        quota_headroom_percent=round(headroom, 2),
    )
