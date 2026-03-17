"""Firebase Cloud Messaging push notifications."""

import json
import logging

from config import FIREBASE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger("push_notifications")

_firebase_initialized = False


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    if not FIREBASE_SERVICE_ACCOUNT_JSON:
        logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not set — push notifications disabled")
        return

    import firebase_admin
    from firebase_admin import credentials

    cred_dict = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    _firebase_initialized = True


async def send_push(token: str, title: str, body: str, data: dict | None = None):
    """Send a push notification via FCM."""
    _init_firebase()
    if not _firebase_initialized:
        logger.debug("Firebase not initialized, skipping push")
        return

    from firebase_admin import messaging

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        token=token,
    )

    try:
        messaging.send(message)
        logger.info("Push sent to token %s...", token[:20])
    except Exception as e:
        logger.error("Push notification failed: %s", e)


async def send_push_to_user(user_id: str, title: str, body: str,
                             data: dict | None = None, db=None):
    """Send push to all registered devices for a user."""
    if not db:
        return

    from sqlalchemy import select
    from models.push_token import PushToken

    result = await db.execute(
        select(PushToken).where(PushToken.user_id == user_id)
    )
    tokens = result.scalars().all()

    for pt in tokens:
        await send_push(pt.token, title, body, data)
