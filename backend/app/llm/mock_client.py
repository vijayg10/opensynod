"""Mock LLM client for UI testing and development."""

from __future__ import annotations

import asyncio
import json
import random
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall, ToolDefinition

_MOCK_PARAGRAPHS = [
    "This is an interesting point that deserves careful consideration. Looking at the evidence available, there are several factors we should weigh before reaching a conclusion.",
    "I'd like to offer a different perspective on this matter. While the previous arguments have merit, we should also consider the broader implications and potential unintended consequences.",
    "Based on my analysis, the most effective approach would involve a balanced strategy that accounts for both short-term needs and long-term sustainability.",
    "There are compelling arguments on both sides of this debate. However, I believe the weight of evidence tilts toward a more nuanced position that incorporates elements from multiple viewpoints.",
    "Let me build on what has been discussed so far. The key insight here is that we need to consider not just the immediate outcomes but also the systemic effects of any decision we make.",
    "I appreciate the thoughtful analysis shared by others. To add to the discussion, I think we should also examine the historical precedents and what lessons they offer for our current situation.",
    "From a practical standpoint, implementation challenges are just as important as theoretical soundness. We need a solution that is not only correct in principle but also feasible to execute.",
    "This is a complex topic with many dimensions. I want to focus on one aspect that I think has been underappreciated so far: the role of feedback loops in shaping outcomes over time.",
]

_PHASES = ["opening", "exploration", "debate", "convergence", "vote"]


def _extract_seat_ids(messages: list[LLMMessage]) -> list[str]:
    """Try to extract available speaker seat_ids from the user message content."""
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            match = re.search(r"Available speakers:\s*(.+)", content)
            if match:
                return [s.strip() for s in match.group(1).split(",") if s.strip()]
    return []


def _extract_last_speaker(messages: list[LLMMessage]) -> str | None:
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            match = re.search(r"Last speaker:\s*(\S+)", content)
            if match and match.group(1) != "none":
                return match.group(1)
    return None


def _extract_current_phase(messages: list[LLMMessage]) -> str | None:
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            match = re.search(r"Current phase:\s*(\S+)", content)
            if match:
                return match.group(1)
    return None


def _extract_turn_count(messages: list[LLMMessage]) -> int:
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            match = re.search(r"Turn count:\s*(\d+)", content)
            if match:
                return int(match.group(1))
    return 0


def _mock_moderator_decision(messages: list[LLMMessage]) -> dict[str, Any]:
    """Generate a realistic moderator decision with dynamic speaker selection and phase transitions."""
    seat_ids = _extract_seat_ids(messages)
    last_speaker = _extract_last_speaker(messages)
    current_phase = _extract_current_phase(messages)
    turn_count = _extract_turn_count(messages)

    # Pick next speaker: weighted random, avoiding the last speaker
    if seat_ids:
        candidates = [s for s in seat_ids if s != last_speaker] or seat_ids
        next_speaker = random.choice(candidates)
    else:
        next_speaker = "unknown"

    # Determine phase transitions based on turn count
    phase_transition = None
    if current_phase and current_phase in _PHASES:
        phase_idx = _PHASES.index(current_phase)
        # Transition thresholds: opening after ~N seats, exploration after ~8, debate after ~14, convergence after ~18
        if current_phase == "opening" and turn_count >= max(len(seat_ids), 3):
            phase_transition = "exploration"
        elif current_phase == "exploration" and turn_count >= 8:
            phase_transition = "debate"
        elif current_phase == "debate" and turn_count >= 14:
            phase_transition = "convergence"
        elif current_phase == "convergence" and turn_count >= 18:
            phase_transition = "vote"

    return {
        "next_speaker": next_speaker,
        "phase_transition": phase_transition,
        "inject_challenge": random.random() < 0.2,
        "challenge_target": None,
        "summary": None,
        "reasoning": f"Mock decision: selected {next_speaker} for turn {turn_count + 1}",
    }


def _mock_tool_response(tool: ToolDefinition, messages: list[LLMMessage]) -> dict[str, Any]:
    """Generate a mock response for a known tool."""
    name = tool["name"]

    if name == "make_moderator_decision":
        return _mock_moderator_decision(messages)

    if name == "cast_vote":
        return {
            "vote": random.choice(["yes", "yes", "yes", "no", "abstain"]),
            "rationale": "Based on the discussion, this is my considered position.",
        }

    if name == "make_recommendation":
        return {
            "outcome_type": "recommendation",
            "statement": "Based on the comprehensive discussion, the group recommends a balanced approach that addresses the key concerns raised by all participants.",
            "supporting_arguments": [
                "Multiple participants identified this as the most practical path forward.",
                "The approach balances competing priorities effectively.",
            ],
            "substantive_dissents": [
                "Some participants raised concerns about implementation complexity.",
            ],
        }

    # Generic fallback: fill required fields from schema
    schema = tool.get("input_schema", {})
    result: dict[str, Any] = {}
    for prop, prop_schema in schema.get("properties", {}).items():
        prop_type = prop_schema.get("type", "string")
        if isinstance(prop_type, list):
            prop_type = prop_type[0]
        if prop_type == "string":
            result[prop] = f"mock_{prop}"
        elif prop_type == "boolean":
            result[prop] = False
        elif prop_type == "array":
            result[prop] = []
        elif prop_type == "number" or prop_type == "integer":
            result[prop] = 0
    return result


class MockLLMClient(BaseLLMClient):
    """Returns random placeholder text instead of calling a real LLM provider."""

    async def chat(
        self,
        model: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        await asyncio.sleep(random.uniform(0.3, 1.0))

        # If tools are provided, return a mock tool call
        if tools:
            tool = tools[0]
            tool_input = _mock_tool_response(tool, messages)
            return LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id=f"mock_{uuid.uuid4().hex[:8]}",
                        name=tool["name"],
                        input=tool_input,
                    )
                ],
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                model=f"mock({model})",
                latency_ms=0,
            )

        paragraphs = random.sample(_MOCK_PARAGRAPHS, k=random.randint(1, 3))
        content = "\n\n".join(paragraphs)
        output_tokens = len(content.split())

        return LLMResponse(
            content=content,
            tool_calls=[],
            input_tokens=0,
            output_tokens=output_tokens,
            cost_usd=0.0,
            model=f"mock({model})",
            latency_ms=0,
        )

    async def chat_stream(
        self,
        model: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[str | ToolCall]:
        return self._stream_generator()

    async def _stream_generator(self) -> AsyncIterator[str | ToolCall]:
        paragraphs = random.sample(_MOCK_PARAGRAPHS, k=random.randint(1, 3))
        content = "\n\n".join(paragraphs)

        # Stream word-by-word with small delays to simulate real streaming
        words = content.split()
        for i, word in enumerate(words):
            token = word if i == 0 else f" {word}"
            yield token
            await asyncio.sleep(random.uniform(0.02, 0.06))
