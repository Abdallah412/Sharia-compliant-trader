"""Telegram notification sender."""

import logging
import os

import requests

logger = logging.getLogger("notifications.telegram")


async def send_telegram(chat_id: str, text: str, parse_mode: str = "HTML"):
    """Send a Telegram message to a user's chat."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        logger.debug("Telegram not configured, skipping")
        return

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Telegram send failed: %s", resp.text)
    except Exception as e:
        logger.error("Telegram error: %s", e)


async def send_telegram_with_buttons(chat_id: str, text: str, buttons: list[list[dict]]):
    """Send message with inline keyboard buttons (Approve/Reject)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": buttons},
            },
            timeout=10,
        )
    except Exception as e:
        logger.error("Telegram buttons error: %s", e)
