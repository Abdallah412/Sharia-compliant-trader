"""
Halal Trader — FastAPI Main Application
Multi-tenant SaaS backend with auth, payments, AI pipeline, and trading bot.
"""

import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import CORS_ORIGINS, API_PORT, API_HOST, ENVIRONMENT, FRONTEND_URL
from database import get_db, init_db

# Routers
from auth.router import router as auth_router
from payments.router import router as payments_router
from notifications.router import router as notifications_router
from screener.router import router as screener_router
from auth.dependencies import get_current_user, require_tier
from models.user import User

# Optional imports
try:
    from shariah_screener import ShariahScreener
    _screener = ShariahScreener()
except ImportError:
    _screener = None

try:
    from data_fetcher import get_current_price, get_price_history, calculate_ema
except ImportError:
    get_current_price = None

try:
    from news_fetcher import get_news_sentiment
except ImportError:
    get_news_sentiment = None

try:
    from tax_engine import TaxEngine
    _tax_engine = TaxEngine()
except ImportError:
    _tax_engine = None

try:
    from zakat_calculator import calculate_zakat_due
except ImportError:
    calculate_zakat_due = None

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

    # Start scheduler in production
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


# ---------------------------------------------------------------------------
# Portfolio endpoints (Pro+)
# ---------------------------------------------------------------------------
@app.get("/api/portfolio")
async def get_portfolio(user: User = Depends(require_tier("pro", "managed"))):
    return {
        "total_value": 0,
        "cash": 0,
        "day_pnl": 0,
        "total_return_pct": 0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/holdings")
async def get_holdings(user: User = Depends(require_tier("pro", "managed"))):
    return {"holdings": [], "count": 0}


# ---------------------------------------------------------------------------
# Trades (Pro+)
# ---------------------------------------------------------------------------
@app.get("/api/trades")
async def get_trades(
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    from models.trade import Trade
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user.id)
        .order_by(Trade.executed_at.desc())
        .limit(50)
    )
    trades = result.scalars().all()
    return {
        "trades": [
            {
                "id": t.id,
                "ticker": t.ticker,
                "action": t.action,
                "quantity": t.quantity,
                "price": t.price,
                "total_value": t.total_value,
                "dry_run": t.dry_run,
                "sheikh_verdict": t.sheikh_verdict,
                "executed_at": t.executed_at.isoformat(),
            }
            for t in trades
        ],
        "count": len(trades),
    }


# ---------------------------------------------------------------------------
# AI Pipeline (Pro+)
# ---------------------------------------------------------------------------
@app.post("/api/analyze/{ticker}")
async def analyze_ticker(
    ticker: str,
    user: User = Depends(require_tier("pro", "managed")),
    db: AsyncSession = Depends(get_db),
):
    """Run full 4-agent pipeline on demand."""
    from middleware.ai_rate_limiter import check_ai_limit
    ticker = _validate_ticker(ticker)
    await check_ai_limit(user, "full_pipeline", db)

    # This would gather real data and run the pipeline
    # For now, return a placeholder
    return {
        "ticker": ticker,
        "status": "pipeline_ready",
        "message": "Connect Schwab account to enable live analysis",
    }


@app.get("/api/decisions")
async def get_decisions(user: User = Depends(require_tier("pro", "managed"))):
    return {"decisions": [], "count": 0}


# ---------------------------------------------------------------------------
# Data endpoints (available to all authenticated users)
# ---------------------------------------------------------------------------
@app.get("/api/price/{ticker}")
async def get_price(ticker: str, user: User = Depends(get_current_user)):
    ticker = _validate_ticker(ticker)

    current_price = None
    ema20 = None
    ema50 = None

    if get_current_price:
        try:
            current_price = get_current_price(ticker)
        except Exception:
            pass

        try:
            df = get_price_history(ticker, days=120)
            if not df.empty and "close" in df.columns:
                ema20_s = calculate_ema(df["close"], span=20)
                ema50_s = calculate_ema(df["close"], span=50)
                ema20 = round(float(ema20_s.iloc[-1]), 2) if len(ema20_s) > 0 else None
                ema50 = round(float(ema50_s.iloc[-1]), 2) if len(ema50_s) > 0 else None
        except Exception:
            pass

    return {
        "ticker": ticker,
        "current_price": current_price,
        "ema20": ema20,
        "ema50": ema50,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/news/{ticker}")
async def get_news(ticker: str, user: User = Depends(get_current_user)):
    ticker = _validate_ticker(ticker)

    if not get_news_sentiment:
        return {"ticker": ticker, "score": 0, "headlines": []}

    try:
        sentiment = get_news_sentiment(ticker, ticker)
        return {
            "ticker": ticker,
            "score": sentiment.get("score", 0),
            "headlines": sentiment.get("top_headlines", []),
        }
    except Exception:
        return {"ticker": ticker, "score": 0, "headlines": []}


# ---------------------------------------------------------------------------
# Tax (Pro+)
# ---------------------------------------------------------------------------
@app.get("/api/tax/summary")
async def get_tax_summary(user: User = Depends(require_tier("pro", "managed"))):
    return {
        "ytd_short_term_gains": 0,
        "ytd_long_term_gains": 0,
        "estimated_tax": 0,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/tax/harvest")
async def get_tax_harvest(user: User = Depends(require_tier("pro", "managed"))):
    return {"opportunities": []}


@app.get("/api/zakat")
async def get_zakat(user: User = Depends(require_tier("pro", "managed"))):
    return {
        "zakat_due": False,
        "amount": 0,
        "nisab_threshold": 6800,
        "portfolio_value": 0,
    }


# ---------------------------------------------------------------------------
# Schwab connection (Pro+)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
@app.get("/admin/costs")
async def admin_costs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_trader:
        raise HTTPException(status_code=403, detail="Admin only")

    from sqlalchemy import func
    from models.token_usage import TokenUsage

    result = await db.execute(
        select(
            func.sum(TokenUsage.estimated_cost_usd),
            func.count(TokenUsage.id),
        )
    )
    row = result.one()
    return {
        "total_cost_usd": float(row[0] or 0),
        "total_calls": row[1] or 0,
    }


# ---------------------------------------------------------------------------
# Serve frontend static files in production
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logger.info("Serving frontend from %s", FRONTEND_DIST)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Halal Trader API on %s:%d", API_HOST, API_PORT)
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=ENVIRONMENT == "development",
        log_level="info",
    )
