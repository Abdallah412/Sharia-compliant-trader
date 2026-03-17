"""
Halal Trading Bot — Scheduler
Runs recurring tasks using APScheduler:
  - Daily trading cycle (Mon–Fri 9:35 AM ET)
  - Daily summary (Mon–Fri 4:05 PM ET)
  - Weekly token check (Monday 8:00 AM ET)
  - Quarterly compliance rescreen (Jan, Apr, Jul, Oct 1st)
  - Annual Zakat reminder (March 1st)
"""

import os
import sys
import asyncio
import logging

import pytz
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

ET = pytz.timezone("America/New_York")

# ---------------------------------------------------------------------------
# Sibling module imports
# ---------------------------------------------------------------------------
try:
    from trading_bot import run_daily_cycle
except ImportError:
    logger.warning("trading_bot not found — daily cycle job will be a no-op")
    async def run_daily_cycle():
        logger.info("[NO-OP] trading_bot.run_daily_cycle not available")

try:
    from notifier import send_daily_summary, send_notification
except ImportError:
    logger.warning("notifier not found — notification jobs will be no-ops")
    async def send_daily_summary():
        logger.info("[NO-OP] notifier.send_daily_summary not available")
    async def send_notification(msg):
        logger.info("[NO-OP] notifier.send_notification: %s", msg)

try:
    from schwab_auth import get_token_age_days
except ImportError:
    logger.warning("schwab_auth not found — token check will be a no-op")
    def get_token_age_days():
        return -1

try:
    from shariah_screener import ShariahScreener
except ImportError:
    logger.warning("shariah_screener not found — compliance rescreen will be a no-op")
    ShariahScreener = None

try:
    from portfolio_manager import PortfolioManager
except ImportError:
    logger.warning("portfolio_manager not found — some scheduled tasks will be limited")
    PortfolioManager = None

try:
    from zakat_calculator import calculate_zakat, get_zakat_report
except ImportError:
    logger.warning("zakat_calculator not found — Zakat reminder will be a no-op")
    calculate_zakat = None
    get_zakat_report = None


# ---------------------------------------------------------------------------
# Scheduled job functions
# ---------------------------------------------------------------------------

async def job_daily_cycle():
    """Run the daily trading cycle at market open + 5 minutes."""
    logger.info("=== DAILY TRADING CYCLE START ===")
    try:
        if asyncio.iscoroutinefunction(run_daily_cycle):
            await run_daily_cycle()
        else:
            run_daily_cycle()
        logger.info("=== DAILY TRADING CYCLE COMPLETE ===")
    except Exception as exc:
        logger.error("Daily trading cycle failed: %s", exc, exc_info=True)


async def job_daily_summary():
    """Send end-of-day portfolio summary after market close."""
    logger.info("Generating daily summary...")
    try:
        if asyncio.iscoroutinefunction(send_daily_summary):
            await send_daily_summary()
        else:
            send_daily_summary()
        logger.info("Daily summary sent.")
    except Exception as exc:
        logger.error("Daily summary failed: %s", exc, exc_info=True)


async def job_weekly_token_check():
    """Check Schwab API token age and warn if near expiry."""
    logger.info("Checking Schwab API token age...")
    try:
        age = get_token_age_days()
        if age < 0:
            msg = "WARNING: Unable to determine Schwab token age."
        elif age >= 6:
            msg = (
                f"URGENT: Schwab API token is {age} days old and will expire soon! "
                "Please re-authenticate at https://127.0.0.1 callback."
            )
        elif age >= 5:
            msg = f"Schwab API token is {age} days old. Consider refreshing soon."
        else:
            msg = f"Schwab API token is {age} days old. OK."
            logger.info(msg)
            return

        logger.warning(msg)
        if asyncio.iscoroutinefunction(send_notification):
            await send_notification(msg)
        else:
            send_notification(msg)
    except Exception as exc:
        logger.error("Token check failed: %s", exc, exc_info=True)


