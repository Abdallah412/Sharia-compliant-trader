"""
Orchestrator Agent — Senior portfolio manager.
Synthesizes Sheikh, Finance, and Accountant agent outputs into a final trading decision.
"""

import anthropic
import json
import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("orchestrator")

AUTO_EXECUTE_MAX_USD = float(os.getenv("AUTO_EXECUTE_MAX_USD", "5000"))

SYSTEM_PROMPT = """You are a senior portfolio manager responsible for synthesizing the recommendations \
of three specialist agents — a Shariah scholar (Sheikh), a quantitative analyst (Finance), and a tax \
accountant — into a single, final trading decision.

You MUST follow this strict decision hierarchy:
1. If the Sheikh verdict is HARAM → REJECT the trade immediately, regardless of other signals.
2. If the Sheikh verdict is DOUBTFUL → flag for MANUAL_REVIEW, regardless of other signals.
3. If the Finance signal is SELL with confidence > 60 → SELL (after considering tax implications).
4. If the Finance signal is BUY AND the Tax verdict is PROCEED → EXECUTE the trade.
5. If the Tax verdict is WAIT_FOR_LONGTERM AND days_to_long_term < 30 → HOLD.
6. Default → HOLD.

You MUST respond with ONLY a valid JSON object (no markdown, no explanation outside JSON) with these fields:
- final_decision: "EXECUTE" | "HOLD" | "REJECT" | "MANUAL_REVIEW"
- action: "BUY" | "SELL" | "HOLD"
- ticker: string
- quantity: integer
- estimated_price: float
- confidence: integer 0-100
- primary_reason: string explaining the decisive factor
- sheikh_summary: string — one-line summary of Sheikh verdict
- finance_summary: string — one-line summary of Finance signal
- accountant_summary: string — one-line summary of Tax verdict
- tax_warning: string — any tax concern (empty string if none)
- shariah_warning: string — any Shariah concern (empty string if none)
- notification_message: string — human-readable notification for the user
- requires_user_approval: boolean
- auto_execute_eligible: boolean
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


def run_pipeline(
    ticker: str,
    action: str,
    quantity: int,
    price: float,
    sheikh_input: dict | None = None,
    finance_input: dict | None = None,
    accountant_input: dict | None = None,
) -> dict:
    """
    Run the full three-agent pipeline and return the orchestrated decision.

    If pre-computed agent inputs are not provided, callers should supply them.
    This function focuses on the orchestration step — calling all three agents
    in sequence, then synthesizing with the orchestrator LLM.
    """
    from backend.agents.sheikh_agent import evaluate as sheikh_evaluate
    from backend.agents.finance_agent import evaluate as finance_evaluate
    from backend.agents.accountant_agent import evaluate as accountant_evaluate

    # ── Step 1: Sheikh Agent ─────────────────────────────────────────────
    logger.info("Pipeline step 1/3: Sheikh agent for %s", ticker)
    if sheikh_input is not None:
        sheikh_result = sheikh_evaluate(**sheikh_input)
    else:
        logger.warning("No sheikh_input provided; using minimal defaults for %s", ticker)
        sheikh_result = sheikh_evaluate(
            ticker=ticker, sector="Unknown", industry="Unknown",
            debt_ratio=0.0, cash_ratio=0.0,
            revenue_total=0.0, revenue_impermissible=0.0,
            dividend_yield=0.0, scholarly_flags=[],
        )

    # Short-circuit: HARAM → REJECT immediately
    if sheikh_result.get("verdict") == "HARAM":
        logger.info("Sheikh verdict HARAM — pipeline halted for %s", ticker)
        return {
            "final_decision": "REJECT",
            "action": "HOLD",
            "ticker": ticker,
            "quantity": quantity,
            "estimated_price": price,
            "confidence": sheikh_result.get("confidence", 0),
            "primary_reason": f"Shariah non-compliant: {sheikh_result.get('primary_reason', '')}",
            "sheikh_summary": sheikh_result.get("primary_reason", "HARAM"),
            "finance_summary": "Not evaluated — blocked by Shariah screen.",
            "accountant_summary": "Not evaluated — blocked by Shariah screen.",
            "tax_warning": "",
            "shariah_warning": sheikh_result.get("scholarly_concerns", ""),
            "notification_message": f"REJECTED: {ticker} failed Shariah compliance screening. {sheikh_result.get('primary_reason', '')}",
            "requires_user_approval": False,
            "auto_execute_eligible": False,
        }

    # Short-circuit: DOUBTFUL → MANUAL_REVIEW
    if sheikh_result.get("verdict") == "DOUBTFUL":
        logger.info("Sheikh verdict DOUBTFUL — flagging %s for manual review", ticker)
        return {
            "final_decision": "MANUAL_REVIEW",
            "action": "HOLD",
            "ticker": ticker,
            "quantity": quantity,
            "estimated_price": price,
            "confidence": sheikh_result.get("confidence", 0),
            "primary_reason": f"Shariah compliance uncertain: {sheikh_result.get('primary_reason', '')}",
            "sheikh_summary": sheikh_result.get("primary_reason", "DOUBTFUL"),
            "finance_summary": "Not evaluated — pending Shariah review.",
            "accountant_summary": "Not evaluated — pending Shariah review.",
            "tax_warning": "",
            "shariah_warning": sheikh_result.get("scholarly_concerns", ""),
            "notification_message": f"REVIEW REQUIRED: {ticker} has uncertain Shariah compliance. {sheikh_result.get('primary_reason', '')}",
            "requires_user_approval": True,
            "auto_execute_eligible": False,
        }

    # ── Step 2: Finance Agent ────────────────────────────────────────────
    logger.info("Pipeline step 2/3: Finance agent for %s", ticker)
    if finance_input is not None:
        finance_result = finance_evaluate(**finance_input)
    else:
        logger.warning("No finance_input provided; using minimal defaults for %s", ticker)
        finance_result = finance_evaluate(
            ticker=ticker, current_price=price,
            ema20=price, ema50=price, ema_signal="NEUTRAL",
            news_sentiment_score=0.0, top_headlines=[],
            earnings_surprise_pct=0.0, forward_pe=0.0,
            analyst_consensus="none", vix_level=0.0,
            macro_summary="No macro data available.",
        )

    # ── Step 3: Accountant Agent ─────────────────────────────────────────
    logger.info("Pipeline step 3/3: Accountant agent for %s", ticker)
    if accountant_input is not None:
        accountant_result = accountant_evaluate(**accountant_input)
    else:
        logger.warning("No accountant_input provided; using minimal defaults for %s", ticker)
        from datetime import date
        accountant_result = accountant_evaluate(
            ticker=ticker, purchase_date=date.today().isoformat(),
            purchase_price=price, current_price=price,
            quantity=quantity, action_proposed=action,
            user_income_bracket="24%", user_filing_status="single",
            user_state="CA", ytd_realized_gains=0.0,
            recent_sales_history=[],
        )

    # ── Step 4: Orchestrator LLM ─────────────────────────────────────────
    logger.info("Synthesizing pipeline results for %s", ticker)

    trade_value = price * quantity
    orchestrator_input = {
        "ticker": ticker,
        "proposed_action": action,
        "quantity": quantity,
        "estimated_price": price,
        "trade_value_usd": round(trade_value, 2),
        "auto_execute_max_usd": AUTO_EXECUTE_MAX_USD,
        "sheikh_result": sheikh_result,
        "finance_result": finance_result,
        "accountant_result": accountant_result,
    }

    try:
        result = call_agent(SYSTEM_PROMPT, json.dumps(orchestrator_input))
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Orchestrator response as JSON: %s", e)
        return {
            "final_decision": "HOLD",
            "action": "HOLD",
            "ticker": ticker,
            "quantity": quantity,
            "estimated_price": price,
            "confidence": 0,
            "primary_reason": f"Orchestrator response parsing error: {e}",
            "sheikh_summary": sheikh_result.get("primary_reason", ""),
            "finance_summary": finance_result.get("primary_reason", ""),
            "accountant_summary": accountant_result.get("recommendation", ""),
            "tax_warning": "",
            "shariah_warning": "",
            "notification_message": "Pipeline error — defaulting to HOLD.",
            "requires_user_approval": True,
            "auto_execute_eligible": False,
        }

    # ── Enforce auto_execute_eligible rules ──────────────────────────────
    auto_eligible = (
        sheikh_result.get("verdict") == "HALAL"
        and sheikh_result.get("confidence", 0) > 90
        and finance_result.get("signal") in ("BUY", "SELL")
        and finance_result.get("confidence", 0) > 75
        and accountant_result.get("tax_verdict") == "PROCEED"
        and trade_value < AUTO_EXECUTE_MAX_USD
    )
    result["auto_execute_eligible"] = auto_eligible
    if auto_eligible:
        result["requires_user_approval"] = False

    logger.info(
        "Pipeline complete for %s: decision=%s action=%s auto_execute=%s",
        ticker, result.get("final_decision"), result.get("action"), auto_eligible,
    )
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python orchestrator.py <TICKER> <ACTION>")
        print("  ACTION: BUY or SELL")
        print("  Example: python orchestrator.py AAPL BUY")
        sys.exit(1)

    ticker_symbol = sys.argv[1].upper()
    action_arg = sys.argv[2].upper()

    # For standalone testing, run the pipeline with minimal defaults
    result = run_pipeline(
        ticker=ticker_symbol,
        action=action_arg,
        quantity=10,
        price=150.00,
    )

    print(json.dumps(result, indent=2))
