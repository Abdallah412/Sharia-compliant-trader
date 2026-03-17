"""Notification endpoints: in-app inbox, push token registration."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.dependencies import get_current_user
from models.user import User
from models.notification import Notification
from models.push_token import PushToken

router = APIRouter(prefix="/api", tags=["notifications"])


class PushTokenRequest(BaseModel):
    token: str
    platform: str  # ios|android|web


@router.get("/notifications")
async def get_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifs = result.scalars().all()
    return {
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "type": n.type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ],
        "unread_count": sum(1 for n in notifs if not n.is_read),
    }


@router.post("/notifications/read/{notification_id}")
async def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user.id)
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}


@router.post("/users/push-token")
async def save_push_token(
    body: PushTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.platform not in ("ios", "android", "web"):
        raise HTTPException(status_code=400, detail="Invalid platform")

    # Upsert: update if token exists, create otherwise
    result = await db.execute(
        select(PushToken).where(PushToken.token == body.token)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.user_id = user.id
        existing.platform = body.platform
        existing.last_seen = datetime.now(timezone.utc)
    else:
        db.add(PushToken(
            user_id=user.id,
            token=body.token,
            platform=body.platform,
        ))

    await db.commit()
    return {"status": "saved"}
