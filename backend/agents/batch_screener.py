"""
Batch API screener for non-urgent tasks (50% cost reduction).
Use for quarterly re-screen of all holdings across all users.
"""

import logging
import anthropic

from config import ANTHROPIC_API_KEY
from agents.sheikh_agent import SYSTEM_PROMPT as SHEIKH_PROMPT

logger = logging.getLogger("batch_screener")


def batch_screen_tickers(tickers: list[str]) -> str:
    """
    Submit batch screening requests at 50% the normal cost.
    Results arrive within 24 hours.
    Returns batch ID to poll for results.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    requests = [
        {
            "custom_id": ticker,
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "system": [
                    {
                        "type": "text",
                        "text": SHEIKH_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [
                    {
                        "role": "user",
                        "content": f"Screen this ticker for Shariah compliance: {ticker}",
                    }
                ],
            },
        }
        for ticker in tickers
    ]

    batch = client.messages.batches.create(requests=requests)
    logger.info("Batch submitted: id=%s tickers=%d", batch.id, len(tickers))
    return batch.id
