"""
AAOIFI financial ratio checks — deterministic number crunching.
Run in parallel with pre-screen before invoking the Sheikh Agent.
"""

from dataclasses import dataclass


# AAOIFI thresholds (Sa'd ibn Abi Waqqas hadith: "One third is much")
THRESHOLDS = {
    "debt_to_market_cap": 0.30,     # Interest-bearing debt / market cap
    "cash_to_equity": 0.30,         # Interest-bearing deposits / equity
    "receivables_to_assets": 0.33,  # Net receivables / total assets
    "haram_revenue_pct": 0.05,      # Max haram-source revenue (5%)
}


@dataclass
class RatioResult:
    debt_ratio: float
    cash_ratio: float
    receivables_ratio: float
    haram_revenue_pct: float
    debt_pass: bool
    cash_pass: bool
    receivables_pass: bool
    revenue_pass: bool
    all_pass: bool
    purification_pct: float


def calculate_ratios(
    total_debt: float,
    market_cap: float,
    interest_bearing_cash: float,
    total_equity: float,
    net_receivables: float,
    total_assets: float,
    haram_revenue: float,
    total_revenue: float,
) -> RatioResult:
    """Calculate AAOIFI financial ratios and check thresholds."""
    debt_ratio = total_debt / market_cap if market_cap > 0 else 1.0
    cash_ratio = interest_bearing_cash / total_equity if total_equity > 0 else 1.0
    receivables_ratio = net_receivables / total_assets if total_assets > 0 else 1.0
    haram_pct = haram_revenue / total_revenue if total_revenue > 0 else 0.0

    debt_pass = debt_ratio < THRESHOLDS["debt_to_market_cap"]
    cash_pass = cash_ratio < THRESHOLDS["cash_to_equity"]
    receivables_pass = receivables_ratio < THRESHOLDS["receivables_to_assets"]
    revenue_pass = haram_pct < THRESHOLDS["haram_revenue_pct"]

    # Purification: % of dividends from haram income to donate
    purification_pct = round(haram_pct * 100, 2)

    return RatioResult(
        debt_ratio=round(debt_ratio, 4),
        cash_ratio=round(cash_ratio, 4),
        receivables_ratio=round(receivables_ratio, 4),
        haram_revenue_pct=round(haram_pct, 4),
        debt_pass=debt_pass,
        cash_pass=cash_pass,
        receivables_pass=receivables_pass,
        revenue_pass=revenue_pass,
        all_pass=all([debt_pass, cash_pass, receivables_pass, revenue_pass]),
        purification_pct=purification_pct,
    )
