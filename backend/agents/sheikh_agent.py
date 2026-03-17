"""
Sheikh Agent — Sunni Muslim scholar specializing in Islamic finance.
Screens equities for Shariah compliance using AAOIFI standards.
"""

import anthropic
import json
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("sheikh_agent")

SYSTEM_PROMPT = """You are a Sunni Muslim scholar specializing in Islamic finance (fiqh al-mu'amalat). \
You strictly follow the Accounting and Auditing Organization for Islamic Financial Institutions (AAOIFI) \
Shariah standards for equity screening.

You apply the following prohibitions rigorously:
- Riba (interest/usury) — any interest-bearing debt or interest income must be evaluated.
- Gharar (excessive uncertainty) — speculative or opaque business models are suspect.
- Maysir (gambling) — revenue from gambling, lotteries, or speculation is haram.

You use the 30% financial-ratio thresholds derived from the hadith of Sa'd ibn Abi Waqqas \
(reported in Sahih Muslim) which permits up to one-third:
- Total debt / trailing 36-month average market capitalisation < 30%
- Cash + interest-bearing securities / trailing 36-month average market capitalisation < 30%
- Revenue from impermissible activities / total revenue < 5% (strict) or < 30% (lenient)

You MUST respond with ONLY a valid JSON object (no markdown, no explanation outside JSON) with these fields:
- verdict: "HALAL" | "DOUBTFUL" | "HARAM"
- confidence: integer 0-100
- primary_reason: string explaining the main basis for the verdict
- screens_passed: list of strings naming each screen that passed
- screens_failed: list of strings naming each screen that failed
- madhab_notes: string with any relevant school-of-thought differences
- purification_pct: float — percentage of dividends to purify (donate) due to impermissible income
- scholarly_concerns: string with any reservations or minority opinions
- recommendation: "PROCEED" | "REVIEW_MANUALLY" | "DO_NOT_INVEST"
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
    sector: str,
    industry: str,
    debt_ratio: float,
    cash_ratio: float,
    revenue_total: float,
    revenue_impermissible: float,
    dividend_yield: float,
    scholarly_flags: list[str] | None = None,
) -> dict:
    """Run a Shariah compliance screen on the given equity."""
    logger.info("Evaluating Shariah compliance for %s", ticker)

    impermissible_revenue_pct = (
        (revenue_impermissible / revenue_total * 100) if revenue_total > 0 else 0.0
    )

    user_message = json.dumps(
        {
            "ticker": ticker,
            "sector": sector,
            "industry": industry,
            "debt_ratio_pct": round(debt_ratio * 100, 2),
            "cash_ratio_pct": round(cash_ratio * 100, 2),
            "revenue_total": revenue_total,
            "revenue_impermissible": revenue_impermissible,
            "impermissible_revenue_pct": round(impermissible_revenue_pct, 2),
            "dividend_yield_pct": round(dividend_yield * 100, 2),
            "scholarly_flags": scholarly_flags or [],
        }
    )

    try:
        result = call_agent(SYSTEM_PROMPT, user_message)
        logger.info("Sheikh verdict for %s: %s (confidence %s)", ticker, result.get("verdict"), result.get("confidence"))
        return result
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Sheikh agent response as JSON: %s", e)
        return {
            "verdict": "DOUBTFUL",
            "confidence": 0,
            "primary_reason": f"Agent response parsing error: {e}",
            "screens_passed": [],
            "screens_failed": ["parse_error"],
            "madhab_notes": "",
            "purification_pct": 0.0,
            "scholarly_concerns": "Unable to evaluate — agent returned invalid JSON.",
            "recommendation": "REVIEW_MANUALLY",
        }
    except Exception as e:
        logger.error("Sheikh agent error for %s: %s", ticker, e)
        raise


if __name__ == "__main__":
    import yfinance as yf

    if len(sys.argv) < 2:
        print("Usage: python sheikh_agent.py <TICKER>")
        sys.exit(1)

    ticker_symbol = sys.argv[1].upper()
    logger.info("Fetching data for %s via yfinance", ticker_symbol)

    stock = yf.Ticker(ticker_symbol)
    info = stock.info

    total_debt = info.get("totalDebt", 0) or 0
    market_cap = info.get("marketCap", 1) or 1
    cash_and_equivalents = (info.get("totalCash", 0) or 0) + (info.get("shortTermInvestments", 0) or 0)
    total_revenue = info.get("totalRevenue", 0) or 0
    div_yield = info.get("dividendYield", 0) or 0

    debt_r = total_debt / market_cap if market_cap else 0
    cash_r = cash_and_equivalents / market_cap if market_cap else 0

    result = evaluate(
        ticker=ticker_symbol,
        sector=info.get("sector", "Unknown"),
        industry=info.get("industry", "Unknown"),
        debt_ratio=debt_r,
        cash_ratio=cash_r,
        revenue_total=total_revenue,
        revenue_impermissible=0.0,
        dividend_yield=div_yield,
        scholarly_flags=[],
    )

    print(json.dumps(result, indent=2))
