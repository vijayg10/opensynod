"""Tests for discussion state machine (Phase 5)."""

from __future__ import annotations

import pytest

from app.orchestrator.state_machine import InvalidTransitionError, StateMachine


class TestStatusTransitions:
    def test_draft_to_queued(self) -> None:
        assert StateMachine.can_transition_status("draft", "queued")

    def test_queued_to_running(self) -> None:
        assert StateMachine.can_transition_status("queued", "running")

    def test_running_to_paused(self) -> None:
        assert StateMachine.can_transition_status("running", "paused")

    def test_running_to_voting(self) -> None:
        assert StateMachine.can_transition_status("running", "voting")

    def test_paused_to_running(self) -> None:
        assert StateMachine.can_transition_status("paused", "running")

    def test_voting_to_concluded(self) -> None:
        assert StateMachine.can_transition_status("voting", "concluded")

    def test_concluded_is_terminal(self) -> None:
        assert not StateMachine.can_transition_status("concluded", "running")
        assert not StateMachine.can_transition_status("concluded", "draft")

    def test_failed_is_terminal(self) -> None:
        assert not StateMachine.can_transition_status("failed", "running")

    def test_invalid_transitions_rejected(self) -> None:
        assert not StateMachine.can_transition_status("draft", "running")
        assert not StateMachine.can_transition_status("draft", "voting")
        assert not StateMachine.can_transition_status("concluded", "voting")


class TestPhaseTransitions:
    def test_none_to_opening(self) -> None:
        assert StateMachine.can_transition_phase(None, "opening")

    def test_opening_to_exploration(self) -> None:
        assert StateMachine.can_transition_phase("opening", "exploration")

    def test_exploration_to_debate(self) -> None:
        assert StateMachine.can_transition_phase("exploration", "debate")

    def test_debate_to_convergence(self) -> None:
        assert StateMachine.can_transition_phase("debate", "convergence")

    def test_convergence_to_vote(self) -> None:
        assert StateMachine.can_transition_phase("convergence", "vote")

    def test_cannot_skip_phases(self) -> None:
        assert not StateMachine.can_transition_phase("opening", "debate")
        assert not StateMachine.can_transition_phase("opening", "vote")

    def test_cannot_go_backwards(self) -> None:
        assert not StateMachine.can_transition_phase("exploration", "opening")
        assert not StateMachine.can_transition_phase("debate", "exploration")
