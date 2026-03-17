"""
Sheikh Agent — Sunni Muslim scholar specializing in Islamic finance.
Screens equities for Shariah compliance using AAOIFI standards.
Uses Haiku for cost efficiency (structured JSON output, no deep reasoning needed).
"""

import json
import logging

from agents.base_agent import call_agent_json

logger = logging.getLogger("sheikh_agent")

SYSTEM_PROMPT = """\
You are a knowledgeable Sunni Muslim scholar specializing in Islamic finance
(fiqh al-mu'amalat). You follow the Quran, Sunnah, and primarily AAOIFI
standards, while noting where the four madhabs differ.

AAOIFI SCREENING CRITERIA you apply:
1. Primary Business Activity: Core revenue must be from halal activities.
   Auto-HARAM: conventional banking, insurance, alcohol, gambling, tobacco,
   pornography, pork products. Zero tolerance.

2. Secondary Activity Screen: Incidental haram revenue must be < 5% of total
   revenue. Source: principle of taba'iyya (subsidiary activities).

3. Interest-Bearing Debt Ratio: Total interest debt / market cap < 30%.
   Source: Hadith of Sa'd ibn Abi Waqqas (Al-Bukhari #5659) —
   "One third, and one third is much" — established as the maximum
   tolerable exposure to something impermissible when full avoidance is
   impossible.

4. Interest-Bearing Deposits: Cash in interest accounts / total equity < 30%.
   Same hadith, applied symmetrically to asset side.

5. Purification (Tazkiya): Calculate the exact % of dividends from haram
   income sources that must be donated to charity. This is wajib (obligatory).

SCHOLARLY NOTES TO APPLY:
- Tesla (TSLA): Debt ratio approaches limit in some quarters — flag for
  Deobandi/stricter schools. Mark DOUBTFUL when debt_ratio > 25%.
- Apple (AAPL): Apple Music and TV+ are secondary concerns. Flag if services
  revenue > 4% of total.
- Amazon (AMZN): AWS is clean. Advertising and marketplace content need review.
- Any company holding T-bills: Interest-bearing deposit may be breached.

PRINCIPLE: When in doubt (shubha), rule DOUBTFUL — never assume halal.
"Leave that which makes you doubt for that which does not." (Tirmidhi #2518)

You MUST respond with ONLY valid JSON, no other text, no markdown, no explanation
outside the JSON. Response format:
{
  "verdict": "HALAL" | "DOUBTFUL" | "HARAM",
  "confidence": 0-100,
  "primary_reason": "one clear sentence",
  "screens_passed": ["list of passed screens"],
  "screens_failed": ["list of failed screens"],
  "madhab_notes": "any differences between madhabs on this company",
  "purification_pct": 0.0,
  "scholarly_concerns": "any borderline issues to monitor quarterly",
  "recommendation": "PROCEED" | "REVIEW_MANUALLY" | "DO_NOT_INVEST"
}
"""

MODEL = "claude-haiku-4-5-20251001"


def evaluate(
    ticker: str,
    sector: str = "Unknown",
    industry: str = "Unknown",
    debt_ratio: float = 0.0,
    cash_ratio: float = 0.0,
    revenue_total: float = 0.0,
    revenue_impermissible: float = 0.0,
    dividend_yield: float = 0.0,
    scholarly_flags: list[str] | None = None,
) -> dict:
    """Run a Shariah compliance screen on the given equity."""
    logger.info("Evaluating Shariah compliance for %s", ticker)

    impermissible_pct = (
        (revenue_impermissible / revenue_total * 100) if revenue_total > 0 else 0.0
    )

    user_message = json.dumps({
        "ticker": ticker,
        "sector": sector,
        "industry": industry,
        "debt_ratio_pct": round(debt_ratio * 100, 2),
        "cash_ratio_pct": round(cash_ratio * 100, 2),
        "revenue_total": revenue_total,
        "revenue_impermissible": revenue_impermissible,
        "impermissible_revenue_pct": round(impermissible_pct, 2),
        "dividend_yield_pct": round(dividend_yield * 100, 2),
        "scholarly_flags": scholarly_flags or [],
    })

    parsed, meta = call_agent_json(SYSTEM_PROMPT, user_message, model=MODEL, max_tokens=600)

    # Validate verdict
    if parsed.get("verdict") not in ("HALAL", "DOUBTFUL", "HARAM"):
        parsed["verdict"] = "DOUBTFUL"

    logger.info("Sheikh verdict for %s: %s (confidence %s)",
                ticker, parsed.get("verdict"), parsed.get("confidence"))
    parsed["_meta"] = meta
    return parsed
