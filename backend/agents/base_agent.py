"""
Base agent call function with prompt caching.
All agent calls go through this single function.
System prompts use cache_control for 90% input cost savings.
"""

import logging
import anthropic

from config import ANTHROPIC_API_KEY
from utils.json_parser import safe_parse_json

logger = logging.getLogger(__name__)

client = None


def _get_client() -> anthropic.Anthropic:
    global client
    if client is None:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return client


def call_agent(
    system_prompt: str,
    user_message: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 800,
) -> dict:
    """
    Single reusable function for all agent calls.
    System prompt is always cached — 10% of input cost after first call.
    """
    response = _get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    usage = response.usage
    result = {
        "content": response.content[0].text,
        "model": model,
        "tokens_in": usage.input_tokens,
        "tokens_out": usage.output_tokens,
        "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
        "cache_hit": getattr(usage, "cache_read_input_tokens", 0) > 0,
    }

    logger.info(
        "Agent call: model=%s in=%d out=%d cache_hit=%s",
        model, result["tokens_in"], result["tokens_out"], result["cache_hit"],
    )
    return result


def call_agent_json(
    system_prompt: str,
    user_message: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 800,
) -> tuple[dict, dict]:
    """Call agent and parse JSON response. Returns (parsed_json, raw_metadata)."""
    raw = call_agent(system_prompt, user_message, model=model, max_tokens=max_tokens)
    parsed = safe_parse_json(raw["content"])
    return parsed, raw
