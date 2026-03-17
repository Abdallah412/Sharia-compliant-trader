"""
Tax engine — holding period, wash sale detection, loss harvesting, YTD gains.
"""

import logging
from datetime import date, datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger("tax.engine")

# 2026 Federal long-term capital gains brackets (single filer)
LTCG_BRACKETS_SINGLE = [
    (49_450, 0.00),
    (544_400, 0.15),
    (float("inf"), 0.20),
]

# Net Investment Income Tax
NIIT_THRESHOLD_SINGLE = 200_000
NIIT_THRESHOLD_MARRIED = 250_000
NIIT_RATE = 0.038

# State tax rates (simplified — top marginal rate)
STATE_RATES = {
    "CA": 0.133, "NY": 0.109, "NJ": 0.1075, "OR": 0.099,
    "MN": 0.0985, "HI": 0.11, "VT": 0.0875, "IA": 0.06,
    "WI": 0.0765, "SC": 0.065, "TX": 0.0, "FL": 0.0,
    "NV": 0.0, "WA": 0.0, "WY": 0.0, "TN": 0.0, "NH": 0.0,
}


def is_long_term(purchase_date: str | date) -> bool:
    """Position held > 365 days?"""
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    return (date.today() - purchase_date).days > 365


def days_to_long_term(purchase_date: str | date) -> int:
    """Days remaining until long-term qualification."""
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    days_held = (date.today() - purchase_date).days
    return max(0, 366 - days_held)


def estimate_tax(
    gain: float,
    is_lt: bool,
    income_bracket_pct: int = 22,
    state: str = "CA",
    filing_status: str = "single",
    ytd_gains: float = 0.0,
) -> dict:
    """Estimate federal + state tax on a capital gain."""
    if gain <= 0:
        return {"federal": 0.0, "state": 0.0, "niit": 0.0, "total": 0.0}

    # Federal
    if is_lt:
        federal_rate = 0.15  # Most common bracket
        for threshold, rate in LTCG_BRACKETS_SINGLE:
            if ytd_gains + gain <= threshold:
                federal_rate = rate
                break
    else:
        federal_rate = income_bracket_pct / 100.0

    federal = gain * federal_rate

    # NIIT
    threshold = NIIT_THRESHOLD_MARRIED if filing_status == "married" else NIIT_THRESHOLD_SINGLE
    niit = gain * NIIT_RATE if (ytd_gains + gain) > threshold else 0.0

    # State
    state_rate = STATE_RATES.get(state.upper(), 0.05)
    state_tax = gain * state_rate

    total = federal + niit + state_tax
    return {
        "federal": round(federal, 2),
        "state": round(state_tax, 2),
        "niit": round(niit, 2),
        "total": round(total, 2),
        "effective_rate_pct": round(total / gain * 100, 1) if gain > 0 else 0,
    }


def check_wash_sale(
    ticker: str,
    action: str,
    recent_trades: list[dict],
) -> dict:
    """
    Check for wash sale risk.
    If the same ticker was sold at a loss within 30 days before or after,
    the loss is disallowed.
    """
    if action != "SELL":
        return {"risk": False, "warning": ""}

    today = date.today()
    window_start = today - timedelta(days=30)
    window_end = today + timedelta(days=30)

    for trade in recent_trades:
        if trade.get("ticker") != ticker:
            continue
        if trade.get("action") != "BUY":
            continue
        trade_date = trade.get("date", "")
        if isinstance(trade_date, str):
            try:
                trade_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
            except ValueError:
                continue
        if window_start <= trade_date <= window_end:
            return {
                "risk": True,
                "warning": f"Wash sale risk: {ticker} was bought on {trade_date} "
                           f"within 30-day window. Loss will be disallowed by IRS.",
            }

    return {"risk": False, "warning": ""}


def find_harvest_candidates(positions: list[dict]) -> list[dict]:
    """Find positions with unrealized losses for tax-loss harvesting."""
    candidates = []
    for pos in positions:
        current = pos.get("current_price", 0)
        cost = pos.get("avg_cost", 0)
        if current < cost and cost > 0:
            loss = (current - cost) * pos.get("quantity", 0)
            candidates.append({
                "ticker": pos.get("ticker"),
                "quantity": pos.get("quantity"),
                "avg_cost": cost,
                "current_price": current,
                "unrealized_loss": round(loss, 2),
                "loss_pct": round((current - cost) / cost * 100, 1),
            })
    return sorted(candidates, key=lambda x: x["unrealized_loss"])
