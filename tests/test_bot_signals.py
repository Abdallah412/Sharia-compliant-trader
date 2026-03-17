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
        # Strategy: start with a long downtrend (EMA20 well below EMA50),
        # then inject a single massive spike on the last price so EMA20
        # jumps above EMA50 on the final bar while the second-to-last bar
        # still has EMA20 <= EMA50.
        n = 70
        # Gentle downtrend for most of the series
        base = [100.0 - i * 0.3 for i in range(n)]
        prices = pd.Series(base)

        # Verify that EMA20 < EMA50 at position -1 (before we add the spike)
        ema20 = calculate_ema(prices, 20)
        ema50 = calculate_ema(prices, 50)
        gap = ema50.iloc[-1] - ema20.iloc[-1]

        # Add a big spike that will push EMA20 above EMA50
        # EMA20 multiplier = 2/21 ≈ 0.095, so new_ema20 ≈ spike*0.095 + old*0.905
        # We need: spike * 0.095 + ema20_now * 0.905 > ema50_now (roughly)
        spike_needed = (ema50.iloc[-1] - ema20.iloc[-1] * 0.905) / 0.095 + 50
        prices = pd.concat([prices, pd.Series([spike_needed])], ignore_index=True)

        signal, confidence = calculate_signal(prices)
        assert signal == "BUY"
        assert confidence >= 0


class TestDeathCross:
    def test_death_cross_sell_signal(self):
        """When EMA20 crosses below EMA50, signal should be SELL."""
        # Strategy: start with a gentle uptrend (EMA20 above EMA50),
        # then inject a massive drop on the last bar so EMA20 falls
        # below EMA50.
        n = 70
        base = [100.0 + i * 0.3 for i in range(n)]
        prices = pd.Series(base)

        ema20 = calculate_ema(prices, 20)
        ema50 = calculate_ema(prices, 50)

        # EMA20 multiplier = 2/21 ≈ 0.095
        # We need: drop * 0.095 + ema20_now * 0.905 < ema50_now (roughly)
        drop_needed = (ema50.iloc[-1] - ema20.iloc[-1] * 0.905) / 0.095 - 50
        prices = pd.concat([prices, pd.Series([drop_needed])], ignore_index=True)

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
