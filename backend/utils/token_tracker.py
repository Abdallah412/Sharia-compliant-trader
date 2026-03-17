"""
Log every Anthropic API call for cost attribution and billing protection.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Current pricing per 1M tokens (update quarterly)
PRICING = {
    "claude-haiku-4-5-20251001": {
        "input": 0.80 / 1_000_000,
        "output": 4.00 / 1_000_000,
        "cache_write": 1.00 / 1_000_000,
        "cache_read": 0.08 / 1_000_000,
    },
    "claude-sonnet-4-6": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
        "cache_write": 3.75 / 1_000_000,
        "cache_read": 0.30 / 1_000_000,
    },
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int,
                  cache_creation_tokens: int = 0, cache_read_tokens: int = 0) -> float:
    """Calculate estimated USD cost for an API call."""
    rates = PRICING.get(model, PRICING["claude-haiku-4-5-20251001"])
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_creation_tokens * rates["cache_write"]
        + cache_read_tokens * rates["cache_read"]
    )


async def log_token_usage(
    db: AsyncSession,
    user_id: str,
    feature: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
):
    """Write a token usage record to the database."""
    from models.token_usage import TokenUsage

    cost = estimate_cost(model, input_tokens, output_tokens,
                         cache_creation_tokens, cache_read_tokens)

    usage = TokenUsage(
        user_id=user_id,
        feature=feature,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        estimated_cost_usd=cost,
        created_at=datetime.now(timezone.utc),
    )
    db.add(usage)
    await db.commit()
    logger.debug("Token usage logged: user=%s feature=%s cost=$%.4f", user_id, feature, cost)
