"""
Finance Agent — CFA-level quantitative analyst.
Produces BUY/HOLD/SELL signals with position-sizing guidance.
"""

import anthropic
import json
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("finance_agent")

SYSTEM_PROMPT = """You are a CFA-level quantitative analyst with 20 years of experience in equity markets. \
You target 15-25% annualized returns with a Sharpe ratio above 1.0. You combine technical analysis \
(EMA crossovers, momentum), fundamental analysis (earnings, PE ratios, analyst consensus), \
sentiment analysis (news headlines, scores), and macro context (VIX, economic summary) to produce \
a single actionable trading signal.

You MUST respond with ONLY a valid JSON object (no markdown, no explanation outside JSON) with these fields:
- signal: "BUY" | "HOLD" | "SELL"
- confidence: integer 0-100
- expected_return_low: float — low end of expected return percentage over time_horizon_days
- expected_return_high: float — high end of expected return percentage over time_horizon_days
- position_size_multiplier: float 0.0-1.0 — fraction of standard position size to allocate
- time_horizon_days: integer — recommended holding period in days
- primary_reason: string explaining the main driver of the signal
- supporting_factors: list of strings with additional bullish/bearish factors
- risk_factors: list of strings with key risks to the thesis
- macro_context: string summarising the macro environment impact
- recommendation: "EXECUTE" | "WAIT_FOR_CONFIRMATION" | "SKIP"
"""

client = anthropic.Anthropic()


def call_agent(system_prompt: str, user_message: str) -> dict:
    """Call the Anthropic API and parse the JSON response."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    text = response.content[0].text
    return json.loads(text)


def evaluate(
    ticker: str,
    current_price: float,
    ema20: float,
    ema50: float,
    ema_signal: str,
    news_sentiment_score: float,
    top_headlines: list[str],
    earnings_surprise_pct: float,
    forward_pe: float,
    analyst_consensus: str,
    vix_level: float,
    macro_summary: str,
) -> dict:
    """Produce a quantitative trading signal for the given equity."""
    logger.info("Evaluating financial signal for %s at $%.2f", ticker, current_price)

    user_message = json.dumps(
        {
            "ticker": ticker,
            "current_price": current_price,
            "ema20": ema20,
            "ema50": ema50,
            "ema_signal": ema_signal,
            "news_sentiment_score": news_sentiment_score,
            "top_headlines": top_headlines,
            "earnings_surprise_pct": earnings_surprise_pct,
            "forward_pe": forward_pe,
            "analyst_consensus": analyst_consensus,
            "vix_level": vix_level,
            "macro_summary": macro_summary,
        }
    )

    try:
        result = call_agent(SYSTEM_PROMPT, user_message)
        logger.info("Finance signal for %s: %s (confidence %s)", ticker, result.get("signal"), result.get("confidence"))
        return result
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Finance agent response as JSON: %s", e)
        return {
            "signal": "HOLD",
            "confidence": 0,
            "expected_return_low": 0.0,
            "expected_return_high": 0.0,
            "position_size_multiplier": 0.0,
            "time_horizon_days": 0,
            "primary_reason": f"Agent response parsing error: {e}",
            "supporting_factors": [],
            "risk_factors": ["parse_error"],
            "macro_context": "",
            "recommendation": "SKIP",
        }
    except Exception as e:
        logger.error("Finance agent error for %s: %s", ticker, e)
        raise


if __name__ == "__main__":
    import yfinance as yf
    import pandas as pd

    if len(sys.argv) < 2:
        print("Usage: python finance_agent.py <TICKER>")
        sys.exit(1)

    ticker_symbol = sys.argv[1].upper()
    logger.info("Fetching data for %s via yfinance", ticker_symbol)

    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    hist = stock.history(period="3mo")

    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0

    ema20 = float(hist["Close"].ewm(span=20, adjust=False).mean().iloc[-1]) if len(hist) >= 20 else current_price
    ema50 = float(hist["Close"].ewm(span=50, adjust=False).mean().iloc[-1]) if len(hist) >= 50 else current_price

    if ema20 > ema50:
        ema_signal = "BULLISH_CROSSOVER"
    elif ema20 < ema50:
        ema_signal = "BEARISH_CROSSOVER"
    else:
        ema_signal = "NEUTRAL"

    forward_pe = info.get("forwardPE", 0.0) or 0.0
    analyst_consensus = info.get("recommendationKey", "none") or "none"

    result = evaluate(
        ticker=ticker_symbol,
        current_price=current_price,
        ema20=round(ema20, 2),
        ema50=round(ema50, 2),
        ema_signal=ema_signal,
        news_sentiment_score=0.0,
        top_headlines=[],
        earnings_surprise_pct=0.0,
        forward_pe=forward_pe,
        analyst_consensus=analyst_consensus,
        vix_level=0.0,
        macro_summary="No macro data available.",
    )

    print(json.dumps(result, indent=2))
