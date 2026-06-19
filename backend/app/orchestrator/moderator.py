"""Moderator agent: makes structured decisions about discussion flow."""

from __future__ import annotations

import json
from typing import Any

from app.llm.base import LLMMessage, ToolDefinition
from app.llm.router import LLMRouter
from app.orchestrator.schemas import (
    AgentVoteDecision,
    ModeratorDecision,
    ModeratorRecommendation,
)

_MAKE_DECISION_TOOL: ToolDefinition = {
    "name": "make_moderator_decision",
    "description": (
        "Communicate your moderation decision for the next step in the discussion. "
        "You MUST call this tool after every analysis."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "next_speaker": {
                "type": "string",
                "description": "seat_id of the participant who should speak next",
            },
            "phase_transition": {
                "type": ["string", "null"],
                "enum": ["opening", "exploration", "debate", "convergence", "vote", None],
                "description": "Transition to this phase, or null to stay in current phase",
            },
            "inject_challenge": {
                "type": "boolean",
                "description": "True if you want the next speaker to challenge the emerging consensus",
            },
            "challenge_target": {
                "type": ["string", "null"],
                "description": "seat_id of the position to challenge, if inject_challenge is true",
            },
            "summary": {
                "type": ["string", "null"],
                "description": "Summary of discussion so far, if this is a summary turn",
            },
            "reasoning": {
                "type": "string",
                "description": "Your brief reasoning for this decision",
            },
        },
        "required": ["next_speaker", "inject_challenge", "reasoning"],
    },
}

_CAST_VOTE_TOOL: ToolDefinition = {
    "name": "cast_vote",
    "description": "Cast your vote on the proposed recommendation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "vote": {
                "type": "string",
                "enum": ["yes", "no", "abstain"],
                "description": "Your vote on the recommendation",
            },
            "rationale": {
                "type": "string",
                "description": "Brief rationale for your vote",
            },
        },
        "required": ["vote", "rationale"],
    },
}

_MAKE_RECOMMENDATION_TOOL: ToolDefinition = {
    "name": "make_recommendation",
    "description": "Generate the final recommendation or no-consensus statement for the session.",
    "input_schema": {
        "type": "object",
        "properties": {
            "outcome_type": {
                "type": "string",
                "enum": ["recommendation", "no_consensus"],
            },
            "statement": {
                "type": "string",
                "description": "The recommendation statement or explanation of why consensus was not reached",
            },
            "supporting_arguments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key arguments that support this recommendation",
            },
            "substantive_dissents": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Significant minority positions that deserve record",
            },
        },
        "required": ["outcome_type", "statement", "supporting_arguments", "substantive_dissents"],
    },
}