async def job_quarterly_compliance_rescreen():
    """Re-screen all portfolio holdings for Shariah compliance."""
    logger.info("=== QUARTERLY COMPLIANCE RESCREEN ===")
    if ShariahScreener is None:
        logger.warning("ShariahScreener not available — skipping rescreen")
        return

    try:
        screener = ShariahScreener()

        # Get current holdings
        tickers = []
        if PortfolioManager is not None:
            try:
                pm = PortfolioManager()
                tickers = pm.get_tickers() if hasattr(pm, "get_tickers") else []
            except Exception:
                pass

        if not tickers:
            # Fallback: read from portfolio state
            from pathlib import Path
            import json
            state_path = Path(__file__).resolve().parent.parent / "data" / "portfolio_state.json"
            if state_path.exists():
                state = json.loads(state_path.read_text())
                tickers = list(state.get("holdings", {}).keys())

        if not tickers:
            logger.info("No holdings found to rescreen.")
            return

        results = screener.screen_portfolio(tickers)
        non_compliant = [r for r in results if r.compliant is False]
        doubtful = [r for r in results if r.compliant is None]

        summary_parts = [f"Rescreened {len(results)} holdings."]
        if non_compliant:
            names = ", ".join(r.ticker for r in non_compliant)
            summary_parts.append(f"NON-COMPLIANT: {names}")
        if doubtful:
            names = ", ".join(r.ticker for r in doubtful)
            summary_parts.append(f"DOUBTFUL: {names}")
        if not non_compliant and not doubtful:
            summary_parts.append("All holdings remain Shariah-compliant.")

        msg = " | ".join(summary_parts)
        logger.info(msg)
        if asyncio.iscoroutinefunction(send_notification):
            await send_notification(msg)
        else:
            send_notification(msg)

    except Exception as exc:
        logger.error("Quarterly compliance rescreen failed: %s", exc, exc_info=True)


async def job_annual_zakat_reminder():
    """Annual Zakat calculation and reminder on March 1st."""
    logger.info("=== ANNUAL ZAKAT REMINDER ===")
    try:
        if calculate_zakat is not None and get_zakat_report is not None:
            report = get_zakat_report()
            msg = (
                f"ZAKAT REMINDER: It is time to calculate and pay your annual Zakat. "
                f"Report: {report}"
            )
        else:
            msg = (
                "ZAKAT REMINDER: It is time to calculate and pay your annual Zakat. "
                "The zakat_calculator module is not installed — please calculate manually."
            )

        logger.info(msg)
        if asyncio.iscoroutinefunction(send_notification):
            await send_notification(msg)
        else:
            send_notification(msg)
    except Exception as exc:
        logger.error("Zakat reminder failed: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------

def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    scheduler = AsyncIOScheduler(timezone=ET)

    # Daily bot run — Mon-Fri 9:35 AM ET (5 min after market open)
    scheduler.add_job(
        job_daily_cycle,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=35, timezone=ET),
        id="daily_cycle",
        name="Daily Trading Cycle",
        misfire_grace_time=300,
    )

    # Daily summary — Mon-Fri 4:05 PM ET (5 min after market close)
    scheduler.add_job(
        job_daily_summary,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=5, timezone=ET),
        id="daily_summary",
        name="Daily Portfolio Summary",
        misfire_grace_time=300,
    )

    # Weekly token check — Monday 8:00 AM ET
    scheduler.add_job(
        job_weekly_token_check,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone=ET),
        id="weekly_token_check",
        name="Weekly Schwab Token Check",
        misfire_grace_time=3600,
    )

    # Quarterly compliance rescreen — 1st of Jan, Apr, Jul, Oct at 7:00 AM ET
    scheduler.add_job(
        job_quarterly_compliance_rescreen,
        CronTrigger(month="1,4,7,10", day=1, hour=7, minute=0, timezone=ET),
        id="quarterly_rescreen",
        name="Quarterly Shariah Compliance Rescreen",
        misfire_grace_time=86400,
    )

    # Annual Zakat reminder — March 1st at 8:00 AM ET
    scheduler.add_job(
        job_annual_zakat_reminder,
        CronTrigger(month=3, day=1, hour=8, minute=0, timezone=ET),
        id="annual_zakat",
        name="Annual Zakat Reminder",
        misfire_grace_time=86400,
    )

    return scheduler


# ---------------------------------------------------------------------------
# Main — run scheduler + API server together
# ---------------------------------------------------------------------------

async def main():
    """Start the scheduler and the FastAPI server in the same event loop."""
    import uvicorn

    api_port = int(os.getenv("API_PORT", "8000"))

    # Create and start the scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started with %d jobs.", len(scheduler.get_jobs()))
    for job in scheduler.get_jobs():
        logger.info("  [%s] %s — next run: %s", job.id, job.name, job.next_run_time)

    # Start uvicorn API server
    config = uvicorn.Config(
        "api_server:app",
        host="0.0.0.0",
        port=api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    logger.info("Starting API server on port %d", api_port)

    try:
        await server.serve()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())
