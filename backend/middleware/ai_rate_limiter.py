"""Per-tier AI rate limiting. Enforced server-side, not just UI."""

from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.token_usage import TokenUsage

AI_LIMITS = {
    "free": {
        "screener_calls_per_day": 5,
        "full_pipeline_calls_per_day": 0,
        "model_allowed": "claude-haiku-4-5-20251001",
    },
    "pro": {
        "screener_calls_per_day": -1,       # Unlimited
        "full_pipeline_calls_per_day": 20,
        "model_allowed": "claude-sonnet-4-6",
    },
    "managed": {
        "screener_calls_per_day": -1,
        "full_pipeline_calls_per_day": -1,
        "model_allowed": "claude-sonnet-4-6",
    },
}


async def get_daily_usage_count(user_id: str, feature: str, db: AsyncSession) -> int:
    """Count today's AI calls for a user+feature."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(TokenUsage.id))
        .where(TokenUsage.user_id == user_id)
        .where(TokenUsage.feature == feature)
        .where(TokenUsage.created_at >= today_start)
    )
    return result.scalar() or 0


async def check_ai_limit(user: User, feature: str, db: AsyncSession) -> bool:
    """Returns True if within limits. Raises 429 if exceeded."""
    limits = AI_LIMITS.get(user.tier, AI_LIMITS["free"])
    daily_limit = limits.get(f"{feature}_calls_per_day", 0)

    if daily_limit == -1:
        return True

    today_count = await get_daily_usage_count(user.id, feature, db)
    if today_count >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit of {daily_limit} {feature} calls reached. Upgrade for more.",
        )
    return True


def get_allowed_model(tier: str) -> str:
    """Return the best model allowed for a given tier."""
    return AI_LIMITS.get(tier, AI_LIMITS["free"])["model_allowed"]
