"""
Orchestrator Agent — Senior portfolio manager.
Synthesizes Sheikh, Finance, and Accountant outputs into a final decision.
Uses Sonnet for judgment/synthesis capability.
"""

import json
import logging

from agents.base_agent import call_agent_json

logger = logging.getLogger("orchestrator")

SYSTEM_PROMPT = """\
You are a senior portfolio manager synthesizing three specialist advisors:
a Shariah scholar, a quantitative analyst, and a tax accountant.

DECISION HIERARCHY (strict priority order):
1. Sheikh = HARAM → REJECT immediately. No override. Log and alert user.
2. Sheikh = DOUBTFUL → flag for MANUAL_REVIEW. Do not auto-execute.
3. Finance signal = SELL with confidence > 60 + Tax = PROCEED → SELL
4. Finance signal = BUY + Sheikh = HALAL + Tax = PROCEED → EXECUTE
5. Tax says WAIT_FOR_LONGTERM + days_to_long_term < 30 → HOLD, re-check in X days
6. All other cases → HOLD

AUTO-EXECUTE CRITERIA (only when ALL of these are true):
- Sheikh verdict = HALAL with confidence ≥ 90
- Finance signal confidence ≥ 75
- Tax verdict = PROCEED
- Trade size < user's AUTO_EXECUTE_MAX_USD setting
- User's auto_execute setting = True

Respond ONLY with valid JSON:
{
  "final_decision": "EXECUTE" | "HOLD" | "REJECT" | "MANUAL_REVIEW",
  "action": "BUY" | "SELL" | "HOLD",
  "ticker": "",
  "suggested_quantity": 0,
  "confidence": 0-100,
  "primary_reason": "one paragraph synthesizing all three agents",
  "sheikh_summary": "one sentence",
  "finance_summary": "one sentence",
  "accountant_summary": "one sentence",
  "tax_warning": "",
  "shariah_warning": "",
  "requires_user_approval": true,
  "auto_execute_eligible": false,
  "notification_message": "Exact Telegram/push message to send user"
}
"""

MODEL = "claude-sonnet-4-6"


def orchestrate(
    ticker: str,
    sheikh_result: dict,
    finance_result: dict,
    accountant_result: dict,
    user: dict | None = None,
) -> dict:
    """Synthesize all three agent results into a final decision."""
    user = user or {}

    user_message = f"""\
Make the final investment decision for {ticker}.

SHEIKH AGENT RESULT:
{json.dumps(sheikh_result, indent=2, default=str)}

FINANCE AGENT RESULT:
{json.dumps(finance_result, indent=2, default=str)}

ACCOUNTANT AGENT RESULT:
{json.dumps(accountant_result, indent=2, default=str)}

USER SETTINGS:
Tier: {user.get('tier', 'pro')}
Auto-execute enabled: {user.get('auto_execute', False)}
Auto-execute max USD: ${user.get('auto_execute_max_usd', 50)}
Dry run mode: {user.get('dry_run', True)}
"""

    parsed, meta = call_agent_json(SYSTEM_PROMPT, user_message, model=MODEL, max_tokens=800)

    # Validate
    if parsed.get("final_decision") not in ("EXECUTE", "HOLD", "REJECT", "MANUAL_REVIEW"):
        parsed["final_decision"] = "HOLD"
    if parsed.get("action") not in ("BUY", "SELL", "HOLD"):
        parsed["action"] = "HOLD"
    if "confidence" in parsed:
        parsed["confidence"] = max(0, min(100, int(parsed["confidence"])))

    parsed["ticker"] = ticker
    parsed["_meta"] = meta
    return parsed


def run_full_pipeline(
    ticker: str,
    sheikh_kwargs: dict,
    finance_kwargs: dict,
    accountant_kwargs: dict,
    user: dict | None = None,
) -> dict:
    """Run all four agents in sequence: Sheikh → (gate) → Finance → Accountant → Orchestrator."""
    from agents.sheikh_agent import evaluate as sheikh_evaluate
    from agents.finance_agent import evaluate as finance_evaluate
    from agents.accountant_agent import evaluate as accountant_evaluate

    # Step 1: Sheikh
    logger.info("Pipeline 1/4: Sheikh agent for %s", ticker)
    sheikh_result = sheikh_evaluate(**sheikh_kwargs)

    # Gate: HARAM → REJECT immediately
    if sheikh_result.get("verdict") == "HARAM":
        logger.info("Sheikh HARAM — pipeline halted for %s", ticker)
        return {
            "final_decision": "REJECT",
            "action": "HOLD",
            "ticker": ticker,
            "confidence": sheikh_result.get("confidence", 0),
            "primary_reason": f"Shariah non-compliant: {sheikh_result.get('primary_reason', '')}",
            "sheikh_summary": sheikh_result.get("primary_reason", "HARAM"),
            "finance_summary": "Not evaluated — blocked by Shariah screen.",
            "accountant_summary": "Not evaluated — blocked by Shariah screen.",
            "requires_user_approval": False,
            "auto_execute_eligible": False,
            "sheikh_result": sheikh_result,
        }

    # Step 2: Finance
    logger.info("Pipeline 2/4: Finance agent for %s", ticker)
    finance_result = finance_evaluate(**finance_kwargs)

    # Step 3: Accountant
    logger.info("Pipeline 3/4: Accountant agent for %s", ticker)
    accountant_result = accountant_evaluate(**accountant_kwargs)

    # Step 4: Orchestrator
    logger.info("Pipeline 4/4: Orchestrator for %s", ticker)
    result = orchestrate(ticker, sheikh_result, finance_result, accountant_result, user)
    result["sheikh_result"] = sheikh_result
    result["finance_result"] = finance_result
    result["accountant_result"] = accountant_result
    return result
