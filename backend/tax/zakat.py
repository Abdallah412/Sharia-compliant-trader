"""
Zakat calculator — nisab threshold, lunar year, purification.
"""

import logging
from datetime import date, timedelta

import requests

logger = logging.getLogger("tax.zakat")

GOLD_GRAMS_NISAB = 85       # 85 grams of gold
ZAKAT_RATE = 0.025           # 2.5%
LUNAR_YEAR_DAYS = 354        # Islamic lunar year


def get_gold_price_per_gram() -> float:
    """Fetch current gold price per gram in USD. Fallback to ~$80/gram."""
    try:
        resp = requests.get(
            "https://www.goldapi.io/api/XAU/USD",
            headers={"x-access-token": ""},  # free tier
            timeout=5,
        )
        if resp.status_code == 200:
            price_per_oz = resp.json().get("price", 2500.0)
            return price_per_oz / 31.1035  # troy oz to grams
    except Exception:
        pass
    return 80.0  # Conservative fallback (~$80/gram = ~$2,488/oz)


def calculate_nisab() -> float:
    """Current nisab threshold in USD."""
    return GOLD_GRAMS_NISAB * get_gold_price_per_gram()


def calculate_zakat(
    portfolio_value: float,
    cash_balance: float,
    purchase_date: str | date | None = None,
    gold_price_per_gram: float | None = None,
) -> dict:
    """
    Calculate Zakat due on investment portfolio.

    Zakat is wajib (obligatory) when:
    1. Wealth exceeds nisab (85g of gold)
    2. Wealth has been held for one lunar year (354 days)
    """
    if gold_price_per_gram is None:
        gold_price_per_gram = get_gold_price_per_gram()

    nisab = GOLD_GRAMS_NISAB * gold_price_per_gram
    total_wealth = portfolio_value + cash_balance

    # Check hawl (one lunar year)
    hawl_met = False
    days_held = 0
    if purchase_date:
        if isinstance(purchase_date, str):
            from datetime import datetime
            purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
        days_held = (date.today() - purchase_date).days
        hawl_met = days_held >= LUNAR_YEAR_DAYS

    zakat_due = total_wealth >= nisab and hawl_met
    zakat_amount = total_wealth * ZAKAT_RATE if zakat_due else 0.0

    return {
        "zakat_due": zakat_due,
        "zakat_amount_usd": round(zakat_amount, 2),
        "total_wealth_usd": round(total_wealth, 2),
        "nisab_usd": round(nisab, 2),
        "above_nisab": total_wealth >= nisab,
        "hawl_met": hawl_met,
        "days_held": days_held,
        "days_to_hawl": max(0, LUNAR_YEAR_DAYS - days_held),
        "gold_price_per_gram": round(gold_price_per_gram, 2),
        "rate": ZAKAT_RATE,
    }


def calculate_purification(dividend_amount: float, purification_pct: float) -> dict:
    """
    Calculate dividend purification (tazkiya).
    The impermissible portion of dividends must be donated as sadaqah.
    """
    donation = dividend_amount * (purification_pct / 100.0)
    return {
        "dividend_amount": round(dividend_amount, 2),
        "purification_pct": purification_pct,
        "donation_required": round(donation, 2),
        "net_halal_dividend": round(dividend_amount - donation, 2),
    }
