"""Tests for the Moderator agent (Phase 5)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.orchestrator.moderator import ModeratorAgent, _MAKE_DECISION_TOOL
from app.orchestrator.schemas import ModeratorDecision


def _make_moderator() -> ModeratorAgent:
    router = MagicMock()
    return ModeratorAgent(
        router=router,
        model="claude-opus-4-7",
        system_prompt="You are a moderator.",
    )


class TestModeratorDecisionParsing:
    def test_parse_valid_decision(self) -> None:
        moderator = _make_moderator()
        seat_ids = ["cfo", "analyst", "lawyer"]
        decision = moderator._parse_decision(
            {
                "next_speaker": "analyst",
                "inject_challenge": True,
                "challenge_target": "cfo",
                "reasoning": "The CFO's position needs challenge.",
            },
            seat_ids,
            last_speaker="cfo",
        )
        assert decision.next_speaker == "analyst"
        assert decision.inject_challenge is True
        assert decision.challenge_target == "cfo"

    def test_fallback_when_speaker_not_in_seats(self) -> None:
        moderator = _make_moderator()
        seat_ids = ["cfo", "analyst", "lawyer"]
        decision = moderator._parse_decision(
            {
                "next_speaker": "unknown_seat",
                "inject_challenge": False,
                "reasoning": "...",
            },
            seat_ids,
            last_speaker="cfo",
        )
        assert decision.next_speaker in seat_ids

    def test_round_robin_fallback(self) -> None:
        seat_ids = ["a", "b", "c"]
        assert ModeratorAgent._round_robin_next(seat_ids, "a") == "b"
        assert ModeratorAgent._round_robin_next(seat_ids, "b") == "c"
        assert ModeratorAgent._round_robin_next(seat_ids, "c") == "a"
        assert ModeratorAgent._round_robin_next(seat_ids, None) == "a"

    def test_round_robin_wraps(self) -> None:
        seat_ids = ["x", "y"]
        assert ModeratorAgent._round_robin_next(seat_ids, "y") == "x"


class TestModeratorDecisionTool:
    def test_decision_tool_has_required_fields(self) -> None:
        schema = _MAKE_DECISION_TOOL["input_schema"]
        assert "next_speaker" in schema["properties"]
        assert "inject_challenge" in schema["properties"]
        assert "reasoning" in schema["properties"]
        assert set(schema["required"]) >= {"next_speaker", "inject_challenge", "reasoning"}


class TestPhaseGuidance:
    def test_opening_phase_guidance(self) -> None:
        moderator = _make_moderator()
        guidance = moderator._build_phase_guidance(
            current_phase="opening",
            turn_count=0,
            challenges_this_phase=0,
            convergence_speed_threshold=3,
            min_turns_before_convergence=8,
            has_devil_advocate=True,
            devil_advocate_seat="bear_analyst",
        )
        assert "OPENING" in guidance

    def test_debate_phase_forces_challenge_when_threshold_not_met(self) -> None:
        moderator = _make_moderator()
        guidance = moderator._build_phase_guidance(
            current_phase="debate",
            turn_count=5,
            challenges_this_phase=1,
            convergence_speed_threshold=3,
            min_turns_before_convergence=8,
            has_devil_advocate=True,
            devil_advocate_seat="bear_analyst",
        )
        assert "challenge" in guidance.lower()
        assert "bear_analyst" in guidance

    def test_debate_phase_allows_convergence_after_threshold(self) -> None:
        moderator = _make_moderator()
        guidance = moderator._build_phase_guidance(
            current_phase="debate",
            turn_count=10,
            challenges_this_phase=4,
            convergence_speed_threshold=3,
            min_turns_before_convergence=8,
            has_devil_advocate=True,
            devil_advocate_seat="bear_analyst",
        )
        assert "convergence" in guidance.lower()
