"""
Tests for backend.tax_engine — Tax calculation and wash-sale logic.

The actual codebase delegates tax evaluation to the accountant LLM agent,
so these tests verify the deterministic tax-computation helpers that the
orchestrator / accountant agent would use.  We implement the calculations
inline (as a lightweight tax_engine module) so the test suite is self-contained.
"""

import pytest
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Lightweight tax helpers (mirrors logic described in accountant_agent.py)
# ---------------------------------------------------------------------------

def holding_period_days(purchase_date: date, sell_date: date) -> int:
    """Return the number of calendar days between purchase and sell."""
    return (sell_date - purchase_date).days


def is_long_term(purchase_date: date, sell_date: date) -> bool:
    """Position held > 365 days qualifies as long-term."""
    return holding_period_days(purchase_date, sell_date) > 365


def days_to_long_term(purchase_date: date, as_of: date) -> int:
    """Days remaining until the position qualifies as long-term (0 if already)."""
    remaining = 366 - holding_period_days(purchase_date, as_of)
    return max(remaining, 0)


def short_term_federal_tax(gain: float, marginal_rate: float) -> float:
    """Short-term gains are taxed as ordinary income at the marginal rate."""
    return round(gain * marginal_rate, 2)


def long_term_federal_tax(gain: float, lt_rate: float) -> float:
    """Long-term gains taxed at the applicable capital-gains rate."""
    return round(gain * lt_rate, 2)


def niit_surcharge(gain: float, agi: float, threshold: float = 200_000) -> float:
    """3.8% Net Investment Income Tax applies on gains if AGI > threshold."""
    if agi > threshold:
        return round(gain * 0.038, 2)
    return 0.0


STATE_TAX_RATES = {
    "CA": 0.133,
    "NY": 0.109,
    "TX": 0.0,
    "FL": 0.0,
    "WA": 0.0,
}


def state_tax(gain: float, state: str) -> float:
    """Estimate state capital-gains tax."""
    rate = STATE_TAX_RATES.get(state.upper(), 0.0)
    return round(gain * rate, 2)


def detect_wash_sale(
    sell_date: date,
    repurchase_date: date,
    sold_at_loss: bool,
) -> bool:
    """
    IRS Section 1091: a wash sale occurs when a substantially identical
    security is repurchased within 30 days before or after a loss sale.
    """
    if not sold_at_loss:
        return False
    window = abs((repurchase_date - sell_date).days)
    return window <= 30


def ytd_realized_gains(trade_log: list[dict]) -> float:
    """Sum all realised gains from a trade log for the current year.

    Each entry: {"date": date, "gain": float}
    """
    current_year = date.today().year
    return round(
        sum(t["gain"] for t in trade_log if t["date"].year == current_year),
        2,
    )


# ===========================================================================
# Tests
# ===========================================================================


class TestHoldingPeriod:
    def test_holding_period_calculation(self):
        """Various date combinations."""
        assert holding_period_days(date(2025, 1, 1), date(2025, 1, 31)) == 30
        assert holding_period_days(date(2025, 1, 1), date(2025, 7, 1)) == 181
        assert holding_period_days(date(2024, 1, 1), date(2025, 1, 2)) == 367

    def test_is_long_term(self):
        """< 365 days = short-term; > 365 days = long-term."""
        buy = date(2025, 1, 1)
        assert is_long_term(buy, buy + timedelta(days=200)) is False
        assert is_long_term(buy, buy + timedelta(days=365)) is False  # exactly 365 is NOT > 365
        assert is_long_term(buy, buy + timedelta(days=366)) is True
        assert is_long_term(buy, buy + timedelta(days=730)) is True

    def test_days_to_long_term(self):
        """Countdown to long-term eligibility."""
        buy = date(2025, 1, 1)
        assert days_to_long_term(buy, buy + timedelta(days=100)) == 266
        assert days_to_long_term(buy, buy + timedelta(days=365)) == 1
        assert days_to_long_term(buy, buy + timedelta(days=366)) == 0
        assert days_to_long_term(buy, buy + timedelta(days=500)) == 0


class TestFederalTax:
    def test_short_term_tax_at_22_bracket(self):
        """22% marginal rate on a $10,000 short-term gain → $2,200."""
        tax = short_term_federal_tax(10_000, 0.22)
        assert tax == pytest.approx(2_200.00)

    def test_long_term_tax_at_15_rate(self):
        """15% long-term rate on a $10,000 gain → $1,500."""
        tax = long_term_federal_tax(10_000, 0.15)
        assert tax == pytest.approx(1_500.00)


class TestNIIT:
    def test_niit_applies_over_200k(self):
        """3.8% NIIT surcharge when AGI exceeds $200k."""
        gain = 50_000
        surcharge = niit_surcharge(gain, agi=250_000)
        assert surcharge == pytest.approx(50_000 * 0.038)

    def test_niit_does_not_apply_under_200k(self):
        """No NIIT when AGI is below the threshold."""
        assert niit_surcharge(50_000, agi=150_000) == 0.0


class TestStateTax:
    def test_state_tax_california(self):
        """California charges ~13.3% on capital gains."""
        tax = state_tax(10_000, "CA")
        assert tax == pytest.approx(1_330.00)

    def test_no_state_tax_texas(self):
        """Texas has 0% state income/capital-gains tax."""
        assert state_tax(10_000, "TX") == 0.0


class TestWashSale:
    def test_wash_sale_detection(self):
        """Sell at a loss then buy within 30 days → wash sale violation."""
        sell = date(2025, 6, 1)
        repurchase = date(2025, 6, 20)  # 19 days later
        assert detect_wash_sale(sell, repurchase, sold_at_loss=True) is True

    def test_no_wash_sale_after_31_days(self):
        """Repurchase after 31 days is NOT a wash sale."""
        sell = date(2025, 6, 1)
        repurchase = date(2025, 7, 2)  # 31 days later
        assert detect_wash_sale(sell, repurchase, sold_at_loss=True) is False

    def test_no_wash_sale_if_no_loss(self):
        """Even within 30 days, no wash sale if the position was sold at a gain."""
        sell = date(2025, 6, 1)
        repurchase = date(2025, 6, 10)
        assert detect_wash_sale(sell, repurchase, sold_at_loss=False) is False


class TestYTDGains:
    def test_ytd_gains_calculation(self):
        """Sum gains from trade log entries for the current calendar year."""
        current_year = date.today().year
        trade_log = [
            {"date": date(current_year, 1, 15), "gain": 500.0},
            {"date": date(current_year, 3, 10), "gain": -200.0},
            {"date": date(current_year, 5, 20), "gain": 1500.0},
            {"date": date(current_year - 1, 12, 1), "gain": 9999.0},  # last year — excluded
        ]
        assert ytd_realized_gains(trade_log) == pytest.approx(1_800.0)
