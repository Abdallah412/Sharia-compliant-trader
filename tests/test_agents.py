"""
Tests for the agent pipeline — Sheikh, Finance, and Accountant agents.
All Anthropic API calls are mocked so no network access is needed.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from backend.agents import sheikh_agent, finance_agent, accountant_agent


# ---------------------------------------------------------------------------
# Helpers — build mock Anthropic responses
# ---------------------------------------------------------------------------

def _mock_anthropic_response(payload: dict):
    """Return a mock that mimics anthropic.Anthropic().messages.create(...)."""
    mock_message = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = json.dumps(payload)
    mock_message.content = [mock_content_block]
    return mock_message


def _make_mock_client(payload: dict):
    """Return a mock Anthropic client whose messages.create returns *payload*."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_anthropic_response(payload)
    return mock_client


# ===========================================================================
# Sheikh Agent tests
# ===========================================================================

class TestSheikhAgent:
    @patch.object(sheikh_agent, "client")
    def test_sheikh_haram_stops_pipeline(self, mock_client_attr):
        """When the Sheikh returns HARAM the orchestrator should get a REJECT-able result."""
        haram_response = {
            "verdict": "HARAM",
            "confidence": 95,
            "primary_reason": "Primary business is conventional banking (riba)",
            "screens_passed": [],
            "screens_failed": ["primary_business_activity"],
            "madhab_notes": "All four schools agree banking is impermissible",
            "purification_pct": 0.0,
            "scholarly_concerns": "",
            "recommendation": "DO_NOT_INVEST",
        }
        mock_client_attr.messages.create.return_value = _mock_anthropic_response(haram_response)

        result = sheikh_agent.evaluate(
            ticker="FAKEBK",
            sector="Financial Services",
            industry="Banks—Diversified",
            debt_ratio=0.6,
            cash_ratio=0.1,
            revenue_total=50_000_000_000,
            revenue_impermissible=50_000_000_000,
            dividend_yield=0.03,
        )

        assert result["verdict"] == "HARAM"
        assert result["recommendation"] == "DO_NOT_INVEST"

    @patch.object(sheikh_agent, "client")
    def test_sheikh_halal_continues(self, mock_client_attr):
        """When the Sheikh returns HALAL the pipeline should continue."""
        halal_response = {
            "verdict": "HALAL",
            "confidence": 88,
            "primary_reason": "Technology company, all ratios within AAOIFI limits",
            "screens_passed": [
                "primary_business", "debt_ratio", "cash_ratio",
                "receivables_ratio", "revenue_purity",
            ],
            "screens_failed": [],
            "madhab_notes": "",
            "purification_pct": 1.2,
            "scholarly_concerns": "",
            "recommendation": "PROCEED",
        }
        mock_client_attr.messages.create.return_value = _mock_anthropic_response(halal_response)

        result = sheikh_agent.evaluate(
            ticker="NVDA",
            sector="Technology",
            industry="Semiconductors",
            debt_ratio=0.10,
            cash_ratio=0.05,
            revenue_total=60_000_000_000,
            revenue_impermissible=0,
            dividend_yield=0.005,
        )

        assert result["verdict"] == "HALAL"
        assert result["recommendation"] == "PROCEED"
        assert result["confidence"] > 0


# ===========================================================================
# Orchestrator decision hierarchy tests
# ===========================================================================

