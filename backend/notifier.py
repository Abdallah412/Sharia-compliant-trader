"""
Telegram Notification Module for Halal Trader Bot.
Sends trade alerts, compliance updates, tax warnings, daily summaries,
and zakat reminders via Telegram using python-telegram-bot v20+ (async).
"""

import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Callback data constants
CALLBACK_APPROVE = "trade_approve"
CALLBACK_REJECT = "trade_reject"
CALLBACK_DETAILS = "trade_details"

# Will be set externally by the orchestrator to execute approved trades
_trade_execution_callback = None


def set_trade_execution_callback(callback):
    """Register a callback function that executes an approved trade."""
    global _trade_execution_callback
    _trade_execution_callback = callback


async def _send_message(text: str, reply_markup=None) -> None:
    """Internal helper to send a message to the configured chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured — skipping notification.")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    async with app:
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


async def send_trade_alert(decision: dict) -> None:
    """
    Send an orchestrator trade decision as a Telegram alert with approval buttons.

    Expected decision keys:
        action, ticker, qty, price, total_value,
        sheikh_verdict, sheikh_summary,
        finance_signal, finance_confidence,
        tax_verdict, tax_recommendation,
        primary_reason
    """
    action = decision.get("action", "UNKNOWN")
    ticker = decision.get("ticker", "???")
    qty = decision.get("qty", 0)
    price = decision.get("price", 0.0)
    total_value = decision.get("total_value", qty * price)
    sheikh_verdict = decision.get("sheikh_verdict", "N/A")
    sheikh_summary = decision.get("sheikh_summary", "")
    finance_signal = decision.get("finance_signal", "N/A")
    finance_confidence = decision.get("finance_confidence", 0)
    tax_verdict = decision.get("tax_verdict", "N/A")
    tax_recommendation = decision.get("tax_recommendation", "")
    primary_reason = decision.get("primary_reason", "")

    text = (
        "\U0001f54c HALAL TRADER \u2014 TRADE SIGNAL\n"
        f"\U0001f4ca {action}: {ticker} \u00d7 {qty} @ ~${price:,.2f}\n"
        f"\U0001f4b0 Total: ~${total_value:,.2f}\n"
        f"\U0001f54c Sheikh: {sheikh_verdict} \u2014 {sheikh_summary}\n"
        f"\U0001f4c8 Finance: {finance_signal} ({finance_confidence}% confidence)\n"
        f"\U0001f9fe Tax: {tax_verdict} \u2014 {tax_recommendation}\n"
        f"\u26a1 Reason: {primary_reason}"
    )

    # Encode the ticker into callback data so the handler knows which trade
    callback_approve = f"{CALLBACK_APPROVE}:{ticker}"
    callback_reject = f"{CALLBACK_REJECT}:{ticker}"
    callback_details = f"{CALLBACK_DETAILS}:{ticker}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Approve Trade", callback_data=callback_approve),
                InlineKeyboardButton("Reject", callback_data=callback_reject),
                InlineKeyboardButton("View Details", callback_data=callback_details),
            ]
        ]
    )

    await _send_message(text, reply_markup=keyboard)
    logger.info("Trade alert sent for %s %s", action, ticker)


async def send_compliance_alert(ticker: str, old_status: str, new_status: str) -> None:
    """Alert when a holding's Shariah compliance status changes."""
    if new_status.lower() in ("non-compliant", "fail", "haram"):
        icon = "\u274c"
        urgency = "<b>ACTION REQUIRED</b>"
    else:
        icon = "\u2705"
        urgency = "Status Update"

    text = (
        f"{icon} <b>COMPLIANCE CHANGE</b> \u2014 {urgency}\n\n"
        f"Ticker: <b>{ticker}</b>\n"
        f"Previous: {old_status}\n"
        f"Current: <b>{new_status}</b>\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    )

    if new_status.lower() in ("non-compliant", "fail", "haram"):
        text += (
            "\u26a0\ufe0f This position may need to be liquidated to maintain "
            "Shariah compliance. Please review immediately."
        )

    await _send_message(text)
    logger.info("Compliance alert sent for %s: %s -> %s", ticker, old_status, new_status)


async def send_tax_warning(tax_data: dict) -> None:
    """Send a tax-related warning (e.g., wash sale risk, short-term gains)."""
    warning_type = tax_data.get("warning_type", "General Tax Warning")
    ticker = tax_data.get("ticker", "N/A")
    details = tax_data.get("details", "")
    estimated_impact = tax_data.get("estimated_impact", 0.0)
    recommendation = tax_data.get("recommendation", "")

    text = (
        f"\u26a0\ufe0f <b>TAX WARNING</b> \u2014 {warning_type}\n\n"
        f"Ticker: <b>{ticker}</b>\n"
        f"Details: {details}\n"
        f"Estimated Impact: <b>${estimated_impact:,.2f}</b>\n"
        f"Recommendation: {recommendation}\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    await _send_message(text)
    logger.info("Tax warning sent: %s for %s", warning_type, ticker)


async def send_daily_summary(portfolio: dict, trades: list) -> None:
    """Send end-of-day portfolio summary and trade recap."""
    total_value = portfolio.get("total_value", 0.0)
    cash = portfolio.get("cash", 0.0)
    day_pnl = portfolio.get("day_pnl", 0.0)
    total_return_pct = portfolio.get("total_return_pct", 0.0)
    positions = portfolio.get("positions", {})

    pnl_icon = "\U0001f7e2" if day_pnl >= 0 else "\U0001f534"

    text = (
        f"\U0001f4c5 <b>DAILY SUMMARY</b> \u2014 {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"\U0001f4b0 Portfolio Value: <b>${total_value:,.2f}</b>\n"
        f"\U0001f4b5 Cash: ${cash:,.2f}\n"
        f"{pnl_icon} Day P&amp;L: <b>${day_pnl:+,.2f}</b>\n"
        f"\U0001f4c8 Total Return: {total_return_pct:+.2f}%\n"
        f"\U0001f4ca Positions: {len(positions)}\n"
    )

    if trades:
        text += f"\n<b>Today's Trades ({len(trades)}):</b>\n"
        for t in trades:
            action = t.get("action", "?")
            ticker = t.get("ticker", "?")
            qty = t.get("qty", 0)
            price = t.get("price", 0.0)
            text += f"  \u2022 {action} {ticker} \u00d7 {qty} @ ${price:,.2f}\n"
    else:
        text += "\nNo trades executed today."

    if positions:
        text += "\n<b>Holdings:</b>\n"
        for ticker, pos in positions.items():
            qty = pos.get("qty", 0)
            avg = pos.get("avg_price", 0.0)
            text += f"  \u2022 {ticker}: {qty} shares @ ${avg:,.2f} avg\n"

    await _send_message(text)
    logger.info("Daily summary sent.")


async def send_zakat_reminder(zakat_data: dict) -> None:
    """Send a zakat calculation reminder."""
    total_zakatable = zakat_data.get("total_zakatable", 0.0)
    zakat_due = zakat_data.get("zakat_due", 0.0)
    nisab_threshold = zakat_data.get("nisab_threshold", 0.0)
    holdings_breakdown = zakat_data.get("holdings_breakdown", [])
    hijri_date = zakat_data.get("hijri_date", "")

    text = (
        f"\U0001f54c <b>ZAKAT REMINDER</b>\n\n"
        f"Hijri Date: {hijri_date}\n"
        f"Nisab Threshold: ${nisab_threshold:,.2f}\n"
        f"Total Zakatable Assets: <b>${total_zakatable:,.2f}</b>\n"
        f"Zakat Due (2.5%): <b>${zakat_due:,.2f}</b>\n"
    )

    if holdings_breakdown:
        text += "\n<b>Breakdown:</b>\n"
        for item in holdings_breakdown:
            name = item.get("name", "?")
            value = item.get("value", 0.0)
            text += f"  \u2022 {name}: ${value:,.2f}\n"

    text += (
        "\n<i>This is an estimate. Consult a scholar for your specific situation.</i>"
    )

    await _send_message(text)
    logger.info("Zakat reminder sent. Due: $%.2f", zakat_due)


async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Approve / Reject / View Details button presses from trade alerts."""
    query = update.callback_query
    await query.answer()

    # Security: verify the callback comes from the authorized chat
    if str(query.message.chat_id) != str(TELEGRAM_CHAT_ID):
        logger.warning(
            "Unauthorized callback from chat_id=%s (expected %s)",
            query.message.chat_id, TELEGRAM_CHAT_ID,
        )
        await query.edit_message_text(text="Unauthorized.")
        return

    data = query.data or ""
    parts = data.split(":", 1)
    action = parts[0]
    ticker = parts[1] if len(parts) > 1 else "UNKNOWN"

    # Validate ticker from callback data
    import re
    if not re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?(-[A-Z]{1,2})?$", ticker):
        logger.warning("Invalid ticker in callback data: %s", ticker[:20])
        await query.edit_message_text(text="Invalid ticker in callback.")
        return

    if action == CALLBACK_APPROVE:
        await query.edit_message_text(
            text=f"\u2705 <b>APPROVED</b> \u2014 Trade for {ticker} has been approved.\n"
            f"Executing...",
            parse_mode="HTML",
        )
        logger.info("Trade APPROVED for %s by user.", ticker)

        if _trade_execution_callback:
            try:
                await _trade_execution_callback(ticker)
            except Exception as e:
                logger.error("Trade execution failed for %s: %s", ticker, e)
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=f"\u274c Trade execution failed for {ticker}: {e}",
                )

    elif action == CALLBACK_REJECT:
        await query.edit_message_text(
            text=f"\u274c <b>REJECTED</b> \u2014 Trade for {ticker} has been rejected.",
            parse_mode="HTML",
        )
        logger.info("Trade REJECTED for %s by user.", ticker)

    elif action == CALLBACK_DETAILS:
        await query.edit_message_text(
            text=(
                f"\U0001f4cb <b>TRADE DETAILS</b> \u2014 {ticker}\n\n"
                f"Full analysis details are available in the dashboard."
            ),
            parse_mode="HTML",
        )
        logger.info("Details requested for %s.", ticker)

    else:
        logger.warning("Unknown callback action: %s", data)


def get_bot_application() -> Application:
    """Build and return a configured Application with the approval callback handler."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_approval_callback))
    return app


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        async def _test():
            # Test trade alert
            sample_decision = {
                "action": "BUY",
                "ticker": "MSFT",
                "qty": 5,
                "price": 420.50,
                "total_value": 2102.50,
                "sheikh_verdict": "HALAL",
                "sheikh_summary": "Passes all Shariah screens",
                "finance_signal": "BUY",
                "finance_confidence": 78,
                "tax_verdict": "OK",
                "tax_recommendation": "Long-term hold preferred",
                "primary_reason": "Golden cross on EMA20/50 + Shariah compliant",
            }
            print("Sending test trade alert...")
            await send_trade_alert(sample_decision)
            print("Test trade alert sent successfully.")

        asyncio.run(_test())
    else:
        print("Usage: python notifier.py test")
        print("  Sends a test trade alert to the configured Telegram chat.")
