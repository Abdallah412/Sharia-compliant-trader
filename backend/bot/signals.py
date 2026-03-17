"""
EMA calculation and crossover signal detection.
Pure math — no external API calls.
"""

import pandas as pd


def calculate_ema(prices: pd.Series, span: int = 20) -> pd.Series:
    """Exponential Moving Average."""
    return prices.ewm(span=span, adjust=False).mean()


def detect_signal(prices: pd.Series) -> dict:
    """
    Detect EMA20/EMA50 crossover signal from a price series.
    Returns dict with signal, confidence, ema20, ema50.
    """
    if len(prices) < 50:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "ema20": None,
            "ema50": None,
            "reason": "Insufficient data (need 50+ days)",
        }

    ema20 = calculate_ema(prices, 20)
    ema50 = calculate_ema(prices, 50)

    current_ema20 = float(ema20.iloc[-1])
    current_ema50 = float(ema50.iloc[-1])
    prev_ema20 = float(ema20.iloc[-2])
    prev_ema50 = float(ema50.iloc[-2])

    current_price = float(prices.iloc[-1])
    spread = abs(current_ema20 - current_ema50) / current_price * 100

    # Golden cross: EMA20 crosses above EMA50
    if prev_ema20 <= prev_ema50 and current_ema20 > current_ema50:
        confidence = min(100, int(spread * 20))
        return {
            "signal": "BUY",
            "confidence": max(20, confidence),
            "ema20": round(current_ema20, 2),
            "ema50": round(current_ema50, 2),
            "reason": f"Golden cross: EMA20 ({current_ema20:.2f}) crossed above EMA50 ({current_ema50:.2f})",
        }

    # Death cross: EMA20 crosses below EMA50
    if prev_ema20 >= prev_ema50 and current_ema20 < current_ema50:
        confidence = min(100, int(spread * 20))
        return {
            "signal": "SELL",
            "confidence": max(20, confidence),
            "ema20": round(current_ema20, 2),
            "ema50": round(current_ema50, 2),
            "reason": f"Death cross: EMA20 ({current_ema20:.2f}) crossed below EMA50 ({current_ema50:.2f})",
        }

    # No crossover — HOLD
    if current_ema20 > current_ema50:
        reason = "EMA20 above EMA50 (bullish trend, no fresh crossover)"
    else:
        reason = "EMA20 below EMA50 (bearish trend, no fresh crossover)"

    return {
        "signal": "HOLD",
        "confidence": 0,
        "ema20": round(current_ema20, 2),
        "ema50": round(current_ema50, 2),
        "reason": reason,
    }


def calculate_position_qty(
    portfolio_value: float,
    ticker: str,
    is_etf: bool,
    multiplier: float,
    current_price: float,
) -> int:
    """Calculate position size in whole shares."""
    MAX_PCT = 0.40 if is_etf else 0.20
    CASH_RESERVE = 0.10
    available = portfolio_value * (1 - CASH_RESERVE)
    target_dollars = portfolio_value * MAX_PCT * multiplier
    invest = min(target_dollars, available)
    qty = int(invest // current_price) if current_price > 0 else 0
    return max(qty, 0)
