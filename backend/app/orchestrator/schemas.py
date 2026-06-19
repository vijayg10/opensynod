"""Pydantic schemas for the discussion orchestrator."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ModeratorDecision(BaseModel):
    """Structured output from the Moderator agent after each turn."""

    next_speaker: str
    phase_transition: Literal["opening", "exploration", "debate", "convergence", "vote"] | None = None
    inject_challenge: bool = False
    challenge_target: str | None = None
    summary: str | None = None
    reasoning: str = ""


class AgentVoteDecision(BaseModel):
    """Structured output from an agent during the voting phase."""

    vote: Literal["yes", "no", "abstain"]
    rationale: str


class ModeratorRecommendation(BaseModel):
    """Structured output from Moderator for the voting phase."""

    outcome_type: Literal["recommendation", "no_consensus"]
    statement: str
    supporting_arguments: list[str] = Field(default_factory=list)
    substantive_dissents: list[str] = Field(default_factory=list)


class TurnContext(BaseModel):
    """Context passed to each agent during their turn."""

    session_id: str
    seat_id: str
    phase: str
    topic: str
    hidden_commitment: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)
    pending_interventions: list[dict[str, Any]] = Field(default_factory=list)
    inject_challenge: bool = False
    persona_system_prompt: str = ""
    panel_system_prompt: str = ""
    allowed_tools: list[str] = Field(default_factory=list)


