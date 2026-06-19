"""Tests for cost calculation."""

import pytest
from app.llm.pricing import calculate_cost, PRICING


def test_known_model_cost():
    # claude-sonnet-4-6: input $3/M, output $15/M
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == pytest.approx(18.0, rel=1e-6)


def test_zero_tokens():
    cost = calculate_cost("gpt-4o", input_tokens=0, output_tokens=0)
    assert cost == 0.0


def test_input_only():
    # gpt-4o: $2.50/M input
    cost = calculate_cost("gpt-4o", input_tokens=2_000_000, output_tokens=0)
    assert cost == pytest.approx(5.0, rel=1e-6)


def test_output_only():
    # gpt-4o: $10/M output
    cost = calculate_cost("gpt-4o", input_tokens=0, output_tokens=500_000)
    assert cost == pytest.approx(5.0, rel=1e-6)


def test_unknown_model_uses_default():
    # Should not raise, uses default pricing
    cost = calculate_cost("some-unknown-model", input_tokens=1_000, output_tokens=1_000)
    assert cost >= 0.0


def test_all_known_models_have_positive_rates():
    for model, rates in PRICING.items():
        assert rates["input"] > 0, f"{model} input rate must be positive"
        assert rates["output"] > 0, f"{model} output rate must be positive"


def test_cost_is_rounded():
    cost = calculate_cost("claude-haiku-4-5", input_tokens=123, output_tokens=456)
    # Should be a float with at most 8 decimal places
    assert cost == round(cost, 8)
