"""
Tax Engine for Halal Trading Bot
Calculates holding periods, tax liabilities, wash-sale detection,
year-to-date gains tracking, and tax-loss harvesting candidates.
"""

import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Federal tax brackets (2024 rates, simplified single/married thresholds)
# ---------------------------------------------------------------------------

SHORT_TERM_BRACKETS_SINGLE = [
    (11_600, 0.10),
    (47_150, 0.12),
    (100_525, 0.22),
    (191_950, 0.24),
    (243_725, 0.32),
    (609_350, 0.35),
    (float("inf"), 0.37),
]

SHORT_TERM_BRACKETS_MARRIED = [
    (23_200, 0.10),
    (94_300, 0.12),
    (201_050, 0.22),
    (383_900, 0.24),
    (487_450, 0.32),
    (731_200, 0.35),
    (float("inf"), 0.37),
]

LONG_TERM_BRACKETS_SINGLE = [
    (47_025, 0.00),
    (518_900, 0.15),
    (float("inf"), 0.20),
]

LONG_TERM_BRACKETS_MARRIED = [
    (94_050, 0.00),
    (583_750, 0.15),
    (float("inf"), 0.20),
]

# Net Investment Income Tax (NIIT) thresholds
NIIT_RATE = 0.038
NIIT_THRESHOLD_SINGLE = 200_000
NIIT_THRESHOLD_MARRIED = 250_000

# ---------------------------------------------------------------------------
# State tax rates (top marginal, simplified)
# ---------------------------------------------------------------------------

STATE_TAX_RATES = {
    "CA": 0.133,
    "NY": 0.109,
    "NJ": 0.1075,
    "OR": 0.099,
    "MN": 0.0985,
    "HI": 0.11,
    "VT": 0.0875,
    "IA": 0.06,
    "WI": 0.0765,
    "ME": 0.0715,
    "CT": 0.0699,
    "MA": 0.09,       # includes surtax on short-term gains
    "IL": 0.0495,
    "PA": 0.0307,
    "OH": 0.04,
    "GA": 0.055,
    "NC": 0.0475,
    "AZ": 0.025,
    "CO": 0.044,
    "MI": 0.0425,
    "TX": 0.0,
    "FL": 0.0,
    "NV": 0.0,
    "WA": 0.0,        # note: WA has a 7% LTCG tax on gains > $250k
    "WY": 0.0,
    "AK": 0.0,
    "NH": 0.0,
    "SD": 0.0,
    "TN": 0.0,
}

# Large-gain alert threshold
LARGE_GAIN_ALERT_THRESHOLD = 500.0


