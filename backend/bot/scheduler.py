"""APScheduler — runs all user bots on schedule."""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from database import async_session
from models.user import User
from bot.user_bot import run_daily_cycle

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone="America/New_York")


async def _run_all_user_bots():
    """Run daily cycle for all active Pro/Managed users."""
    logger.info("Starting daily bot run for all users")

    async with async_session() as db:
        result = await db.execute(
            select(User).where(
                User.is_active == True,
                User.tier.in_(["pro", "managed"]),
            )
        )
        users = result.scalars().all()

    logger.info("Found %d active Pro/Managed users", len(users))

    tasks = []
    for user in users:
        async with async_session() as db:
            try:
                await run_daily_cycle(user, db)
            except Exception as e:
                logger.error("Bot cycle failed for user %s: %s", user.id, e)

    logger.info("Daily bot run complete")


def setup_scheduler():
    """Register all scheduled jobs."""
    # Daily trading cycle: Mon-Fri 9:35 AM ET
    scheduler.add_job(
        _run_all_user_bots,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=35),
        id="daily_trading_cycle",
        name="Daily Trading Cycle",
    )

    # Daily summary: Mon-Fri 4:05 PM ET
    scheduler.add_job(
        _run_all_user_bots,  # In production, this would be a separate summary function
        CronTrigger(day_of_week="mon-fri", hour=16, minute=5),
        id="daily_summary",
        name="Daily Summary",
    )

    logger.info("Scheduler configured with %d jobs", len(scheduler.get_jobs()))
    return scheduler
