"""
Portfolio Manager for Halal Trader Bot.
Manages portfolio state persistence, position sizing, limit checks,
and portfolio summary calculations using data/portfolio_state.json.
"""

import os
import sys
import json
import math
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Resolve paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_FILE = PROJECT_ROOT / "data" / "portfolio_state.json"

# Position-sizing rules from environment
MAX_POSITION_PCT_STOCK = float(os.getenv("MAX_POSITION_PCT_STOCK", "0.20"))
MAX_POSITION_PCT_ETF = float(os.getenv("MAX_POSITION_PCT_ETF", "0.40"))
MIN_CASH_RESERVE_PCT = float(os.getenv("MIN_CASH_RESERVE_PCT", "0.10"))

# Default portfolio template
_DEFAULT_PORTFOLIO = {
    "cash": 0.0,
    "initial_value": 0.0,
    "positions": {},
    "last_updated": None,
}


def load_portfolio() -> dict:
    """Load portfolio state from the JSON file. Returns default if missing or empty."""
    try:
        if PORTFOLIO_FILE.exists():
            with open(PORTFOLIO_FILE, "r") as f:
                data = json.load(f)
            if data:
                # Ensure all expected keys exist
                for key, default in _DEFAULT_PORTFOLIO.items():
                    data.setdefault(key, default)
                return data
        logger.info("No existing portfolio found — returning defaults.")
        return dict(_DEFAULT_PORTFOLIO)
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load portfolio: %s", e)
        return dict(_DEFAULT_PORTFOLIO)


def save_portfolio(portfolio: dict) -> None:
    """Persist portfolio state to the JSON file."""
    try:
        PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
        portfolio["last_updated"] = datetime.now().isoformat()
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=2, default=str)
        logger.info("Portfolio saved at %s", portfolio["last_updated"])
    except IOError as e:
        logger.error("Failed to save portfolio: %s", e)
        raise


def _get_current_price(ticker: str) -> float:
    """Fetch the current price via data_fetcher, with a fallback of 0."""
    try:
        from backend.data_fetcher import get_current_price
        return get_current_price(ticker)
    except ImportError:
        pass
    try:
        from data_fetcher import get_current_price
        return get_current_price(ticker)
    except ImportError:
        logger.warning("data_fetcher not available — cannot fetch live price for %s", ticker)
        return 0.0


def update_position(ticker: str, qty: int, price: float, action: str) -> dict:
    """
    Update a position after a trade.

    Args:
        ticker: Stock/ETF symbol.
        qty: Number of shares traded (positive).
        price: Execution price per share.
        action: 'BUY' or 'SELL'.

    Returns:
        Updated position dict for the ticker.
    """
    portfolio = load_portfolio()
    positions = portfolio.setdefault("positions", {})
    action = action.upper()

    if action == "BUY":
        if ticker in positions:
            existing = positions[ticker]
            old_qty = existing.get("qty", 0)
            old_avg = existing.get("avg_price", 0.0)
            new_qty = old_qty + qty
            # Weighted average cost basis
            new_avg = ((old_avg * old_qty) + (price * qty)) / new_qty if new_qty else 0.0
            existing["qty"] = new_qty
            existing["avg_price"] = round(new_avg, 4)
            existing["last_action"] = "BUY"
            existing["last_action_date"] = datetime.now().isoformat()
        else:
            positions[ticker] = {
                "qty": qty,
                "avg_price": round(price, 4),
                "first_bought": datetime.now().isoformat(),
                "last_action": "BUY",
                "last_action_date": datetime.now().isoformat(),
            }
        portfolio["cash"] = portfolio.get("cash", 0.0) - (qty * price)

    elif action == "SELL":
        if ticker not in positions:
            logger.warning("Attempted to sell %s but no position found.", ticker)
            return {}
        existing = positions[ticker]
        old_qty = existing.get("qty", 0)
        sell_qty = min(qty, old_qty)
        remaining = old_qty - sell_qty

        if remaining <= 0:
            del positions[ticker]
        else:
            existing["qty"] = remaining
            existing["last_action"] = "SELL"
            existing["last_action_date"] = datetime.now().isoformat()

        portfolio["cash"] = portfolio.get("cash", 0.0) + (sell_qty * price)

    else:
        logger.error("Unknown action: %s", action)
        return {}

    save_portfolio(portfolio)
    return positions.get(ticker, {})


