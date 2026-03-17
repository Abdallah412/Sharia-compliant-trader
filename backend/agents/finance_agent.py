"""
Finance Agent — CFA-level quantitative analyst.
Produces BUY/HOLD/SELL signals with position-sizing guidance.
Uses Sonnet for balanced reasoning capability.
"""

import json
import logging

from agents.base_agent import call_agent_json

logger = logging.getLogger("finance_agent")

SYSTEM_PROMPT = """\
You are a CFA-level quantitative analyst with 20 years of equity market experience.
Your goal: maximize risk-adjusted returns for a growth portfolio targeting 15-25%
annualized returns with Sharpe ratio > 1.0.

SIGNAL RULES:
- BUY: EMA20 crosses above EMA50 (golden cross) + news sentiment > -20 + no earnings
  within 3 days + VIX < 30
- SELL: EMA20 crosses below EMA50 (death cross) + news sentiment < 20
- HOLD: No crossover, or conflicting signals

NEWS EVENT OVERRIDES (bypass EMA, trigger immediately):
- IMMEDIATE BUY: Earnings beat > 10%, major AI/tech contract, 3+ analyst upgrades
- IMMEDIATE SELL: CEO resignation/fraud, earnings miss > 10% + guidance cut,
  FDA rejection, DOJ investigation
- ALWAYS IGNORE (gharar/maysir): Unconfirmed rumors, Reddit hype, short squeezes

CONFIDENCE SCORING:
- 80-100: EMA + news + earnings all agree → full position
- 60-79: EMA confirmed, news neutral → 75% position
- 40-59: EMA only, no news confirmation → 50% position
- 20-39: Weak signal → 25% position or hold
- 0-19: Conflicting signals → do not enter (gharar risk)

Respond ONLY with valid JSON:
{
  "signal": "BUY" | "HOLD" | "SELL",
  "confidence": 0-100,
  "position_size_multiplier": 0.0-1.0,
  "expected_return_low_pct": -50.0,
  "expected_return_high_pct": 50.0,
  "time_horizon_days": 30,
  "primary_reason": "one sentence",
  "supporting_factors": ["bullish/bearish factors"],
  "risk_factors": ["key risks"],
  "news_driven": false,
  "recommendation": "EXECUTE" | "WAIT_FOR_CONFIRMATION" | "SKIP"
}
"""

MODEL = "claude-sonnet-4-6"


def evaluate(
    ticker: str,
    current_price: float,
    ema20: float,
    ema50: float,
    ema_signal: str,
    news_sentiment_score: float,
    top_headlines: list[str],
    earnings_surprise_pct: float = 0.0,
    forward_pe: float = 0.0,
    analyst_consensus: str = "none",
    vix_level: float = 20.0,
    macro_summary: str = "No macro data available.",
) -> dict:
    """Produce a quantitative trading signal for the given equity."""
    logger.info("Evaluating financial signal for %s at $%.2f", ticker, current_price)

    user_message = json.dumps({
        "ticker": ticker,
        "current_price": current_price,
        "ema20": ema20,
        "ema50": ema50,
        "ema_signal": ema_signal,
        "news_sentiment_score": news_sentiment_score,
        "top_headlines": top_headlines[:5],
        "earnings_surprise_pct": earnings_surprise_pct,
        "forward_pe": forward_pe,
        "analyst_consensus": analyst_consensus,
        "vix_level": vix_level,
        "macro_summary": macro_summary,
    })

    parsed, meta = call_agent_json(SYSTEM_PROMPT, user_message, model=MODEL, max_tokens=700)

    # Validate signal
    if parsed.get("signal") not in ("BUY", "HOLD", "SELL"):
        parsed["signal"] = "HOLD"
    if "confidence" in parsed:
        parsed["confidence"] = max(0, min(100, int(parsed["confidence"])))

    logger.info("Finance signal for %s: %s (confidence %s)",
                ticker, parsed.get("signal"), parsed.get("confidence"))
    parsed["_meta"] = meta
    return parsed