class TaxEngine:
    """Federal + state tax estimation, wash-sale detection, and harvesting."""

    def __init__(self, default_state: str = "CA", default_filing_status: str = "single"):
        self.default_state = default_state.upper()
        self.default_filing_status = default_filing_status.lower()
        logger.info(
            "TaxEngine initialised  state=%s  filing=%s",
            self.default_state,
            self.default_filing_status,
        )

    # ------------------------------------------------------------------
    # Holding-period helpers
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_holding_period(ticker: str, purchase_date) -> int:
        """Return the number of days held from *purchase_date* until today."""
        if isinstance(purchase_date, str):
            purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
        elif isinstance(purchase_date, datetime):
            purchase_date = purchase_date.date()
        days = (date.today() - purchase_date).days
        logger.debug("%s held for %d days (purchased %s)", ticker, days, purchase_date)
        return days

    @staticmethod
    def is_long_term(ticker: str, purchase_date) -> bool:
        """True when the position qualifies for long-term capital-gains rates."""
        return TaxEngine.calculate_holding_period(ticker, purchase_date) > 365

    @staticmethod
    def days_to_long_term(ticker: str, purchase_date) -> int:
        """Days remaining until a position becomes long-term (0 if already)."""
        held = TaxEngine.calculate_holding_period(ticker, purchase_date)
        remaining = 366 - held
        return max(remaining, 0)

    # ------------------------------------------------------------------
    # Tax-liability estimation
    # ------------------------------------------------------------------

    def estimate_tax_liability(
        self,
        gain: float,
        is_long_term: bool,
        income_bracket: float,
        filing_status: Optional[str] = None,
        state: Optional[str] = None,
    ) -> dict:
        """
        Estimate combined federal + state + NIIT tax on a realised gain.

        Parameters
        ----------
        gain : float
            Realised capital gain (positive = gain, negative = loss).
        is_long_term : bool
            Whether the gain qualifies for long-term rates.
        income_bracket : float
            Approximate total taxable income for the year (used for bracket
            look-up and NIIT threshold).
        filing_status : str, optional
            ``"single"`` or ``"married"`` (defaults to instance default).
        state : str, optional
            Two-letter state code (defaults to instance default).

        Returns
        -------
        dict
            federal_tax, state_tax, niit_tax, total_tax, effective_rate
        """
        filing_status = (filing_status or self.default_filing_status).lower()
        state = (state or self.default_state).upper()

        if gain <= 0:
            return {
                "federal_tax": 0.0,
                "state_tax": 0.0,
                "niit_tax": 0.0,
                "total_tax": 0.0,
                "effective_rate": 0.0,
            }

        # --- Federal ---
        federal_rate = self._marginal_rate(gain, income_bracket, is_long_term, filing_status)
        federal_tax = round(gain * federal_rate, 2)

        # --- NIIT ---
        niit_threshold = (
            NIIT_THRESHOLD_MARRIED if filing_status == "married" else NIIT_THRESHOLD_SINGLE
        )
        niit_tax = round(gain * NIIT_RATE, 2) if income_bracket > niit_threshold else 0.0

        # --- State ---
        state_rate = STATE_TAX_RATES.get(state, 0.05)  # default 5 % if unknown
        state_tax = round(gain * state_rate, 2)

        total_tax = round(federal_tax + state_tax + niit_tax, 2)
        effective_rate = round(total_tax / gain, 4) if gain else 0.0

        return {
            "federal_tax": federal_tax,
            "state_tax": state_tax,
            "niit_tax": niit_tax,
            "total_tax": total_tax,
            "effective_rate": effective_rate,
        }

    # ------------------------------------------------------------------
    # Wash-sale detection
    # ------------------------------------------------------------------

    @staticmethod
    def check_wash_sale(
        ticker: str,
        proposed_action: str,
        trade_log_df: pd.DataFrame,
    ) -> dict:
        """
        Check whether a proposed sale would trigger a wash-sale violation.

        A wash sale occurs when a taxpayer sells a security at a loss and
        purchases a *substantially identical* security within 30 calendar
        days before or after the sale.

        Parameters
        ----------
        ticker : str
            Security symbol.
        proposed_action : str
            ``"sell"`` or ``"buy"``.
        trade_log_df : pd.DataFrame
            Must contain columns ``ticker``, ``action``, ``date``
            (and ideally ``gain`` for sell rows).

        Returns
        -------
        dict  {violation: bool, warning: str}
        """
        proposed_action = proposed_action.lower()
        today = date.today()
        window_start = today - timedelta(days=30)
        window_end = today + timedelta(days=30)

        df = trade_log_df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date

        same_ticker = df[df["ticker"].str.upper() == ticker.upper()]

        if proposed_action == "sell":
            # Selling at a loss? Check for any *buy* of same ticker within window.
            recent_buys = same_ticker[
                (same_ticker["action"].str.lower() == "buy")
                & (same_ticker["date"] >= window_start)
                & (same_ticker["date"] <= window_end)
            ]
            if not recent_buys.empty:
                return {
                    "violation": True,
                    "warning": (
                        f"Wash-sale risk for {ticker}: "
                        f"{len(recent_buys)} buy(s) within 30-day window. "
                        "Loss deduction may be disallowed by IRS."
                    ),
                }

        elif proposed_action == "buy":
            # Buying back after a recent loss sale?
            recent_loss_sells = same_ticker[
                (same_ticker["action"].str.lower() == "sell")
                & (same_ticker["date"] >= window_start)
                & (same_ticker["date"] <= window_end)
            ]
            if "gain" in same_ticker.columns:
                recent_loss_sells = recent_loss_sells[recent_loss_sells["gain"] < 0]

            if not recent_loss_sells.empty:
                return {
                    "violation": True,
                    "warning": (
                        f"Wash-sale risk for {ticker}: "
                        f"buying back within 30 days of a loss sale. "
                        "Loss deduction on the prior sale may be disallowed."
                    ),
                }

        return {"violation": False, "warning": "No wash-sale concern detected."}

    # ------------------------------------------------------------------
    # Year-to-date gains
    # ------------------------------------------------------------------

    def get_ytd_gains(self, trade_log_df: pd.DataFrame) -> dict:
        """
        Summarise year-to-date realised gains from a trade log.

        Parameters
        ----------
        trade_log_df : pd.DataFrame
            Columns: ``ticker``, ``action``, ``date``, ``gain``,
            ``holding_days`` (or ``purchase_date``).

        Returns
        -------
        dict
            short_term_gains, long_term_gains, total_realized, estimated_tax,
            large_gain_alert
        """
        df = trade_log_df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date

        year_start = date(date.today().year, 1, 1)
        ytd = df[(df["action"].str.lower() == "sell") & (df["date"] >= year_start)]

        if ytd.empty:
            return {
                "short_term_gains": 0.0,
                "long_term_gains": 0.0,
                "total_realized": 0.0,
                "estimated_tax": 0.0,
                "large_gain_alert": False,
            }

        # Classify each sell as short- or long-term
        if "holding_days" in ytd.columns:
            st = ytd[ytd["holding_days"] <= 365]["gain"].sum()
            lt = ytd[ytd["holding_days"] > 365]["gain"].sum()
        elif "purchase_date" in ytd.columns:
            ytd = ytd.copy()
            ytd["purchase_date"] = pd.to_datetime(ytd["purchase_date"]).dt.date
            ytd["_held"] = ytd.apply(lambda r: (r["date"] - r["purchase_date"]).days, axis=1)
            st = ytd[ytd["_held"] <= 365]["gain"].sum()
            lt = ytd[ytd["_held"] > 365]["gain"].sum()
        else:
            # Cannot determine — treat all as short-term (conservative)
            st = ytd["gain"].sum()
            lt = 0.0

        total = round(st + lt, 2)

        # Rough tax estimate using defaults
        st_tax = self.estimate_tax_liability(
            max(st, 0), is_long_term=False, income_bracket=100_000
        )["total_tax"]
        lt_tax = self.estimate_tax_liability(
            max(lt, 0), is_long_term=True, income_bracket=100_000
        )["total_tax"]
        estimated_tax = round(st_tax + lt_tax, 2)

        alert = total > LARGE_GAIN_ALERT_THRESHOLD
        if alert:
            logger.warning(
                "LARGE GAIN ALERT: YTD realised gains $%.2f exceed $%.0f threshold",
                total,
                LARGE_GAIN_ALERT_THRESHOLD,
            )

        return {
            "short_term_gains": round(st, 2),
            "long_term_gains": round(lt, 2),
            "total_realized": total,
            "estimated_tax": estimated_tax,
            "large_gain_alert": alert,
        }

    # ------------------------------------------------------------------
    # Tax-loss harvesting candidates
    # ------------------------------------------------------------------

    @staticmethod
    def tax_loss_harvest_candidates(positions: list[dict]) -> list[dict]:
        """
        Identify positions whose unrealised loss makes them harvesting
        candidates.

        Parameters
        ----------
        positions : list[dict]
            Each dict must have ``ticker``, ``purchase_price``,
            ``current_price``, ``shares``, and ``purchase_date``.

        Returns
        -------
        list[dict]
            Sorted by largest unrealised loss first, with extra fields
            ``unrealized_loss``, ``is_long_term``, ``holding_days``.
        """
        candidates = []
        for pos in positions:
            unrealised = round(
                (pos["current_price"] - pos["purchase_price"]) * pos["shares"], 2
            )
            if unrealised >= 0:
                continue  # no loss to harvest

            held = TaxEngine.calculate_holding_period(pos["ticker"], pos["purchase_date"])
            candidates.append(
                {
                    "ticker": pos["ticker"],
                    "shares": pos["shares"],
                    "purchase_price": pos["purchase_price"],
                    "current_price": pos["current_price"],
                    "unrealized_loss": unrealised,
                    "holding_days": held,
                    "is_long_term": held > 365,
                    "purchase_date": str(pos["purchase_date"]),
                }
            )

        candidates.sort(key=lambda c: c["unrealized_loss"])
        return candidates

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _marginal_rate(
        gain: float,
        income: float,
        is_long_term: bool,
        filing_status: str,
    ) -> float:
        """Look up the marginal federal rate for the gain."""
        if is_long_term:
            brackets = (
                LONG_TERM_BRACKETS_MARRIED
                if filing_status == "married"
                else LONG_TERM_BRACKETS_SINGLE
            )
        else:
            brackets = (
                SHORT_TERM_BRACKETS_MARRIED
                if filing_status == "married"
                else SHORT_TERM_BRACKETS_SINGLE
            )

        for threshold, rate in brackets:
            if income <= threshold:
                return rate
        return brackets[-1][1]


