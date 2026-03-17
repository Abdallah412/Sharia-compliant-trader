"""
Unified notification service — routes to push + Telegram + DB inbox.
Every notification is saved to the database AND sent via configured channels.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.notification import Notification
from notifications.push import send_push_to_user
from notifications.telegram import send_telegram

logger = logging.getLogger("notifications.service")

# Notification message templates
TEMPLATES = {
    "trade_signal": lambda p: (
        f"BUY {p['ticker']} x {p.get('quantity', '?')} @ ~${p.get('price', '?')} | "
        f"Sheikh {p.get('sheikh', '?')} | Finance {p.get('confidence', '?')}% | Tax {p.get('tax', '?')}",
        f"Trade Signal: {p['ticker']}",
    ),
    "compliance_alert": lambda p: (
        f"{p['ticker']} approaching {p.get('new_status', 'DOUBTFUL')} — {p.get('reason', 'review needed')}",
        f"Compliance Alert: {p['ticker']}",
    ),
    "tax_warning": lambda p: (
        f"Selling now = ${p.get('tax_now', 0)} tax. "
        f"Wait {p.get('days', '?')} days = ${p.get('tax_wait', 0)} (saves ${p.get('savings', 0)})",
        f"Tax Warning: {p.get('ticker', '')}",
    ),
    "stop_loss": lambda p: (
        f"Stop-loss triggered: {p['ticker']} sold @ ${p.get('price', '?')} (loss: ${p.get('loss', '?')})",
        f"Stop-Loss: {p['ticker']}",
    ),
    "daily_summary": lambda p: (
        f"Today: {p.get('pnl', '$0')} ({p.get('pnl_pct', '0%')}). "
        f"{p.get('trades', 0)} trades. Cash: ${p.get('cash', '?')}",
        "Daily Summary",
    ),
    "zakat_reminder": lambda p: (
        f"Zakat due: ${p.get('amount', '?')} on portfolio held {p.get('days', 354)}+ days",
        "Zakat Reminder",
    ),
    "schwab_reauth": lambda p: (
        f"Schwab token expires in {p.get('hours', 24)} hours. Re-authenticate now.",
        "Schwab Re-auth Required",
    ),
    "large_tax_alert": lambda p: (
        f"YTD gains: ${p.get('ytd_gains', '?')}. Estimated tax: ${p.get('tax', '?')}. Consider harvesting.",
        "Large Tax Alert",
    ),
}


async def notify_user(
    user: User,
    notification_type: str,
    payload: dict,
    db: AsyncSession,
):
    """
    Send notification via ALL configured channels:
    1. Firebase FCM push (iOS + Android)
    2. Telegram (Pro/Managed, if configured)
    3. In-app inbox (all tiers — saved to DB)
    """
    # Get formatted message
    template = TEMPLATES.get(notification_type)
    if template:
        body, title = template(payload)
    else:
        body = str(payload)
        title = notification_type.replace("_", " ").title()

    # 1. Save to in-app inbox (all tiers)
    notification = Notification(
        user_id=user.id,
        title=title,
        body=body,
        type=notification_type,
    )
    db.add(notification)
    await db.commit()

    # 2. Firebase push (all tiers with registered devices)
    try:
        await send_push_to_user(user.id, title, body, payload, db)
    except Exception as e:
        logger.warning("Push notification failed for user %s: %s", user.id, e)

    # 3. Telegram (Pro/Managed only, if configured)
    if user.telegram_chat_id and user.tier != "free":
        try:
            await send_telegram(user.telegram_chat_id, f"<b>{title}</b>\n{body}")
        except Exception as e:
            logger.warning("Telegram failed for user %s: %s", user.id, e)

    logger.info("Notification sent: user=%s type=%s", user.id, notification_type)
