"""Feature access control based on subscription tier."""

from fastapi import HTTPException
from models.user import User

# Which features each tier can access
TIER_FEATURES = {
    "free": {
        "screener", "basic_news", "watchlist_3",
    },
    "pro": {
        "screener", "basic_news", "watchlist_3",
        "full_pipeline", "schwab_connect", "trading_bot", "tax_engine",
        "zakat", "watchlist_50", "push_notifications", "telegram_alerts",
        "pdf_reports", "priority_support",
    },
    "managed": {
        "screener", "basic_news", "watchlist_3",
        "full_pipeline", "schwab_connect", "trading_bot", "tax_engine",
        "zakat", "watchlist_50", "push_notifications", "telegram_alerts",
        "pdf_reports", "priority_support",
        "human_review", "weekly_call", "dedicated_dm",
        "monthly_report", "tax_pdf", "vip_onboarding",
    },
}


def check_feature_access(user: User, feature: str) -> bool:
    """Raise 403 if the user's tier doesn't include this feature."""
    allowed = TIER_FEATURES.get(user.tier, TIER_FEATURES["free"])
    if feature not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Feature '{feature}' requires a higher subscription tier.",
        )
    return True