# ======================================================================
# __main__ — quick self-test
# ======================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(message)s")

    engine = TaxEngine(default_state="CA", default_filing_status="single")

    # --- Holding period ---
    purchase = "2024-06-15"
    days = engine.calculate_holding_period("AAPL", purchase)
    print(f"\n--- Holding Period ---")
    print(f"AAPL purchased {purchase}: {days} days held")
    print(f"  Long-term?  {engine.is_long_term('AAPL', purchase)}")
    print(f"  Days to LT: {engine.days_to_long_term('AAPL', purchase)}")

    recent = "2025-12-01"
    print(f"MSFT purchased {recent}: {engine.calculate_holding_period('MSFT', recent)} days held")
    print(f"  Long-term?  {engine.is_long_term('MSFT', recent)}")
    print(f"  Days to LT: {engine.days_to_long_term('MSFT', recent)}")

    # --- Tax liability ---
    print(f"\n--- Tax Liability Estimates ---")
    for lt, label in [(False, "short-term"), (True, "long-term")]:
        est = engine.estimate_tax_liability(
            gain=10_000, is_long_term=lt, income_bracket=150_000, state="CA"
        )
        print(f"  $10k {label} gain (CA, $150k income): {est}")

    est_high = engine.estimate_tax_liability(
        gain=50_000, is_long_term=True, income_bracket=300_000,
        filing_status="single", state="NY",
    )
    print(f"  $50k LT gain (NY, $300k single): {est_high}")

    est_tx = engine.estimate_tax_liability(
        gain=10_000, is_long_term=False, income_bracket=80_000, state="TX",
    )
    print(f"  $10k ST gain (TX, $80k): {est_tx}")

    est_loss = engine.estimate_tax_liability(
        gain=-5_000, is_long_term=False, income_bracket=100_000,
    )
    print(f"  -$5k loss: {est_loss}")

    # --- Wash-sale detection ---
    print(f"\n--- Wash-Sale Detection ---")
    log = pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT"],
            "action": ["buy", "sell", "buy"],
            "date": [
                (date.today() - timedelta(days=10)).isoformat(),
                date.today().isoformat(),
                (date.today() - timedelta(days=60)).isoformat(),
            ],
            "gain": [0, -500, 0],
        }
    )
    print(f"  Sell AAPL (recent buy exists): {engine.check_wash_sale('AAPL', 'sell', log)}")
    print(f"  Sell MSFT (no recent buy):    {engine.check_wash_sale('MSFT', 'sell', log)}")
    print(f"  Buy AAPL (recent loss sell):  {engine.check_wash_sale('AAPL', 'buy', log)}")

    # --- YTD gains ---
    print(f"\n--- YTD Gains ---")
    ytd_log = pd.DataFrame(
        {
            "ticker": ["AAPL", "GOOG", "AMZN", "TSLA"],
            "action": ["sell", "sell", "sell", "sell"],
            "date": [
                date.today().isoformat(),
                date.today().isoformat(),
                "2025-06-01",
                date.today().isoformat(),
            ],
            "gain": [300.0, 250.0, 100.0, -200.0],
            "holding_days": [100, 400, 500, 50],
        }
    )
    ytd = engine.get_ytd_gains(ytd_log)
    print(f"  {ytd}")

    # Trigger large-gain alert
    big_log = pd.DataFrame(
        {
            "ticker": ["NVDA"],
            "action": ["sell"],
            "date": [date.today().isoformat()],
            "gain": [5_000.0],
            "holding_days": [200],
        }
    )
    big_ytd = engine.get_ytd_gains(big_log)
    print(f"  Big gain: {big_ytd}")

    # --- Tax-loss harvesting ---
    print(f"\n--- Tax-Loss Harvest Candidates ---")
    positions = [
        {"ticker": "AAPL", "purchase_price": 180, "current_price": 170, "shares": 10, "purchase_date": "2024-01-15"},
        {"ticker": "GOOG", "purchase_price": 140, "current_price": 155, "shares": 5, "purchase_date": "2024-03-01"},
        {"ticker": "TSLA", "purchase_price": 250, "current_price": 210, "shares": 8, "purchase_date": "2025-11-01"},
        {"ticker": "MSFT", "purchase_price": 400, "current_price": 380, "shares": 3, "purchase_date": "2025-09-15"},
    ]
    candidates = engine.tax_loss_harvest_candidates(positions)
    for c in candidates:
        print(f"  {c['ticker']}: loss ${c['unrealized_loss']}, held {c['holding_days']}d, LT={c['is_long_term']}")

    print("\nAll TaxEngine tests passed.")
