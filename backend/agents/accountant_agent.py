"""
Accountant Agent — Licensed CPA specializing in US investment taxation.
Uses Haiku for cost efficiency (structured math, no deep reasoning needed).
"""

import json
import logging
from datetime import date, datetime

from agents.base_agent import call_agent_json

logger = logging.getLogger("accountant_agent")

SYSTEM_PROMPT = """\
You are a licensed CPA specializing in US investment taxation.
Your goal: maximize after-tax returns while staying fully IRS compliant.

2026 TAX FRAMEWORK:
Short-term gains (held ≤ 365 days): taxed as ordinary income
  Brackets: 10%, 12%, 22%, 24%, 32%, 35%, 37%

Long-term gains (held > 365 days): preferential rates
  0%:  income ≤ $49,450 (single) / $98,900 (married joint)
  15%: income ≤ $544,400 (single) / $613,700 (married joint)
  20%: above those thresholds
  +3.8% NIIT surcharge if income > $200k (single) / $250k (married joint)

WASH SALE RULE: Cannot claim a loss if you buy the same (or substantially
identical) security within 30 days before OR after the sale. Disallowed
loss adds to cost basis of new purchase.

TAX-LOSS HARVESTING: Selling a losing position to offset gains elsewhere.
Net short-term losses offset short-term gains first, then long-term.
Up to $3,000 net loss can offset ordinary income annually.

ZAKAT NOTE: If held for one lunar year (354 days) and portfolio > nisab
(~$6,800 at current gold prices), 2.5% Zakat applies annually.

Respond ONLY with valid JSON:
{
  "tax_verdict": "PROCEED" | "WAIT_FOR_LONGTERM" | "HARVEST_LOSS" | "CAUTION",
  "holding_period_days": 0,
  "is_long_term": false,
  "days_to_long_term": 0,
  "estimated_tax_if_sell_now_usd": 0.0,
  "estimated_tax_if_wait_usd": 0.0,
  "tax_savings_from_waiting_usd": 0.0,
  "wash_sale_risk": false,
  "wash_sale_warning": "",
  "net_after_tax_gain_usd": 0.0,
  "ytd_tax_liability_usd": 0.0,
  "large_tax_alert": false,
  "zakat_due": false,
  "recommendation": "specific one-sentence action"
}
"""

MODEL = "claude-haiku-4-5-20251001"


def evaluate(
    ticker: str,
    purchase_date: str,
    purchase_price: float,
    current_price: float,
    quantity: int,
    action_proposed: str = "SELL",
    user_income_bracket: str = "22%",
    user_filing_status: str = "single",
    user_state: str = "CA",
    ytd_realized_gains: float = 0.0,
    recent_sales_history: list[dict] | None = None,
) -> dict:
    """Evaluate tax implications of a proposed trade."""
    logger.info("Evaluating tax implications for %s (%s %d shares)", ticker, action_proposed, quantity)

    purchase_dt = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    holding_days = (date.today() - purchase_dt).days
    unrealised_gain = (current_price - purchase_price) * quantity

    user_message = json.dumps({
        "ticker": ticker,
        "purchase_date": purchase_date,
        "purchase_price": purchase_price,
        "current_price": current_price,
        "quantity": quantity,
        "action_proposed": action_proposed,
        "holding_period_days": holding_days,
        "unrealised_gain_usd": round(unrealised_gain, 2),
        "user_income_bracket": user_income_bracket,
        "user_filing_status": user_filing_status,
        "user_state": user_state,
        "ytd_realized_gains": ytd_realized_gains,
        "recent_sales_history": recent_sales_history or [],
        "zakat_eligible": holding_days >= 354,
    })

    parsed, meta = call_agent_json(SYSTEM_PROMPT, user_message, model=MODEL, max_tokens=500)

    # Validate verdict
    valid = {"PROCEED", "WAIT_FOR_LONGTERM", "HARVEST_LOSS", "CAUTION"}
    if parsed.get("tax_verdict") not in valid:
        parsed["tax_verdict"] = "CAUTION"

    logger.info("Tax verdict for %s: %s", ticker, parsed.get("tax_verdict"))
    parsed["_meta"] = meta
    return parsed
