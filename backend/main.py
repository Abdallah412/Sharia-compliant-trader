"""
Halal Trader — FastAPI Main Application
Multi-tenant SaaS backend with auth, payments, AI pipeline, and trading bot.
"""

import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import CORS_ORIGINS, API_PORT, API_HOST, ENVIRONMENT
from database import get_db, init_db

# Routers
from auth.router import router as auth_router
from payments.router import router as payments_router
from notifications.router import router as notifications_router
from screener.router import router as screener_router
from auth.dependencies import get_current_user, require_tier
from models.user import User

# New modules
from data.fetcher import get_current_price, get_price_history
from data.news import score_sentiment
from bot.signals import calculate_ema, detect_signal
from tax.zakat import calculate_zakat

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# Ticker validation
TICKER_REGEX = re.compile(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?(-[A-Z]{1,2})?$")


def _validate_ticker(ticker: str) -> str:
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10 or not TICKER_REGEX.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")
    return ticker


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Halal Trader API...")
    await init_db()

    if ENVIRONMENT == "production":
        try:
            from bot.scheduler import setup_scheduler
            sched = setup_scheduler()
            sched.start()
            logger.info("Scheduler started")
        except Exception as e:
            logger.warning("Scheduler failed to start: %s", e)

    yield
    logger.info("Shutting down Halal Trader API")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Halal Trader API",
    description="Sharia-compliant automated investment platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Register routers
app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(notifications_router)
app.include_router(screener_router)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ===========================================================================
# PORTFOLIO (Pro+)
# ===========================================================================
@app.get("/api/portfolio")
async def get_portfolio(user: User = Depends(require_tier("pro", "managed"))):
    return {
        "total_value": 0, "cash": 0, "day_pnl": 0, "total_return_pct": 0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/holdings")
async def get_holdings(user: User = Depends(require_tier("pro", "managed"))):
    return {"holdings": [], "count": 0}


# ===========================================================================
# TRADES (Pro+)
# ===========================================================================
@app.get("/api/trades")
async def get_trades(
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    from models.trade import Trade
    result = await db.execute(
        select(Trade).where(Trade.user_id == user.id)
        .order_by(Trade.executed_at.desc()).limit(100)
    )
    trades = result.scalars().all()
    return {
        "trades": [
            {"id": t.id, "ticker": t.ticker, "action": t.action,
             "quantity": t.quantity, "price": t.price, "total_value": t.total_value,
             "dry_run": t.dry_run, "sheikh_verdict": t.sheikh_verdict,
             "executed_at": t.executed_at.isoformat()}
            for t in trades
        ],
        "count": len(trades),
    }


@app.post("/api/trades/{trade_id}/approve")
async def approve_trade(
    trade_id: str,
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    from models.trade import Trade
    result = await db.execute(select(Trade).where(Trade.id == trade_id, Trade.user_id == user.id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    trade.approved_by = f"user:{user.id}"
    await db.commit()
    return {"status": "approved", "trade_id": trade_id}


@app.post("/api/trades/{trade_id}/reject")
async def reject_trade(
    trade_id: str,
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    from models.trade import Trade
    result = await db.execute(select(Trade).where(Trade.id == trade_id, Trade.user_id == user.id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    trade.approved_by = "rejected"
    await db.commit()
    return {"status": "rejected", "trade_id": trade_id}


# ===========================================================================
# AI PIPELINE (Pro+)
# ===========================================================================
@app.post("/api/analyze/{ticker}")
async def analyze_ticker(
    ticker: str,
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    from middleware.ai_rate_limiter import check_ai_limit
    ticker = _validate_ticker(ticker)
    await check_ai_limit(user, "full_pipeline", db)
    return {"ticker": ticker, "status": "pipeline_ready",
            "message": "Connect Schwab account to enable live analysis"}


@app.get("/api/decisions")
async def get_decisions(user: User = Depends(require_tier("pro", "managed"))):
    return {"decisions": [], "count": 0}


# ===========================================================================
# DATA (all authenticated)
# ===========================================================================
@app.get("/api/price/{ticker}")
async def get_price(ticker: str, user: User = Depends(get_current_user)):
    ticker = _validate_ticker(ticker)
    current_price = None
    ema20 = ema50 = None
    signal = None

    try:
        current_price = get_current_price(ticker)
    except Exception:
        pass

    try:
        df = get_price_history(ticker, days=120)
        if not df.empty and "close" in df.columns:
            sig = detect_signal(df["close"])
            ema20 = sig["ema20"]
            ema50 = sig["ema50"]
            signal = sig["signal"]
    except Exception:
        pass

    return {"ticker": ticker, "current_price": current_price,
            "ema20": ema20, "ema50": ema50, "signal": signal,
            "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/news/{ticker}")
async def get_news(ticker: str, user: User = Depends(get_current_user)):
    ticker = _validate_ticker(ticker)
    try:
        result = score_sentiment(ticker, user_id=user.id)
        return {"ticker": ticker, **result}
    except Exception:
        return {"ticker": ticker, "score": 0, "headlines": []}


# ===========================================================================
# TAX (Pro+)
# ===========================================================================
@app.get("/api/tax/summary")
async def get_tax_summary(user: User = Depends(require_tier("pro", "managed"))):
    return {"ytd_short_term_gains": 0, "ytd_long_term_gains": 0,
            "estimated_tax": 0, "as_of": datetime.now(timezone.utc).isoformat()}


@app.get("/api/tax/harvest")
async def get_tax_harvest(user: User = Depends(require_tier("pro", "managed"))):
    return {"opportunities": []}


@app.get("/api/zakat")
async def get_zakat(user: User = Depends(require_tier("pro", "managed"))):
    result = calculate_zakat(portfolio_value=0, cash_balance=0)
    return result


# ===========================================================================
# SCHWAB (Pro+)
# ===========================================================================
@app.post("/api/schwab/connect")
async def connect_schwab(
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    return {"status": "ready", "message": "Schwab OAuth flow endpoint"}


@app.post("/api/schwab/disconnect")
async def disconnect_schwab(
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    user.schwab_app_key_enc = None
    user.schwab_app_secret_enc = None
    user.schwab_token_json_enc = None
    await db.commit()
    return {"status": "disconnected"}


@app.get("/api/schwab/status")
async def schwab_status(user: User = Depends(require_tier("pro", "managed"))):
    connected = user.schwab_token_json_enc is not None
    return {"connected": connected, "token_age_days": None}


# ===========================================================================
# WATCHLIST (all tiers, Free limited to 3)
# ===========================================================================
@app.get("/api/watchlist")
async def get_watchlist(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from models.watchlist import WatchlistItem
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.added_at.desc())
    )
    items = result.scalars().all()
    return {"watchlist": [{"ticker": w.ticker, "added_at": w.added_at.isoformat()} for w in items],
            "count": len(items)}


class WatchlistAdd(BaseModel):
    ticker: str


@app.post("/api/watchlist")
async def add_to_watchlist(
    body: WatchlistAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from models.watchlist import WatchlistItem
    ticker = _validate_ticker(body.ticker)

    # Enforce Free tier limit
    if user.tier == "free":
        result = await db.execute(
            select(func.count(WatchlistItem.id)).where(WatchlistItem.user_id == user.id)
        )
        count = result.scalar() or 0
        if count >= 3:
            raise HTTPException(status_code=403, detail="Free tier limited to 3 watchlist items. Upgrade to Pro.")

    # Check duplicate
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.ticker == ticker)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already in watchlist")

    db.add(WatchlistItem(user_id=user.id, ticker=ticker))
    await db.commit()
    return {"status": "added", "ticker": ticker}


@app.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from models.watchlist import WatchlistItem
    ticker = _validate_ticker(ticker)
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.ticker == ticker)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    await db.delete(item)
    await db.commit()
    return {"status": "removed", "ticker": ticker}


# ===========================================================================
# TRADER INBOX (Managed tier, is_trader=True)
# ===========================================================================
@app.get("/trader/queue")
async def trader_queue(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_trader:
        raise HTTPException(status_code=403, detail="Trader access only")
    from models.trader_review import TraderReview
    result = await db.execute(
        select(TraderReview).where(TraderReview.status == "pending")
        .order_by(TraderReview.created_at.asc()).limit(50)
    )
    reviews = result.scalars().all()
    return {
        "queue": [
            {"id": r.id, "user_id": r.user_id, "trade_id": r.trade_id,
             "signal": r.signal_json, "status": r.status,
             "created_at": r.created_at.isoformat()}
            for r in reviews
        ],
        "count": len(reviews),
    }


@app.post("/trader/approve/{review_id}")
async def trader_approve(
    review_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_trader:
        raise HTTPException(status_code=403, detail="Trader access only")
    from models.trader_review import TraderReview
    result = await db.execute(select(TraderReview).where(TraderReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.status = "approved"
    review.reviewed_by = user.email
    review.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "approved", "review_id": review_id}


@app.post("/trader/reject/{review_id}")
async def trader_reject(
    review_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_trader:
        raise HTTPException(status_code=403, detail="Trader access only")
    from models.trader_review import TraderReview
    result = await db.execute(select(TraderReview).where(TraderReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.status = "rejected"
    review.reviewed_by = user.email
    review.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "rejected", "review_id": review_id}


# ===========================================================================
# ADMIN
# ===========================================================================
@app.get("/admin/costs")
async def admin_costs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_trader:
        raise HTTPException(status_code=403, detail="Admin only")
    from models.token_usage import TokenUsage
    result = await db.execute(
        select(func.sum(TokenUsage.estimated_cost_usd), func.count(TokenUsage.id))
    )
    row = result.one()
    return {"total_cost_usd": float(row[0] or 0), "total_calls": row[1] or 0}


@app.get("/admin/revenue")
async def admin_revenue(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_trader:
        raise HTTPException(status_code=403, detail="Admin only")
    # Tier breakdown
    for tier in ("free", "pro", "managed"):
        result = await db.execute(
            select(func.count(User.id)).where(User.tier == tier, User.is_active == True)
        )
        count = result.scalar() or 0
    result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    total = result.scalar() or 0
    # In production, calculate MRR from Stripe
    return {"total_users": total, "mrr_estimate": 0}


@app.get("/admin/users")
async def admin_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_trader:
        raise HTTPException(status_code=403, detail="Admin only")
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(100))
    users = result.scalars().all()
    return {
        "users": [
            {"id": u.id, "email": u.email, "tier": u.tier,
             "is_active": u.is_active, "created_at": u.created_at.isoformat()}
            for u in users
        ],
    }


# ===========================================================================
# Serve frontend static files in production
# ===========================================================================
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logger.info("Serving frontend from %s", FRONTEND_DIST)


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Halal Trader API on %s:%d", API_HOST, API_PORT)
    uvicorn.run("main:app", host=API_HOST, port=API_PORT,
                reload=ENVIRONMENT == "development", log_level="info")
