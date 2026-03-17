"""
Zakat Calculator for Halal Trading Bot
Calculates zakat obligations on investment portfolios and dividend purification
amounts according to Islamic financial principles.
"""

import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOLD_GRAMS_NISAB = 85          # Nisab = value of 85 grams of gold
ZAKAT_RATE = 0.025             # 2.5 %
LUNAR_YEAR_DAYS = 354          # One Islamic (Hijri) lunar year
DEFAULT_GOLD_PRICE_PER_GRAM = 70.59  # ~$6,000 / 85g — conservative fallback
GOLD_API_URL = "https://api.gold-api.com/price/XAU"  # free tier, no key needed


# ---------------------------------------------------------------------------
# Gold price helper
# ---------------------------------------------------------------------------

def _fetch_gold_price_per_gram() -> float:
    """
    Attempt to fetch the current gold price per gram (USD).
    Falls back to a sensible default on any failure.
    """
    try:
        resp = requests.get(GOLD_API_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # price per troy ounce -> per gram  (1 troy oz = 31.1035 g)
        price_per_oz = float(data.get("price", 0))
        if price_per_oz > 0:
            per_gram = round(price_per_oz / 31.1035, 2)
            logger.info("Live gold price: $%.2f/g ($%.2f/oz)", per_gram, price_per_oz)
            return per_gram
    except Exception as exc:
        logger.warning("Could not fetch live gold price (%s). Using default.", exc)

    return DEFAULT_GOLD_PRICE_PER_GRAM


# ---------------------------------------------------------------------------
# Zakat calculation
# ---------------------------------------------------------------------------

def calculate_zakat_due(
    portfolio_value: float,
    cash: float,
    purchase_date,
    gold_price_per_gram: Optional[float] = None,
) -> dict:
    """
    Determine whether zakat is due on combined portfolio + cash wealth and
    calculate the amount.

    Zakat conditions:
    1. Total zakatable wealth >= Nisab (value of 85 g gold).
    2. Wealth has been held for one full lunar year (354 days).

    Parameters
    ----------
    portfolio_value : float
        Current market value of all halal investments.
    cash : float
        Liquid cash and cash-equivalent holdings.
    purchase_date : str | date | datetime
        The date the wealth reached Nisab level (start of the haul /
        holding period).  Accepts ``"YYYY-MM-DD"`` strings.
    gold_price_per_gram : float, optional
        Override the gold spot price per gram (useful for testing).

    Returns
    -------
    dict
        zakat_due (bool), amount (float), lunar_year_date (str),
        nisab_threshold (float), note (str)
    """
    # Normalise purchase_date
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    elif isinstance(purchase_date, datetime):
        purchase_date = purchase_date.date()

    # Nisab threshold
    gpg = gold_price_per_gram if gold_price_per_gram else _fetch_gold_price_per_gram()
    nisab = round(GOLD_GRAMS_NISAB * gpg, 2)

    total_wealth = portfolio_value + cash
    lunar_year_date = purchase_date + timedelta(days=LUNAR_YEAR_DAYS)
    days_held = (date.today() - purchase_date).days
    haul_complete = days_held >= LUNAR_YEAR_DAYS

    zakat_due = (total_wealth >= nisab) and haul_complete
    amount = round(total_wealth * ZAKAT_RATE, 2) if zakat_due else 0.0

    # Build human-readable note
    if total_wealth < nisab:
        note = (
            f"Total wealth (${total_wealth:,.2f}) is below the Nisab "
            f"threshold (${nisab:,.2f}). Zakat is not obligatory."
        )
    elif not haul_complete:
        remaining = LUNAR_YEAR_DAYS - days_held
        note = (
            f"Wealth exceeds Nisab but the lunar year (haul) is not yet "
            f"complete. {remaining} day(s) remain until {lunar_year_date}."
        )
    else:
        note = (
            f"Zakat is due. 2.5% of ${total_wealth:,.2f} = ${amount:,.2f}. "
            f"May Allah accept your worship."
        )

    logger.info(
        "Zakat check: wealth=$%.2f  nisab=$%.2f  haul_complete=%s  due=%s  amount=$%.2f",
        total_wealth, nisab, haul_complete, zakat_due, amount,
    )

    return {
        "zakat_due": zakat_due,
        "amount": amount,
        "lunar_year_date": str(lunar_year_date),
        "nisab_threshold": nisab,
        "total_wealth": round(total_wealth, 2),
        "days_held": days_held,
        "note": note,
    }


# ---------------------------------------------------------------------------
# Dividend purification
# ---------------------------------------------------------------------------

def calculate_purification(
    dividend_amount: float,
    purification_pct: float,
) -> dict:
    """
    Calculate how much of a dividend must be donated to purify haram income.

    Many Shariah-compliant stocks derive a small portion of revenue from
    impermissible activities (interest income, etc.).  Scholars require
    investors to *purify* dividends by donating the haram percentage to
    charity (not as zakat, but as sadaqah).

    Parameters
    ----------
    dividend_amount : float
        Total gross dividend received.
    purification_pct : float
        Percentage of the company's revenue that is non-compliant
        (e.g., 0.05 for 5 %).  Typically obtained from a Shariah
        screening report.

    Returns
    -------
    dict
        total_dividend, haram_portion, keep_amount, donate_amount, note
    """
    if purification_pct < 0 or purification_pct > 1:
        raise ValueError(
            f"purification_pct must be between 0 and 1, got {purification_pct}"
        )

    donate = round(dividend_amount * purification_pct, 2)
    keep = round(dividend_amount - donate, 2)

    if purification_pct == 0:
        note = "No purification needed — company has 0% impermissible revenue."
    else:
        note = (
            f"{purification_pct * 100:.1f}% of dividend (${donate:,.2f}) should "
            f"be donated to charity as purification. This is not zakat — it is "
            f"sadaqah to cleanse impermissible earnings."
        )

    logger.info(
        "Purification: dividend=$%.2f  pct=%.2f%%  donate=$%.2f  keep=$%.2f",
        dividend_amount, purification_pct * 100, donate, keep,
    )

    return {
        "total_dividend": round(dividend_amount, 2),
        "haram_portion": purification_pct,
        "keep_amount": keep,
        "donate_amount": donate,
        "note": note,
    }


# ======================================================================
# __main__ — quick self-test
# ======================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(message)s")

    # --- Zakat: due ---
    print("\n--- Zakat Calculation (due) ---")
    result = calculate_zakat_due(
        portfolio_value=50_000,
        cash=10_000,
        purchase_date="2025-01-01",
        gold_price_per_gram=70.59,  # ~$6,000 nisab
    )
    for k, v in result.items():
        print(f"  {k}: {v}")

    # --- Zakat: below nisab ---
    print("\n--- Zakat Calculation (below Nisab) ---")
    result2 = calculate_zakat_due(
        portfolio_value=3_000,
        cash=500,
        purchase_date="2025-01-01",
        gold_price_per_gram=70.59,
    )
    for k, v in result2.items():
        print(f"  {k}: {v}")

    # --- Zakat: haul not complete ---
    print("\n--- Zakat Calculation (haul incomplete) ---")
    result3 = calculate_zakat_due(
        portfolio_value=50_000,
        cash=10_000,
        purchase_date=date.today() - timedelta(days=100),
        gold_price_per_gram=70.59,
    )
    for k, v in result3.items():
        print(f"  {k}: {v}")

    # --- Purification ---
    print("\n--- Dividend Purification ---")
    purif = calculate_purification(dividend_amount=1_200.00, purification_pct=0.05)
    for k, v in purif.items():
        print(f"  {k}: {v}")

    purif_zero = calculate_purification(dividend_amount=500.00, purification_pct=0.0)
    for k, v in purif_zero.items():
        print(f"  {k}: {v}")

    purif_high = calculate_purification(dividend_amount=2_000.00, purification_pct=0.12)
    for k, v in purif_high.items():
        print(f"  {k}: {v}")

    print("\nAll zakat calculator tests passed.")
