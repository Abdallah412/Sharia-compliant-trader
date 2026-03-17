"""Screener API endpoint — Shariah compliance screening with AI rate limiting."""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.dependencies import get_current_user
from models.user import User
from models.screening_result import ScreeningResult
from middleware.ai_rate_limiter import check_ai_limit
from shariah_screener import ShariahScreener

router = APIRouter(prefix="/api", tags=["screener"])
logger = logging.getLogger("screener_api")

_screener = ShariahScreener()


@router.get("/screen/{ticker}")
async def screen_ticker(
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """On-demand Shariah screen. Rate-limited by tier."""
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    # Check rate limit
    await check_ai_limit(user, "screener", db)

    # Check cache (90-day validity)
    result = await db.execute(
        select(ScreeningResult)
        .where(
            ScreeningResult.ticker == ticker,
            ScreeningResult.user_id == user.id,
            ScreeningResult.expires_at > datetime.now(timezone.utc),
        )
        .order_by(ScreeningResult.screened_at.desc())
        .limit(1)
    )
    cached = result.scalar_one_or_none()
    if cached:
        return {"ticker": ticker, "cached": True, **cached.full_report}

    # Run screen
    screen_result = _screener.screen(ticker)

    report = {
        "verdict": "HALAL" if screen_result.compliant is True else ("HARAM" if screen_result.compliant is False else "DOUBTFUL"),
        "company_name": screen_result.company_name,
        "sector": screen_result.sector,
        "industry": screen_result.industry,
        "debt_ratio": screen_result.debt_ratio,
        "cash_ratio": screen_result.cash_ratio,
        "receivables_ratio": screen_result.receivables_ratio,
        "purification_pct": screen_result.purification_pct,
        "fail_reasons": screen_result.fail_reasons,
        "warnings": screen_result.warnings,
        "madhab_notes": screen_result.madhab_notes,
    }

    # Cache result
    db.add(ScreeningResult(
        user_id=user.id,
        ticker=ticker,
        verdict=report["verdict"],
        full_report=report,
        source="yfinance",
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    ))
    await db.commit()

    return {"ticker": ticker, "cached": False, **report}
