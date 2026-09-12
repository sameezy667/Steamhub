"""
@file backfill.py
@description Standalone snapshot-to-daily_delta rebuild script for validating and recomputing diff logic
@module backend/src
"""

import argparse
import asyncio
from collections import defaultdict
from datetime import date
import logging
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.database import AsyncSessionLocal
from backend.src.models import DailyDelta, Snapshot, User
from backend.src.poller import upsert_daily_delta
from backend.src.utils import timestamp_to_utc_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("steamhub.backfill")


async def recompute_daily_deltas_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Rebuilds daily_deltas for a specific user from raw snapshots.
    Guarantees parity with incremental polling by using canonical timestamp_to_utc_date.
    """
    logger.info("Recomputing daily deltas for user: %s", user_id)

    # 1. Fetch all snapshots for this user in chronological order
    result = await session.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.app_id, Snapshot.captured_at.asc())
    )
    snapshots = result.scalars().all()

    # Group snapshots by app_id
    by_app: dict[int, list[Snapshot]] = defaultdict(list)
    for snap in snapshots:
        by_app[snap.app_id].append(snap)

    computed_deltas: dict[tuple[uuid.UUID, int, date], int] = defaultdict(int)
    total_snapshots_processed = 0
    total_deltas_generated = 0

    for app_id, app_snaps in by_app.items():
        if not app_snaps:
            continue

        prev_snap: Snapshot | None = None
        for current_snap in app_snaps:
            total_snapshots_processed += 1
            if prev_snap is None:
                # First observation seeds baseline
                prev_snap = current_snap
                continue

            delta = (
                current_snap.playtime_forever_minutes
                - prev_snap.playtime_forever_minutes
            )
            if delta > 0:
                play_date = timestamp_to_utc_date(current_snap.captured_at)
                computed_deltas[(user_id, app_id, play_date)] += delta
                total_deltas_generated += 1
            elif delta < 0:
                logger.warning(
                    "Backfill encountered negative delta for user %s, app %d (%d -> %d)",
                    user_id,
                    app_id,
                    prev_snap.playtime_forever_minutes,
                    current_snap.playtime_forever_minutes,
                )

            prev_snap = current_snap

    if not dry_run:
        # Delete existing daily_deltas for this user
        await session.execute(delete(DailyDelta).where(DailyDelta.user_id == user_id))

        # Insert recomputed deltas
        for (u_id, a_id, p_date), minutes in computed_deltas.items():
            await upsert_daily_delta(session, u_id, a_id, p_date, minutes)

        await session.commit()
        logger.info(
            "Backfill committed for user %s: %d days/apps updated.",
            user_id,
            len(computed_deltas),
        )
    else:
        logger.info(
            "[DRY RUN] Backfill calculated %d delta rows across %d snapshots.",
            len(computed_deltas),
            total_snapshots_processed,
        )

    return {
        "snapshots_processed": total_snapshots_processed,
        "deltas_generated": total_deltas_generated,
        "delta_rows": len(computed_deltas),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild daily_deltas table from raw immutable snapshots."
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Specific user UUID to rebuild (optional). If omitted, rebuilds all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate deltas without writing to database.",
    )
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        if args.user_id:
            user_uuid = uuid.UUID(args.user_id)
            stats = await recompute_daily_deltas_for_user(
                session, user_uuid, dry_run=args.dry_run
            )
            print(f"Result for user {args.user_id}: {stats}")
        else:
            result = await session.execute(select(User.id))
            user_ids = result.scalars().all()
            print(f"Found {len(user_ids)} users to backfill.")
            for u_id in user_ids:
                await recompute_daily_deltas_for_user(
                    session, u_id, dry_run=args.dry_run
                )
            print("Backfill completed successfully for all users.")


if __name__ == "__main__":
    asyncio.run(main())
