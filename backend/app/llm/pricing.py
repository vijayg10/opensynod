"""Per-model pricing tables (USD per 1M tokens).

Updated as of 2026-05-16. Override via config rather than modifying this file.
"""

from __future__ import annotations

# Structure: model_id -> {"input": price_per_million, "output": price_per_million}
PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o3": {"input": 10.0, "output": 40.0},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Google
    "gemini-2.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
}

_DEFAULT_PRICING = {"input": 0.50, "output": 1.50}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token counts."""
    rates = PRICING.get(model, _DEFAULT_PRICING)
    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    return round(input_cost + output_cost, 8)
