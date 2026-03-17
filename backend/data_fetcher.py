"""
Module 3: Market Data Fetcher
Fetches price history, fundamentals, earnings calendar, and macro data.
"""

import os
import logging
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FRED_API_KEY = os.getenv("FRED_API_KEY", "")


def get_price_history(ticker: str, days: int = 90) -> pd.DataFrame:
    """Returns OHLCV DataFrame with columns: date, open, high, low, close, volume."""
    try:
        stock = yf.Ticker(ticker)
        period = f"{days}d" if days <= 365 else f"{days // 365}y"
        df = stock.history(period=period)

        if df.empty:
            logger.warning("No price history for %s", ticker)
            return pd.DataFrame()

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"index": "date"})

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        logger.error("Failed to get price history for %s: %s", ticker, e)
        return pd.DataFrame()


def get_current_price(ticker: str) -> float:
    """Returns the current/last known price for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0.0)
        return float(price)
    except Exception as e:
        logger.error("Failed to get current price for %s: %s", ticker, e)
        return 0.0


def get_fundamentals(ticker: str) -> dict:
    """Returns key fundamental data for analysis."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "marketCap": info.get("marketCap", 0),
            "totalDebt": info.get("totalDebt", 0),
            "cash": info.get("totalCash", 0),
            "shortTermInvestments": info.get("shortTermInvestments", 0),
            "netReceivables": info.get("netReceivables", 0),
            "totalAssets": info.get("totalAssets", 0),
            "totalRevenue": info.get("totalRevenue", 0),
            "trailingEPS": info.get("trailingEps", 0),
            "forwardPE": info.get("forwardPE", 0),
            "dividendYield": info.get("dividendYield", 0),
            "totalStockholderEquity": info.get("totalStockholderEquity", 0),
            "interestExpense": info.get("interestExpense", 0),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "longName": info.get("longName", ""),
        }
    except Exception as e:
        logger.error("Failed to get fundamentals for %s: %s", ticker, e)
        return {}


def get_earnings_calendar(ticker: str) -> dict:
    """Returns next earnings date — bot avoids buying within 3 days of earnings."""
    try:
        stock = yf.Ticker(ticker)
        cal = stock.calendar
        if cal is not None and isinstance(cal, dict):
            earnings_date = cal.get("Earnings Date")
            if earnings_date:
                if isinstance(earnings_date, list) and earnings_date:
                    next_date = earnings_date[0]
                else:
                    next_date = earnings_date
                days_until = (pd.Timestamp(next_date).tz_localize(None) - pd.Timestamp.now()).days
                return {
                    "next_earnings_date": str(next_date),
                    "days_until_earnings": max(days_until, 0),
                    "too_close": days_until <= 3 and days_until >= 0,
                }
        return {"next_earnings_date": None, "days_until_earnings": None, "too_close": False}
    except Exception as e:
        logger.warning("Failed to get earnings calendar for %s: %s", ticker, e)
        return {"next_earnings_date": None, "days_until_earnings": None, "too_close": False}


def get_macro_data() -> dict:
    """
    Fetch macro indicators from FRED API.
    High VIX (> 30): pause new buys. Fed rate cuts: bullish for tech.
    """
    result = {
        "fed_funds_rate": None,
        "cpi_yoy": None,
        "unemployment_rate": None,
        "vix": None,
        "macro_risk": "unknown",
    }

    # Get VIX from yfinance
    try:
        vix = yf.Ticker("^VIX")
        vix_info = vix.info
        result["vix"] = vix_info.get("regularMarketPrice") or vix_info.get("previousClose")
    except Exception as e:
        logger.warning("Failed to get VIX: %s", e)

    # Get FRED data if API key available
    if FRED_API_KEY:
        fred_series = {
            "fed_funds_rate": "FEDFUNDS",
            "cpi_yoy": "CPIAUCSL",
            "unemployment_rate": "UNRATE",
        }
        for key, series_id in fred_series.items():
            try:
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": series_id,
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                }
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()
                observations = data.get("observations", [])
                if observations:
                    result[key] = float(observations[0]["value"])
            except Exception as e:
                logger.warning("Failed to get FRED %s: %s", series_id, e)

    # Assess macro risk
    vix = result.get("vix")
    if vix is not None:
        if vix > 30:
            result["macro_risk"] = "high"
        elif vix > 20:
            result["macro_risk"] = "elevated"
        else:
            result["macro_risk"] = "normal"

    return result


def calculate_ema(prices: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average."""
    return prices.ewm(span=span, adjust=False).mean()


def calculate_signal(prices: pd.Series) -> tuple:
    """
    Returns (signal, confidence) based on EMA20/EMA50 crossover.
    signal = 'BUY' | 'SELL' | 'HOLD'
    confidence = how far apart the EMAs are as % of price
    """
    if len(prices) < 50:
        return ("HOLD", 0.0)

    ema20 = calculate_ema(prices, 20)
    ema50 = calculate_ema(prices, 50)

    current_price = prices.iloc[-1]
    ema20_now = ema20.iloc[-1]
    ema50_now = ema50.iloc[-1]
    ema20_prev = ema20.iloc[-2]
    ema50_prev = ema50.iloc[-2]

    spread = abs(ema20_now - ema50_now) / current_price * 100
    confidence = min(round(spread * 20, 1), 100.0)

    # Golden cross: EMA20 crosses above EMA50
    if ema20_prev <= ema50_prev and ema20_now > ema50_now:
        return ("BUY", confidence)

    # Death cross: EMA20 crosses below EMA50
    if ema20_prev >= ema50_prev and ema20_now < ema50_now:
        return ("SELL", confidence)

    # Trending
    if ema20_now > ema50_now:
        return ("HOLD", confidence)  # Uptrend, hold
    else:
        return ("HOLD", confidence)  # Downtrend, hold


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

    print(f"\n=== Data Fetcher: {ticker} ===\n")

    df = get_price_history(ticker, 90)
    print(f"Price history: {len(df)} rows")
    if not df.empty:
        print(df.tail(5).to_string(index=False))

    price = get_current_price(ticker)
    print(f"\nCurrent price: ${price:.2f}")

    if not df.empty:
        signal, confidence = calculate_signal(df["close"])
        print(f"Signal: {signal} (confidence: {confidence}%)")

    fundamentals = get_fundamentals(ticker)
    print(f"\nMarket cap: ${fundamentals.get('marketCap', 0):,.0f}")
    print(f"Forward P/E: {fundamentals.get('forwardPE', 'N/A')}")

    earnings = get_earnings_calendar(ticker)
    print(f"\nNext earnings: {earnings.get('next_earnings_date')}")
    print(f"Too close to earnings: {earnings.get('too_close')}")

    macro = get_macro_data()
    print(f"\nVIX: {macro.get('vix')}")
    print(f"Macro risk: {macro.get('macro_risk')}")
