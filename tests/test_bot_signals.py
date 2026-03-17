"""
Tests for signal logic — EMA crossover signals from backend.data_fetcher.
"""

import pytest
import pandas as pd
import numpy as np
from backend.data_fetcher import calculate_ema, calculate_signal


class TestGoldenCross:
    def test_golden_cross_buy_signal(self):
        """When EMA20 crosses above EMA50, signal should be BUY."""
        # Build a price series where prices are low then rise sharply,
        # causing the short EMA to cross above the long EMA at the end.
        n = 80
        prices = pd.Series(
            [50.0] * 50 + [50.0 + i * 2.0 for i in range(1, n - 50 + 1)]
        )
        # Verify precondition: the last two EMA20/EMA50 values cross
        ema20 = calculate_ema(prices, 20)
        ema50 = calculate_ema(prices, 50)
        # Force a clean crossover by adjusting the second-to-last price
        # so that ema20[-2] <= ema50[-2] and ema20[-1] > ema50[-1].
        # The ramp above should naturally produce this — verify:
        if not (ema20.iloc[-2] <= ema50.iloc[-2] and ema20.iloc[-1] > ema50.iloc[-1]):
            # Construct a guaranteed crossover series
            flat = [100.0] * 60
            ramp = [100.0 + (i ** 2) * 0.5 for i in range(1, 21)]
            prices = pd.Series(flat + ramp)

        signal, confidence = calculate_signal(prices)
        assert signal == "BUY"
        assert confidence >= 0


class TestDeathCross:
    def test_death_cross_sell_signal(self):
        """When EMA20 crosses below EMA50, signal should be SELL."""
        # Prices start high then drop sharply → short EMA crosses below long EMA.
        high = [200.0] * 60
        drop = [200.0 - (i ** 2) * 0.5 for i in range(1, 21)]
        prices = pd.Series(high + drop)

        signal, confidence = calculate_signal(prices)
        assert signal == "SELL"
        assert confidence >= 0


class TestHoldSignal:
    def test_no_crossover_hold(self):
        """When EMAs are parallel (no crossover), signal should be HOLD."""
        # Steady uptrend — EMA20 stays above EMA50, no crossover event
        prices = pd.Series([100.0 + i * 0.5 for i in range(80)])
        signal, confidence = calculate_signal(prices)
        assert signal == "HOLD"

    def test_insufficient_data_hold(self):
        """With fewer than 50 data points, signal should be HOLD with 0 confidence."""
        prices = pd.Series([100.0 + i for i in range(30)])
        signal, confidence = calculate_signal(prices)
        assert signal == "HOLD"
        assert confidence == 0.0


class TestEMACalculation:
    def test_ema_calculation(self):
        """Verify EMA math against a known manual calculation."""
        prices = pd.Series([10.0, 11.0, 12.0, 11.0, 13.0])
        span = 3
        ema = calculate_ema(prices, span)

        # Manual EMA (span=3, multiplier = 2/(3+1) = 0.5):
        # EMA[0] = 10.0
        # EMA[1] = 11.0 * 0.5 + 10.0 * 0.5 = 10.5
        # EMA[2] = 12.0 * 0.5 + 10.5 * 0.5 = 11.25
        # EMA[3] = 11.0 * 0.5 + 11.25 * 0.5 = 11.125
        # EMA[4] = 13.0 * 0.5 + 11.125 * 0.5 = 12.0625
        assert ema.iloc[0] == pytest.approx(10.0)
        assert ema.iloc[1] == pytest.approx(10.5)
        assert ema.iloc[2] == pytest.approx(11.25)
        assert ema.iloc[3] == pytest.approx(11.125)
        assert ema.iloc[4] == pytest.approx(12.0625)