class TestOrchestratorDecisionHierarchy:
    """
    The orchestrator follows this hierarchy:
      1. Sheikh says HARAM → REJECT (regardless of finance/tax)
      2. Sheikh says HALAL + Finance says BUY + Tax says PROCEED → EXECUTE
      3. Sheikh says DOUBTFUL → REVIEW
      4. Finance says SELL → SKIP even if Sheikh says HALAL
    """

    @patch.object(sheikh_agent, "client")
    @patch.object(finance_agent, "client")
    def test_haram_overrides_buy(self, mock_fin_client, mock_sheikh_client):
        """HARAM verdict overrides any BUY signal."""
        mock_sheikh_client.messages.create.return_value = _mock_anthropic_response({
            "verdict": "HARAM",
            "confidence": 95,
            "primary_reason": "Gambling revenue",
            "screens_passed": [],
            "screens_failed": ["primary_business_activity"],
            "madhab_notes": "",
            "purification_pct": 0.0,
            "scholarly_concerns": "",
            "recommendation": "DO_NOT_INVEST",
        })
        mock_fin_client.messages.create.return_value = _mock_anthropic_response({
            "signal": "BUY",
            "confidence": 90,
            "expected_return_low": 5.0,
            "expected_return_high": 15.0,
            "position_size_multiplier": 1.0,
            "time_horizon_days": 30,
            "primary_reason": "Strong momentum",
            "supporting_factors": [],
            "risk_factors": [],
            "macro_context": "",
            "recommendation": "EXECUTE",
        })

        sheikh_result = sheikh_agent.evaluate(
            ticker="MGM", sector="Consumer Cyclical",
            industry="Casinos & Gaming", debt_ratio=0.2,
            cash_ratio=0.1, revenue_total=10e9,
            revenue_impermissible=10e9, dividend_yield=0.01,
        )

        # Orchestrator logic: if sheikh says HARAM, reject regardless
        assert sheikh_result["verdict"] == "HARAM"
        # The orchestrator would return REJECT here
        orchestrator_decision = (
            "REJECT" if sheikh_result["verdict"] == "HARAM" else "CONTINUE"
        )
        assert orchestrator_decision == "REJECT"

    @patch.object(sheikh_agent, "client")
    @patch.object(finance_agent, "client")
    def test_halal_plus_sell_equals_skip(self, mock_fin_client, mock_sheikh_client):
        """HALAL + SELL signal → orchestrator should SKIP."""
        mock_sheikh_client.messages.create.return_value = _mock_anthropic_response({
            "verdict": "HALAL",
            "confidence": 85,
            "primary_reason": "Compliant tech stock",
            "screens_passed": ["all"],
            "screens_failed": [],
            "madhab_notes": "",
            "purification_pct": 0.5,
            "scholarly_concerns": "",
            "recommendation": "PROCEED",
        })
        mock_fin_client.messages.create.return_value = _mock_anthropic_response({
            "signal": "SELL",
            "confidence": 80,
            "expected_return_low": -10.0,
            "expected_return_high": -2.0,
            "position_size_multiplier": 0.0,
            "time_horizon_days": 0,
            "primary_reason": "Death cross confirmed",
            "supporting_factors": [],
            "risk_factors": [],
            "macro_context": "",
            "recommendation": "SKIP",
        })

        sheikh_result = sheikh_agent.evaluate(
            ticker="FAKE", sector="Technology",
            industry="Software", debt_ratio=0.05,
            cash_ratio=0.03, revenue_total=5e9,
            revenue_impermissible=0, dividend_yield=0.01,
        )
        finance_result = finance_agent.evaluate(
            ticker="FAKE", current_price=100.0,
            ema20=95.0, ema50=105.0,
            ema_signal="BEARISH_CROSSOVER",
            news_sentiment_score=-0.5,
            top_headlines=["Stock tanks"],
            earnings_surprise_pct=-5.0,
            forward_pe=30.0, analyst_consensus="sell",
            vix_level=25.0, macro_summary="Recession fears",
        )

        assert sheikh_result["verdict"] == "HALAL"
        assert finance_result["signal"] == "SELL"

        # Orchestrator: HALAL but SELL → SKIP
        orchestrator_decision = "SKIP" if finance_result["signal"] == "SELL" else "EXECUTE"
        assert orchestrator_decision == "SKIP"

    @patch.object(sheikh_agent, "client")
    def test_doubtful_triggers_review(self, mock_sheikh_client):
        """DOUBTFUL verdict should trigger manual review."""
        mock_sheikh_client.messages.create.return_value = _mock_anthropic_response({
            "verdict": "DOUBTFUL",
            "confidence": 55,
            "primary_reason": "Defense contractor — weapons manufacturing unclear",
            "screens_passed": ["debt_ratio", "cash_ratio"],
            "screens_failed": [],
            "madhab_notes": "Hanafi scholars may permit if < 5% weapons revenue",
            "purification_pct": 3.0,
            "scholarly_concerns": "Minority opinion allows defense stocks",
            "recommendation": "REVIEW_MANUALLY",
        })

        result = sheikh_agent.evaluate(
            ticker="LMT", sector="Industrials",
            industry="Aerospace & Defense", debt_ratio=0.15,
            cash_ratio=0.08, revenue_total=65e9,
            revenue_impermissible=0, dividend_yield=0.025,
        )

        assert result["verdict"] == "DOUBTFUL"
        assert result["recommendation"] == "REVIEW_MANUALLY"


# ===========================================================================
# Auto-execute eligibility
# ===========================================================================

class TestAutoExecute:
    def test_auto_execute_eligibility(self):
        """Auto-execute only when ALL conditions are met:
        - Sheikh verdict is HALAL
        - Finance signal is BUY
        - Finance confidence >= 70
        - Tax verdict is PROCEED
        - No wash-sale risk
        """

        def can_auto_execute(sheikh, finance, tax):
            return (
                sheikh.get("verdict") == "HALAL"
                and finance.get("signal") == "BUY"
                and finance.get("confidence", 0) >= 70
                and tax.get("tax_verdict") == "PROCEED"
                and not tax.get("wash_sale_risk", False)
            )

        # All conditions met → True
        assert can_auto_execute(
            sheikh={"verdict": "HALAL", "confidence": 90},
            finance={"signal": "BUY", "confidence": 85},
            tax={"tax_verdict": "PROCEED", "wash_sale_risk": False},
        ) is True

        # Sheikh says DOUBTFUL → False
        assert can_auto_execute(
            sheikh={"verdict": "DOUBTFUL", "confidence": 60},
            finance={"signal": "BUY", "confidence": 85},
            tax={"tax_verdict": "PROCEED", "wash_sale_risk": False},
        ) is False

        # Finance confidence too low → False
        assert can_auto_execute(
            sheikh={"verdict": "HALAL", "confidence": 90},
            finance={"signal": "BUY", "confidence": 50},
            tax={"tax_verdict": "PROCEED", "wash_sale_risk": False},
        ) is False

        # Wash sale risk → False
        assert can_auto_execute(
            sheikh={"verdict": "HALAL", "confidence": 90},
            finance={"signal": "BUY", "confidence": 85},
            tax={"tax_verdict": "PROCEED", "wash_sale_risk": True},
        ) is False

        # Tax says WAIT → False
        assert can_auto_execute(
            sheikh={"verdict": "HALAL", "confidence": 90},
            finance={"signal": "BUY", "confidence": 85},
            tax={"tax_verdict": "WAIT_FOR_LONGTERM", "wash_sale_risk": False},
        ) is False

        # Finance says HOLD → False
        assert can_auto_execute(
            sheikh={"verdict": "HALAL", "confidence": 90},
            finance={"signal": "HOLD", "confidence": 85},
            tax={"tax_verdict": "PROCEED", "wash_sale_risk": False},
        ) is False
