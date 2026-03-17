"""
Halal Trading Bot — FastAPI Server
Provides REST API endpoints for portfolio monitoring, compliance screening,
trade management, and bot control.
"""

import os
import csv
import json
import hmac
import hashlib
import logging
import re
import secrets
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# ---------------------------------------------------------------------------
# Security: API Key Authentication
# ---------------------------------------------------------------------------
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
if not API_SECRET_KEY:
    API_SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning(
        "API_SECRET_KEY not set in environment. Generated ephemeral key. "
        "Set API_SECRET_KEY in .env for persistent authentication."
    )

# Ticker symbol validation regex: 1-10 uppercase letters, dots, hyphens only
TICKER_REGEX = re.compile(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?(-[A-Z]{1,2})?$")


def _validate_ticker(ticker: str) -> str:
    """Validate and sanitize a ticker symbol. Raises HTTPException on invalid input."""
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")
    if not TICKER_REGEX.match(ticker):
        raise HTTPException(
            status_code=400,
            detail="Ticker must contain only uppercase letters, dots, and hyphens (1-10 chars)",
        )
    return ticker


async def verify_api_key(x_api_key: str = Header(None)):
    """Dependency that verifies the API key for protected endpoints."""
    if not x_api_key or not hmac.compare_digest(x_api_key, API_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# ---------------------------------------------------------------------------
# Sibling module imports
# ---------------------------------------------------------------------------
from shariah_screener import ShariahScreener
from data_fetcher import get_current_price, get_price_history, calculate_ema
from portfolio_allocator import recommend_allocation, format_allocation_report
from news_fetcher import get_news_sentiment
from schwab_auth import get_client, get_account_balance, get_positions, get_token_age_days

# These modules may not exist yet — import defensively
try:
    from tax_engine import TaxEngine as _TaxEngine
    _tax_engine_instance = _TaxEngine()

    def get_ytd_gains():
        """Wrapper -- returns YTD gains from trade log."""
        import pandas as pd
        if not TRADE_LOG_PATH.exists():
            return {"short_term_gains": 0, "long_term_gains": 0, "total_realized": 0, "estimated_tax": 0}
        df = pd.read_csv(TRADE_LOG_PATH)
        if "date" not in df.columns and "timestamp" in df.columns:
            df["date"] = df["timestamp"]
        if "gain" not in df.columns:
            return {"short_term_gains": 0, "long_term_gains": 0, "total_realized": 0, "estimated_tax": 0}
        return _tax_engine_instance.get_ytd_gains(df)

    def get_loss_harvest_opportunities():
        return []

    def estimate_tax():
        return get_ytd_gains().get("estimated_tax", 0)

except ImportError:
    logger.warning("tax_engine not found — /api/tax endpoint will be unavailable")
    get_ytd_gains = None
    get_loss_harvest_opportunities = None
    estimate_tax = None

try:
    from portfolio_manager import load_portfolio, get_portfolio_summary, get_all_holdings
except ImportError:
    logger.warning("portfolio_manager not found — some endpoints will use fallback data")
    load_portfolio = None
    get_portfolio_summary = None
    get_all_holdings = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRADE_LOG_PATH = DATA_DIR / "trade_log.csv"
DECISIONS_LOG_PATH = DATA_DIR / "decisions.log"
PORTFOLIO_STATE_PATH = DATA_DIR / "portfolio_state.json"

# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
API_PORT = int(os.getenv("API_PORT", "8000"))
BOT_START_TIME = datetime.now().isoformat()
LAST_RUN_TIME = None
PENDING_TRADES: dict = {}  # trade_id -> trade details

screener = ShariahScreener()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Halal Trading Bot API",
    description="Sharia-compliant automated trading system",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ---------------------------------------------------------------------------
# Global exception handler: prevent leaking internal details
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a safe error response."""
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _load_portfolio_state() -> dict:
    """Load the persisted portfolio state JSON."""
    try:
        if PORTFOLIO_STATE_PATH.exists():
            return json.loads(PORTFOLIO_STATE_PATH.read_text())
    except Exception as exc:
        logger.error("Failed to load portfolio state: %s", exc)
    return {}


def _compliance_badge(compliant) -> str:
    """Map compliance boolean to a human-readable badge."""
    if compliant is True:
        return "halal"
    elif compliant is False:
        return "haram"
    return "doubtful"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def get_status():
    """Bot status, auth status, last run time, dry_run flag."""
    token_age = None
    auth_ok = False
    try:
        token_age = get_token_age_days()
        auth_ok = token_age < 7
    except Exception:
        pass

    return {
        "bot_started": BOT_START_TIME,
        "last_run_time": LAST_RUN_TIME,
        "dry_run": DRY_RUN,
        "auth_ok": auth_ok,
        "token_age_days": token_age,
        "pending_trades": len(PENDING_TRADES),
    }


@app.get("/api/portfolio")
async def get_portfolio():
    """Total value, cash, day P&L, total return %."""
    state = _load_portfolio_state()

    # Try live data from Schwab
    try:
        client = get_client()
        if client:
            balance = get_account_balance(client)
            return {
                "total_value": balance.get("liquidation_value", 0),
                "cash": balance.get("cash_balance", 0),
                "day_pnl": balance.get("day_pnl", state.get("day_pnl", 0)),
                "total_return_pct": state.get("total_return_pct", 0),
                "last_updated": datetime.now().isoformat(),
            }
    except Exception as exc:
        logger.warning("Live portfolio fetch failed, using cached state: %s", exc)

    return {
        "total_value": state.get("total_value", 0),
        "cash": state.get("cash", 0),
        "day_pnl": state.get("day_pnl", 0),
        "total_return_pct": state.get("total_return_pct", 0),
        "last_updated": state.get("last_updated"),
    }


@app.get("/api/holdings")
async def get_holdings():
    """All positions with Shariah compliance badges."""
    positions = []

    try:
        client = get_client()
        if client:
            raw_positions = get_positions(client)
            for pos in raw_positions:
                ticker = pos.get("symbol", pos.get("ticker", ""))
                result = screener.screen(ticker)
                positions.append({
                    "ticker": ticker,
                    "company_name": result.company_name or pos.get("company_name", ""),
                    "quantity": pos.get("quantity", 0),
                    "avg_cost": pos.get("avg_cost", 0),
                    "current_price": pos.get("current_price", 0),
                    "market_value": pos.get("market_value", 0),
                    "day_change_pct": pos.get("day_change_pct", 0),
                    "total_gain_pct": pos.get("total_gain_pct", 0),
                    "compliance": _compliance_badge(result.compliant),
                    "purification_pct": result.purification_pct,
                    "warnings": result.warnings,
                })
    except Exception as exc:
        logger.error("Failed to fetch holdings: %s", exc)

    # Fallback: read from portfolio state
    if not positions:
        state = _load_portfolio_state()
        for ticker, holding in state.get("holdings", {}).items():
            result = screener.screen(ticker)
            positions.append({
                "ticker": ticker,
                "company_name": result.company_name,
                "quantity": holding.get("quantity", 0),
                "avg_cost": holding.get("avg_cost", 0),
                "current_price": holding.get("current_price", 0),
                "market_value": holding.get("market_value", 0),
                "day_change_pct": 0,
                "total_gain_pct": 0,
                "compliance": _compliance_badge(result.compliant),
                "purification_pct": result.purification_pct,
                "warnings": result.warnings,
            })

    return {"holdings": positions, "count": len(positions)}


@app.get("/api/trades")
async def get_trades():
    """Last 50 trades from data/trade_log.csv."""
    trades = []

    if not TRADE_LOG_PATH.exists():
        return {"trades": [], "count": 0}

    try:
        with open(TRADE_LOG_PATH, newline="") as f:
            reader = csv.DictReader(f)
            trades = list(reader)
    except Exception as exc:
        logger.error("Failed to read trade log: %s", exc)
        raise HTTPException(status_code=500, detail="Could not read trade log")

    # Return last 50, most recent first
    trades = trades[-50:][::-1]
    return {"trades": trades, "count": len(trades)}


@app.get("/api/compliance/{ticker}")
async def get_compliance(ticker: str):
    """On-demand Shariah screen via ShariahScreener."""
    ticker = _validate_ticker(ticker)

    result = screener.screen(ticker)
    return {
        "ticker": result.ticker,
        "company_name": result.company_name,
        "sector": result.sector,
        "industry": result.industry,
        "compliance": _compliance_badge(result.compliant),
        "compliant": result.compliant,
        "fail_reasons": result.fail_reasons,
        "warnings": result.warnings,
        "debt_ratio": result.debt_ratio,
        "cash_ratio": result.cash_ratio,
        "receivables_ratio": result.receivables_ratio,
        "purification_pct": result.purification_pct,
        "madhab_notes": result.madhab_notes,
    }


@app.get("/api/price/{ticker}")
async def get_price(ticker: str):
    """Current price + EMA20 + EMA50 + news sentiment score."""
    ticker = _validate_ticker(ticker)

    try:
        current_price = get_current_price(ticker)
    except Exception:
        current_price = None

    ema20 = None
    ema50 = None
    try:
        df = get_price_history(ticker, days=120)
        if not df.empty and "close" in df.columns:
            ema20_series = calculate_ema(df["close"], span=20)
            ema50_series = calculate_ema(df["close"], span=50)
            ema20 = round(float(ema20_series.iloc[-1]), 2) if len(ema20_series) > 0 else None
            ema50 = round(float(ema50_series.iloc[-1]), 2) if len(ema50_series) > 0 else None
    except Exception as exc:
        logger.warning("EMA calculation failed for %s: %s", ticker, exc)

    news_score = None
    try:
        sentiment = get_news_sentiment(ticker, ticker)
        news_score = sentiment.get("score", sentiment.get("sentiment_score"))
    except Exception as exc:
        logger.warning("News sentiment fetch failed for %s: %s", ticker, exc)

    return {
        "ticker": ticker,
        "current_price": current_price,
        "ema20": ema20,
        "ema50": ema50,
        "news_score": news_score,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/tax")
async def get_tax():
    """YTD gains, estimated tax, loss harvest opportunities."""
    if get_ytd_gains is None:
        raise HTTPException(status_code=501, detail="tax_engine module not available")

    try:
        ytd_gains = get_ytd_gains()
        estimated_tax = estimate_tax()
        harvest = get_loss_harvest_opportunities()

        return {
            "ytd_gains": ytd_gains,
            "estimated_tax": estimated_tax,
            "loss_harvest_opportunities": harvest,
            "as_of": datetime.now().isoformat(),
        }
    except Exception as exc:
        logger.error("Tax calculation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Tax calculation failed")


@app.get("/api/decisions")
async def get_decisions():
    """Last 20 decisions from data/decisions.log."""
    if not DECISIONS_LOG_PATH.exists():
        return {"decisions": [], "count": 0}

    try:
        lines = DECISIONS_LOG_PATH.read_text().strip().splitlines()
    except Exception as exc:
        logger.error("Failed to read decisions log: %s", exc)
        raise HTTPException(status_code=500, detail="Could not read decisions log")

    # Return last 20, most recent first
    decisions = lines[-20:][::-1]
    return {"decisions": decisions, "count": len(decisions)}


@app.post("/api/bot/toggle")
async def toggle_bot(authorized: bool = Depends(verify_api_key)):
    """Enable/disable live trading (toggle DRY_RUN). Requires API key."""
    global DRY_RUN
    DRY_RUN = not DRY_RUN
    mode = "DRY RUN (paper)" if DRY_RUN else "LIVE TRADING"
    logger.info("Bot mode toggled to: %s", mode)
    return {"dry_run": DRY_RUN, "mode": mode}


@app.post("/api/allocate")
async def allocate_portfolio(
    amount: float,
    risk_profile: str = "moderate",
    use_ai: bool = True,
    authorized: bool = Depends(verify_api_key),
):
    """
    Given a dollar amount, recommend how to distribute funds across halal stocks.
    risk_profile: 'conservative', 'moderate', or 'aggressive'
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if risk_profile not in ("conservative", "moderate", "aggressive"):
        raise HTTPException(
            status_code=400,
            detail="risk_profile must be 'conservative', 'moderate', or 'aggressive'",
        )

    try:
        plan = recommend_allocation(amount, risk_profile=risk_profile, use_ai=use_ai)
        if "error" in plan:
            raise HTTPException(status_code=400, detail=plan["error"])
        plan["formatted_report"] = format_allocation_report(plan)
        return plan
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Allocation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Allocation failed")


@app.post("/api/approve/{trade_id}")
async def approve_trade(trade_id: str, authorized: bool = Depends(verify_api_key)):
    """Approve a pending trade. Requires API key."""
    # Validate trade_id format to prevent injection
    if not trade_id or len(trade_id) > 64 or not re.match(r"^[a-zA-Z0-9_-]+$", trade_id):
        raise HTTPException(status_code=400, detail="Invalid trade ID format")

    if trade_id not in PENDING_TRADES:
        raise HTTPException(status_code=404, detail="Trade not found or already processed")

    trade = PENDING_TRADES.pop(trade_id)
    trade["approved"] = True
    trade["approved_at"] = datetime.now().isoformat()
    logger.info("Trade %s approved via API", trade_id)

    return {"trade_id": trade_id, "status": "approved", "trade": trade}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Halal Trading Bot API on port %d", API_PORT)
    bind_host = os.getenv("API_HOST", "127.0.0.1")
    uvicorn.run(
        "api_server:app",
        host=bind_host,
        port=API_PORT,
        reload=False,
        log_level="info",
    )
