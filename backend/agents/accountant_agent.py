"""
Accountant Agent — Licensed CPA and tax attorney.
Evaluates US tax implications for retail investment transactions (2026 framework).
"""

import anthropic
import json
import logging
import sys
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("accountant_agent")

SYSTEM_PROMPT = """You are a licensed CPA and tax attorney specializing in US retail investment taxation. \
You operate under the 2026 US federal tax framework. You understand long-term vs short-term capital gains, \
wash sale rules (IRS Section 1091), tax-loss harvesting strategies, and state-level capital gains taxes.

2026 Federal capital gains brackets (single filer):
- 0% rate: taxable income up to ~$48,350
- 15% rate: taxable income $48,351 – $533,400
- 20% rate: taxable income above $533,400
- 3.8% Net Investment Income Tax (NIIT) may apply above $200,000 AGI (single)

Short-term capital gains are taxed as ordinary income.

Wash sale rule: If a substantially identical security is purchased within 30 days before or after a sale \
at a loss, the loss is disallowed for tax purposes.

You MUST respond with ONLY a valid JSON object (no markdown, no explanation outside JSON) with these fields:
- tax_verdict: "PROCEED" | "WAIT_FOR_LONGTERM" | "HARVEST_LOSS" | "CAUTION"
- holding_period_days: integer — number of days the position has been held
- is_long_term: boolean — true if held over 365 days
- days_to_long_term: integer — days remaining to qualify for long-term rate (0 if already long-term)
- estimated_tax_if_sell_now: float — estimated federal + state tax on gain/loss if sold today
- estimated_tax_if_wait: float — estimated tax if held until long-term qualification
- tax_savings_from_waiting: float — difference between sell-now and wait estimates
- wash_sale_risk: boolean — true if recent sales history suggests a wash sale concern
- wash_sale_warning: string — explanation of any wash sale risk (empty string if none)
- net_after_tax_gain: float — estimated net gain after taxes if sold now
- ytd_realized_gains: float — year-to-date realised capital gains passed in
- estimated_annual_tax_liability: float — projected annual tax on investment income
- large_tax_alert: boolean — true if estimated tax exceeds $10,000
- recommendation: string — concise actionable recommendation
- zakat_note: string — note about zakat obligation if position held 354+ days (one lunar year), empty string otherwise
"""

_client = None


def _get_client():
    """Lazily initialize the Anthropic client to avoid import-time crashes."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def call_agent(system_prompt: str, user_message: str) -> dict:
    """Call the Anthropic API and parse the JSON response safely."""
    import re
    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("AI response is not a JSON object")
    # Validate tax_verdict is in allowed set
    VALID_VERDICTS = {"PROCEED", "WAIT_FOR_LONGTERM", "HARVEST_LOSS", "CAUTION"}
    if "tax_verdict" in result and result["tax_verdict"] not in VALID_VERDICTS:
        result["tax_verdict"] = "CAUTION"
    return result


def evaluate(
    ticker: str,
    purchase_date: str,
    purchase_price: float,
    current_price: float,
    quantity: int,
    action_proposed: str,
    user_income_bracket: str,
    user_filing_status: str,
    user_state: str,
    ytd_realized_gains: float,
    recent_sales_history: list[dict],
) -> dict:
    """Evaluate tax implications of a proposed trade."""
    logger.info("Evaluating tax implications for %s (%s %d shares)", ticker, action_proposed, quantity)

    purchase_dt = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    holding_days = (date.today() - purchase_dt).days
    unrealised_gain = (current_price - purchase_price) * quantity

    user_message = json.dumps(
        {
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
            "recent_sales_history": recent_sales_history,
            "zakat_eligible": holding_days >= 354,
        }
    )

    try:
        result = call_agent(SYSTEM_PROMPT, user_message)
        logger.info("Tax verdict for %s: %s", ticker, result.get("tax_verdict"))
        return result
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Accountant agent response as JSON: %s", e)
        return {
            "tax_verdict": "CAUTION",
            "holding_period_days": holding_days,
            "is_long_term": holding_days > 365,
            "days_to_long_term": max(0, 366 - holding_days),
            "estimated_tax_if_sell_now": 0.0,
            "estimated_tax_if_wait": 0.0,
            "tax_savings_from_waiting": 0.0,
            "wash_sale_risk": False,
            "wash_sale_warning": "",
            "net_after_tax_gain": 0.0,
            "ytd_realized_gains": ytd_realized_gains,
            "estimated_annual_tax_liability": 0.0,
            "large_tax_alert": False,
            "recommendation": f"Agent response parsing error: {e}",
            "zakat_note": "",
        }
    except Exception as e:
        logger.error("Accountant agent error for %s: %s", ticker, e)
        raise


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python accountant_agent.py <TICKER> <ACTION> <QUANTITY>")
        print("  ACTION: BUY or SELL")
        print("  Example: python accountant_agent.py AAPL SELL 50")
        sys.exit(1)

    ticker_symbol = sys.argv[1].upper()
    action = sys.argv[2].upper()
    qty = int(sys.argv[3])

    # Defaults for standalone testing
    result = evaluate(
        ticker=ticker_symbol,
        purchase_date="2025-06-01",
        purchase_price=150.00,
        current_price=175.00,
        quantity=qty,
        action_proposed=action,
        user_income_bracket="24%",
        user_filing_status="single",
        user_state="CA",
        ytd_realized_gains=5000.00,
        recent_sales_history=[],
    )

    print(json.dumps(result, indent=2))
