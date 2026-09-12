"""
@file scheduler.py
@description APScheduler background task runner for periodic Steam profile polling
@module backend/src
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.src.config import settings
from backend.src.poller import poll_all_active_users

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """
    Initializes and starts the APScheduler instance for the Steam polling cron job.
    """
    if not scheduler.running:
        trigger = IntervalTrigger(minutes=settings.POLL_INTERVAL_MINUTES)
        scheduler.add_job(
            poll_all_active_users,
            trigger=trigger,
            id="steam_batch_poller",
            name="Periodic Steam Playtime Poller",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        scheduler.start()
        logger.info(
            "APScheduler started with interval %d minutes.",
            settings.POLL_INTERVAL_MINUTES,
        )


def stop_scheduler() -> None:
    """
    Gracefully shuts down the background scheduler.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