class ModeratorAgent:
    """Moderator agent that uses structured tool calling to make decisions."""

    def __init__(self, router: LLMRouter, model: str, system_prompt: str) -> None:
        self._router = router
        self._model = model
        self._system_prompt = system_prompt

    async def decide_next_turn(
        self,
        topic: str,
        current_phase: str,
        turn_count: int,
        seat_ids: list[str],
        history_summary: str,
        last_speaker: str | None,
        challenges_this_phase: int,
        convergence_speed_threshold: int,
        min_turns_before_convergence: int,
        has_devil_advocate: bool,
        devil_advocate_seat: str | None,
    ) -> ModeratorDecision:
        """Ask the moderator to decide who speaks next and whether to advance phases."""

        phase_guidance = self._build_phase_guidance(
            current_phase=current_phase,
            turn_count=turn_count,
            challenges_this_phase=challenges_this_phase,
            convergence_speed_threshold=convergence_speed_threshold,
            min_turns_before_convergence=min_turns_before_convergence,
            has_devil_advocate=has_devil_advocate,
            devil_advocate_seat=devil_advocate_seat,
        )

        user_content = (
            f"Topic: {topic}\n"
            f"Current phase: {current_phase}\n"
            f"Turn count: {turn_count}\n"
            f"Last speaker: {last_speaker or 'none'}\n"
            f"Available speakers: {', '.join(seat_ids)}\n"
            f"Challenges issued this phase: {challenges_this_phase}\n\n"
            f"Discussion summary:\n{history_summary}\n\n"
            f"{phase_guidance}\n\n"
            "Call make_moderator_decision to communicate your decision."
        )

        messages: list[LLMMessage] = [
            LLMMessage(role="user", content=user_content)
        ]

        client = self._router.get_client(self._model)
        response = await client.chat(
            model=self._model,
            messages=messages,
            tools=[_MAKE_DECISION_TOOL],
            system=self._system_prompt,
            max_tokens=1024,
        )

        # Extract tool call
        for tc in response.get("tool_calls", []):
            if tc["name"] == "make_moderator_decision":
                return self._parse_decision(tc["input"], seat_ids, last_speaker)

        # Fallback: round-robin if no tool call
        return self._fallback_decision(seat_ids, last_speaker, current_phase)

    def _build_phase_guidance(
        self,
        current_phase: str,
        turn_count: int,
        challenges_this_phase: int,
        convergence_speed_threshold: int,
        min_turns_before_convergence: int,
        has_devil_advocate: bool,
        devil_advocate_seat: str | None,
    ) -> str:
        guidance_parts: list[str] = []

        if current_phase == "opening":
            guidance_parts.append(
                "OPENING PHASE: Each participant should have given their opening statement. "
                "Once all participants have spoken, transition to 'exploration'."
            )
        elif current_phase == "exploration":
            guidance_parts.append(
                "EXPLORATION PHASE: Participants are exploring different aspects of the topic. "
                "Encourage cross-examination and clarifying questions. "
                "Transition to 'debate' when key positions have emerged and participants start disagreeing."
            )
        elif current_phase == "debate":
            if challenges_this_phase < convergence_speed_threshold and has_devil_advocate:
                guidance_parts.append(
                    f"DEBATE PHASE: Only {challenges_this_phase} challenges issued so far "
                    f"(threshold: {convergence_speed_threshold}). "
                    f"Direct {devil_advocate_seat} to challenge the emerging consensus BEFORE "
                    f"advancing to Convergence. Do NOT transition to convergence yet."
                )
            elif turn_count >= min_turns_before_convergence:
                guidance_parts.append(
                    "DEBATE PHASE: Sufficient debate has occurred. "
                    "You may transition to 'convergence' if key arguments have been thoroughly examined."
                )
            else:
                guidance_parts.append(
                    f"DEBATE PHASE: Continue debate ({turn_count} turns, minimum {min_turns_before_convergence})."
                )
        elif current_phase == "convergence":
            guidance_parts.append(
                "CONVERGENCE PHASE: Guide participants toward areas of agreement. "
                "Identify the strongest arguments on each side. "
                "Transition to 'vote' when a clear recommendation (or no-consensus) has emerged."
            )

        return "\n".join(guidance_parts)

    def _parse_decision(
        self,
        tool_input: dict[str, Any],
        seat_ids: list[str],
        last_speaker: str | None,
    ) -> ModeratorDecision:
        next_speaker = tool_input.get("next_speaker", "")
        if next_speaker not in seat_ids:
            next_speaker = self._round_robin_next(seat_ids, last_speaker)

        # Small models sometimes return schema dicts instead of values — coerce to expected types
        challenge_target = tool_input.get("challenge_target")
        if challenge_target is not None and not isinstance(challenge_target, str):
            challenge_target = None

        inject_challenge = tool_input.get("inject_challenge", False)
        if not isinstance(inject_challenge, bool):
            inject_challenge = bool(inject_challenge) if isinstance(inject_challenge, (int, str)) else False

        phase_transition = tool_input.get("phase_transition")
        if phase_transition is not None and not isinstance(phase_transition, str):
            phase_transition = None
        if isinstance(phase_transition, str):
            phase_transition = phase_transition.lower()
            if phase_transition not in ("opening", "exploration", "debate", "convergence", "vote"):
                phase_transition = None

        summary = tool_input.get("summary")
        if summary is not None and not isinstance(summary, str):
            summary = str(summary) if summary else None

        reasoning = tool_input.get("reasoning", "")
        if not isinstance(reasoning, str):
            reasoning = str(reasoning) if reasoning else ""

        return ModeratorDecision(
            next_speaker=next_speaker,
            phase_transition=phase_transition,
            inject_challenge=inject_challenge,
            challenge_target=challenge_target,
            summary=summary,
            reasoning=reasoning,
        )

    def _fallback_decision(
        self,
        seat_ids: list[str],
        last_speaker: str | None,
        current_phase: str,
    ) -> ModeratorDecision:
        next_speaker = self._round_robin_next(seat_ids, last_speaker)
        return ModeratorDecision(
            next_speaker=next_speaker,
            inject_challenge=False,
            reasoning="Fallback round-robin decision",
        )

    @staticmethod
    def _round_robin_next(seat_ids: list[str], last_speaker: str | None) -> str:
        if not seat_ids:
            return ""
        if last_speaker not in seat_ids:
            return seat_ids[0]
        idx = seat_ids.index(last_speaker)
        return seat_ids[(idx + 1) % len(seat_ids)]

    async def generate_recommendation(
        self,
        topic: str,
        history_summary: str,
        vote_tally: dict[str, int],
    ) -> ModeratorRecommendation:
        """Generate the final recommendation for the voting phase."""
        user_content = (
            f"Topic: {topic}\n\n"
            f"Discussion summary:\n{history_summary}\n\n"
            f"Preliminary vote tally: {json.dumps(vote_tally)}\n\n"
            "Based on the discussion, generate a final recommendation or no-consensus statement. "
            "Call make_recommendation with your decision."
        )

        messages: list[LLMMessage] = [LLMMessage(role="user", content=user_content)]
        client = self._router.get_client(self._model)
        response = await client.chat(
            model=self._model,
            messages=messages,
            tools=[_MAKE_RECOMMENDATION_TOOL],
            system=self._system_prompt,
            max_tokens=2048,
        )

        for tc in response.get("tool_calls", []):
            if tc["name"] == "make_recommendation":
                inp = tc["input"]
                return ModeratorRecommendation(
                    outcome_type=inp.get("outcome_type", "recommendation"),
                    statement=inp.get("statement", ""),
                    supporting_arguments=inp.get("supporting_arguments", []),
                    substantive_dissents=inp.get("substantive_dissents", []),
                )

        return ModeratorRecommendation(
            outcome_type="no_consensus",
            statement="The discussion did not reach a clear consensus.",
            supporting_arguments=[],
            substantive_dissents=[],
        )

    async def get_agent_vote(
        self,
        seat_id: str,
        model: str,
        system_prompt: str,
        topic: str,
        recommendation: ModeratorRecommendation,
        history_summary: str,
    ) -> AgentVoteDecision:
        """Get a structured vote from an agent seat."""
        user_content = (
            f"Topic: {topic}\n\n"
            f"Discussion summary:\n{history_summary}\n\n"
            f"Proposed recommendation:\n{recommendation.statement}\n\n"
            f"Supporting arguments:\n" + "\n".join(f"- {a}" for a in recommendation.supporting_arguments) + "\n\n"
            "Cast your vote on this recommendation. Call cast_vote with your decision."
        )

        messages: list[LLMMessage] = [LLMMessage(role="user", content=user_content)]
        client = self._router.get_client(model)
        response = await client.chat(
            model=model,
            messages=messages,
            tools=[_CAST_VOTE_TOOL],
            system=system_prompt,
            max_tokens=512,
        )

        for tc in response.get("tool_calls", []):
            if tc["name"] == "cast_vote":
                return AgentVoteDecision(
                    vote=tc["input"].get("vote", "abstain"),
                    rationale=tc["input"].get("rationale", ""),
                )

        return AgentVoteDecision(vote="abstain", rationale="No structured vote provided.")

    async def generate_summary(
        self,
        topic: str,
        recent_messages: list[dict[str, Any]],
    ) -> str:
        """Generate a summary of recent messages."""
        content = "\n".join(
            f"[{m.get('seat_id', 'unknown')}]: {m.get('content', '')[:300]}"
            for m in recent_messages
        )

        user_content = (
            f"Topic: {topic}\n\n"
            f"Recent discussion:\n{content}\n\n"
            "In 2-3 sentences, summarize the key points raised, areas of agreement, "
            "and unresolved tensions."
        )

        messages: list[LLMMessage] = [LLMMessage(role="user", content=user_content)]
        client = self._router.get_client(self._model)
        response = await client.chat(
            model=self._model,
            messages=messages,
            system=self._system_prompt,
            max_tokens=512,
        )
        return response.get("content", "")
