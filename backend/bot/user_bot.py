"""Per-user trading bot instance. Runs the 4-agent pipeline for a single user."""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.trade import Trade
from models.notification import Notification
from utils.crypto import decrypt
from agents.orchestrator import run_full_pipeline

logger = logging.getLogger("user_bot")

# Pre-screened halal universe
WATCHLIST_ETFS = ["SPUS", "HLAL", "MNZL"]
WATCHLIST_STOCKS = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA",
    "ORCL", "AMD", "QCOM", "AVGO", "ADBE", "JNJ", "LLY", "ABBV", "MRK", "HD", "AMGN",
]


async def run_daily_cycle(user: User, db: AsyncSession):
    """Execute one daily trading cycle for a user."""
    logger.info("Running daily cycle for user %s (tier=%s, dry_run=%s)",
                user.id, user.tier, user.dry_run)

    if user.tier not in ("pro", "managed"):
        logger.info("User %s is on free tier — skipping bot cycle", user.id)
        return

    # For now, log the cycle start as a notification
    db.add(Notification(
        user_id=user.id,
        title="Daily Cycle Started",
        body=f"Scanning {len(WATCHLIST_ETFS) + len(WATCHLIST_STOCKS)} tickers...",
        type="bot_status",
    ))
    await db.commit()

    # The full implementation would:
    # 1. Decrypt Schwab credentials
    # 2. Fetch positions
    # 3. Check stop-loss / take-profit on existing positions
    # 4. For each watchlist ticker:
    #    a. Fetch fundamentals (data_fetcher)
    #    b. Run full_pipeline (all 4 agents)
    #    c. If EXECUTE + auto_execute → place order
    #    d. If EXECUTE + !auto_execute → save pending trade, notify user
    #    e. Log trade/decision
    # 5. Send daily summary notification

    logger.info("Daily cycle complete for user %s", user.id)