def get_portfolio_summary() -> dict:
    """
    Compute a full portfolio summary.

    Returns:
        dict with keys: total_value, cash, day_pnl, total_return_pct, positions
    """
    portfolio = load_portfolio()
    cash = portfolio.get("cash", 0.0)
    initial_value = portfolio.get("initial_value", 0.0)
    positions = portfolio.get("positions", {})

    holdings_value = 0.0
    day_pnl = 0.0
    enriched_positions = {}

    for ticker, pos in positions.items():
        qty = pos.get("qty", 0)
        avg_price = pos.get("avg_price", 0.0)

        current_price = _get_current_price(ticker)
        if current_price <= 0:
            current_price = avg_price  # fallback

        market_value = qty * current_price
        cost_basis = qty * avg_price
        unrealised_pnl = market_value - cost_basis
        pnl_pct = (unrealised_pnl / cost_basis * 100) if cost_basis else 0.0

        holdings_value += market_value
        day_pnl += unrealised_pnl  # simplified; full day-P&L needs yesterday's close

        enriched_positions[ticker] = {
            **pos,
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "unrealised_pnl": round(unrealised_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        }

    total_value = cash + holdings_value
    total_return_pct = (
        ((total_value - initial_value) / initial_value * 100) if initial_value else 0.0
    )

    return {
        "total_value": round(total_value, 2),
        "cash": round(cash, 2),
        "day_pnl": round(day_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "positions": enriched_positions,
    }


def calculate_position_size(
    portfolio_value: float,
    ticker: str,
    is_etf: bool = False,
    confidence_multiplier: float = 1.0,
) -> int:
    """
    Calculate the number of shares to buy for a given ticker.

    Uses position-limit percentages and cash reserve to determine maximum
    allocation, then scales by the confidence_multiplier (0.0 - 1.0).

    Returns:
        Integer number of shares (floored). 0 if price unavailable or no room.
    """
    max_pct = MAX_POSITION_PCT_ETF if is_etf else MAX_POSITION_PCT_STOCK
    confidence_multiplier = max(0.0, min(confidence_multiplier, 1.0))

    # Max dollars allocatable to this position
    max_allocation = portfolio_value * max_pct * confidence_multiplier

    # Respect cash reserve
    portfolio = load_portfolio()
    cash = portfolio.get("cash", 0.0)
    min_cash = portfolio_value * MIN_CASH_RESERVE_PCT
    available_cash = max(cash - min_cash, 0.0)
    allocation = min(max_allocation, available_cash)

    current_price = _get_current_price(ticker)
    if current_price <= 0:
        logger.warning("Cannot size position for %s — price unavailable.", ticker)
        return 0

    shares = int(math.floor(allocation / current_price))
    logger.info(
        "Position size for %s: %d shares (alloc=$%.2f, price=$%.2f, conf=%.2f)",
        ticker, shares, allocation, current_price, confidence_multiplier,
    )
    return shares


def check_position_limits(ticker: str, proposed_qty: int, proposed_price: float) -> dict:
    """
    Check whether a proposed trade respects portfolio risk limits.

    Returns:
        dict with 'allowed' (bool) and 'reason' (str).
    """
    portfolio = load_portfolio()
    cash = portfolio.get("cash", 0.0)
    positions = portfolio.get("positions", {})

    # Calculate current total portfolio value
    holdings_value = 0.0
    for t, pos in positions.items():
        q = pos.get("qty", 0)
        p = _get_current_price(t)
        if p <= 0:
            p = pos.get("avg_price", 0.0)
        holdings_value += q * p

    total_value = cash + holdings_value
    if total_value <= 0:
        return {"allowed": False, "reason": "Portfolio value is zero or negative."}

    trade_cost = proposed_qty * proposed_price

    # Check cash sufficiency
    if trade_cost > cash:
        return {
            "allowed": False,
            "reason": (
                f"Insufficient cash. Need ${trade_cost:,.2f} but only "
                f"${cash:,.2f} available."
            ),
        }

    # Check cash reserve after trade
    cash_after = cash - trade_cost
    min_cash = total_value * MIN_CASH_RESERVE_PCT
    if cash_after < min_cash:
        return {
            "allowed": False,
            "reason": (
                f"Trade would breach minimum cash reserve. "
                f"Cash after trade: ${cash_after:,.2f}, "
                f"minimum required: ${min_cash:,.2f} "
                f"({MIN_CASH_RESERVE_PCT * 100:.0f}% of portfolio)."
            ),
        }

    # Check position concentration
    existing_value = 0.0
    if ticker in positions:
        eq = positions[ticker].get("qty", 0)
        ep = _get_current_price(ticker)
        if ep <= 0:
            ep = positions[ticker].get("avg_price", 0.0)
        existing_value = eq * ep

    new_position_value = existing_value + trade_cost
    position_pct = new_position_value / total_value

    # Determine limit (use ETF limit if ticker looks like a common ETF pattern)
    # A more robust check could use a database; for now use a simple heuristic
    max_pct = MAX_POSITION_PCT_STOCK  # default to stock
    etf_suffixes = ("ETF", "FUND")
    if any(ticker.upper().endswith(s) for s in etf_suffixes):
        max_pct = MAX_POSITION_PCT_ETF

    if position_pct > max_pct:
        return {
            "allowed": False,
            "reason": (
                f"Position in {ticker} would be {position_pct * 100:.1f}% of portfolio, "
                f"exceeding the {max_pct * 100:.0f}% limit."
            ),
        }

    return {"allowed": True, "reason": "Trade passes all position-limit checks."}


def get_all_holdings() -> list:
    """
    Return a list of position dicts enriched with current price and compliance status.

    Each dict contains: ticker, qty, avg_price, current_price, market_value,
    unrealised_pnl, pnl_pct, compliance_status, first_bought, last_action,
    last_action_date.
    """
    portfolio = load_portfolio()
    positions = portfolio.get("positions", {})
    holdings = []

    # Try to load compliance cache for Shariah status
    compliance_cache = {}
    compliance_file = PROJECT_ROOT / "data" / "compliance_cache.json"
    if compliance_file.exists():
        try:
            with open(compliance_file, "r") as f:
                compliance_cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Could not load compliance cache.")

    for ticker, pos in positions.items():
        qty = pos.get("qty", 0)
        avg_price = pos.get("avg_price", 0.0)
        current_price = _get_current_price(ticker)
        if current_price <= 0:
            current_price = avg_price

        market_value = qty * current_price
        cost_basis = qty * avg_price
        unrealised_pnl = market_value - cost_basis
        pnl_pct = (unrealised_pnl / cost_basis * 100) if cost_basis else 0.0

        # Compliance status from cache
        cached = compliance_cache.get(ticker, {})
        compliance_status = cached.get("status", "unknown")

        holdings.append({
            "ticker": ticker,
            "qty": qty,
            "avg_price": round(avg_price, 4),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "unrealised_pnl": round(unrealised_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "compliance_status": compliance_status,
            "first_bought": pos.get("first_bought"),
            "last_action": pos.get("last_action"),
            "last_action_date": pos.get("last_action_date"),
        })

    return holdings


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("\n=== Portfolio Manager ===\n")

    summary = get_portfolio_summary()
    print(f"Total Value:  ${summary['total_value']:,.2f}")
    print(f"Cash:         ${summary['cash']:,.2f}")
    print(f"Day P&L:      ${summary['day_pnl']:+,.2f}")
    print(f"Total Return: {summary['total_return_pct']:+.2f}%")

    holdings = get_all_holdings()
    if holdings:
        print(f"\nPositions ({len(holdings)}):")
        df = pd.DataFrame(holdings)
        print(df.to_string(index=False))
    else:
        print("\nNo positions held.")

    print("\nPortfolio file:", PORTFOLIO_FILE)
