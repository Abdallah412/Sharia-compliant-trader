"""
Safe JSON parser for Claude agent responses.
Claude occasionally produces JSON with markdown fences or surrounding text.
"""

import json
import re


def safe_parse_json(text: str) -> dict:
    """Robustly parse JSON from Claude's response."""
    text = re.sub(r"```json\s*|\s*```", "", text.strip())

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    return {
        "verdict": "DOUBTFUL",
        "final_decision": "MANUAL_REVIEW",
        "primary_reason": "Agent response parsing failed — flagged for manual review",
        "parse_error": True,
    }
