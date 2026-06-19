"""Agent runner: builds prompts, calls LLM with streaming, handles tool calls."""

from __future__ import annotations

import time
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.llm.base import LLMMessage, LLMResponse, ToolCall
from app.llm.router import LLMRouter
from app.orchestrator.schemas import TurnContext
from app.tools.registry import ToolNotFoundError, ToolRegistry

_PANEL_BASE_SYSTEM = (
    "You are a participant in an AI Round Table discussion. "
    "The goal is rigorous analysis, not validation. "
    "Support your arguments with evidence and cite sources when possible. "
    "Engage directly with other participants' arguments — agree when they are right, "
    "challenge when they are wrong. Do NOT simply agree to be agreeable."
)

_ADVERSARIAL_OVERLAY = (
    "\n\nIMPORTANT: You are in a high-stakes discussion where weak arguments must be exposed. "
    "You are expected to challenge poorly evidenced positions, not validate them."
)

# Hard ceiling on a single turn's output. Acts as a backstop to the word-limit
# instruction in the prompt so a model can't produce a wall of text.
_MAX_RESPONSE_TOKENS = 2048


def _build_system_prompt(ctx: TurnContext, adversarial_framing: bool) -> str:
    parts = [_PANEL_BASE_SYSTEM]
    if adversarial_framing:
        parts.append(_ADVERSARIAL_OVERLAY)
    if ctx.persona_system_prompt:
        parts.append(f"\n\n{ctx.persona_system_prompt}")
    if ctx.inject_challenge:
        parts.append(
            "\n\nMODERATOR NOTE: The discussion is converging too quickly. "
            "You MUST challenge the emerging consensus in your next message. "
            "Find the weakest point in the dominant argument and attack it directly."
        )
    return "\n".join(parts)


def _format_history_as_transcript(
    history: list[dict[str, Any]],
    current_seat_id: str,
) -> str:
    """Format the discussion history as a labeled transcript.

    Instead of mapping messages to assistant/user roles (which makes the LLM
    think all agent messages are its own), we build a single transcript where
    each message is clearly attributed. The LLM can then see who said what.
    """
    lines: list[str] = []
    for msg in history:
        seat = msg.get("seat_id", "system")
        author_type = msg.get("author_type", "")
        content = msg.get("content", "")
        if not content:
            continue

        if author_type == "human":
            label = f"[HUMAN]"
        elif author_type == "system":
            label = f"[MODERATOR]"
        elif seat == current_seat_id:
            label = f"[YOU — {seat}]"
        else:
            label = f"[{seat}]"

        lines.append(f"{label}: {content}")

    return "\n\n".join(lines)


def _format_interventions(interventions: list[dict[str, Any]]) -> str:
    if not interventions:
        return ""
    lines = ["\n--- Human Interventions ---"]
    for iv in interventions:
        name = iv.get("user_name", "Human")
        content = iv.get("content", "")
        lines.append(f"[{name}]: {content}")
    return "\n".join(lines)


def _build_user_message(ctx: TurnContext) -> str:
    parts = [f"Topic: {ctx.topic}\n"]

    if ctx.hidden_commitment:
        parts.append(f"Your initial commitment (sealed before discussion): {ctx.hidden_commitment}\n")

    # Include the full discussion transcript so the model sees what everyone said
    if ctx.history:
        transcript = _format_history_as_transcript(ctx.history, ctx.seat_id)
        parts.append(f"=== DISCUSSION SO FAR ===\n{transcript}\n=== END OF DISCUSSION ===\n")

    interventions = _format_interventions(ctx.pending_interventions)
    if interventions:
        parts.append(interventions + "\n")

    parts.append(
        f"You are [{ctx.seat_id}]. Respond in character based on your persona. "
        f"Do NOT repeat or paraphrase what others already said. "
        f"Build on, challenge, or add new perspectives to the discussion. "
        f"Keep your response under 150 words: lead with your single key point, then "
        f"2-4 sentences of support. No preamble, no restating the topic, no closing summary."
    )
    return "\n".join(parts)


class AgentRunner:
    """Runs a single agent turn: builds prompt, streams LLM response, handles tools."""

    def __init__(
        self,
        router: LLMRouter,
        tool_registry: ToolRegistry,
        redis_client: aioredis.Redis,
        adversarial_framing: bool = False,
    ) -> None:
        self._router = router
        self._tools = tool_registry
        self._redis = redis_client
        self._adversarial = adversarial_framing

    async def run_turn(
        self,
        ctx: TurnContext,
        model: str,
    ) -> LLMResponse:
        """Execute one agent turn. Returns the complete LLMResponse."""
        message_id = str(uuid.uuid4())
        system_prompt = _build_system_prompt(ctx, self._adversarial)

        user_content = _build_user_message(ctx)

        messages: list[LLMMessage] = [
            LLMMessage(role="user", content=user_content),
        ]

        tool_defs = self._tools.all_definitions() if ctx.allowed_tools else []

        client = self._router.get_client(model)

        # Emit message_start event
        await self._publish(ctx.session_id, {
            "event": "message_start",
            "data": {
                "message_id": message_id,
                "seat_id": ctx.seat_id,
                "phase": ctx.phase,
                "author_type": "agent",
            },
        })

        start_ms = int(time.monotonic() * 1000)
        accumulated_content = ""
        tool_calls_received: list[ToolCall] = []

        # chat_stream is async def that returns an AsyncIterator (async generator)
        stream_iter = await client.chat_stream(
            model=model,
            messages=messages,
            tools=tool_defs if tool_defs else None,
            system=system_prompt,
            max_tokens=_MAX_RESPONSE_TOKENS,
        )

        async for chunk in stream_iter:
            if isinstance(chunk, str):
                accumulated_content += chunk
                await self._publish(ctx.session_id, {
                    "event": "token",
                    "data": {
                        "seat_id": ctx.seat_id,
                        "token": chunk,
                        "message_id": message_id,
                    },
                })
            else:
                # ToolCall object
                tool_calls_received.append(chunk)

        # Handle tool calls
        sources: list[dict[str, Any]] = []
        if tool_calls_received:
            accumulated_content, tool_sources = await self._handle_tool_calls(
                ctx=ctx,
                model=model,
                messages=messages,
                system_prompt=system_prompt,
                tool_calls=tool_calls_received,
                message_id=message_id,
                prior_content=accumulated_content,
            )
            sources = tool_sources

        latency_ms = int(time.monotonic() * 1000) - start_ms

        await self._publish(ctx.session_id, {
            "event": "message_end",
            "data": {
                "message_id": message_id,
                "sources_cited": sources,
            },
        })

        # Build a synthetic LLMResponse (token counts approximated since we streamed)
        return LLMResponse(
            content=accumulated_content,
            tool_calls=[],
            input_tokens=0,
            output_tokens=len(accumulated_content.split()),
            cost_usd=0.0,
            model=model,
            latency_ms=latency_ms,
        )

    async def _handle_tool_calls(
        self,
        ctx: TurnContext,
        model: str,
        messages: list[LLMMessage],
        system_prompt: str,
        tool_calls: list[ToolCall],
        message_id: str,
        prior_content: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Execute tool calls and get the final response."""
        sources: list[dict[str, Any]] = []
        tool_results: list[Any] = []

        for tc in tool_calls:
            await self._publish(ctx.session_id, {
                "event": "source_start",
                "data": {
                    "seat_id": ctx.seat_id,
                    "query": tc.get("input", {}).get("query", ""),
                    "tool_name": tc["name"],
                },
            })

            try:
                tool = self._tools.get(tc["name"])
                output = await tool.execute(tc.get("input", {}))

                if output.get("metadata", {}).get("url"):
                    meta = output["metadata"]
                    source = {
                        "url": meta.get("url", ""),
                        "title": meta.get("title", ""),
                        "domain": meta.get("domain", ""),
                    }
                    sources.append(source)
                    await self._publish(ctx.session_id, {
                        "event": "source_ready",
                        "data": {
                            "title": source["title"],
                            "domain": source["domain"],
                            "url": source["url"],
                            "quality_signals": meta.get("quality_signals", {}),
                        },
                    })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": output.get("content", ""),
                })

            except ToolNotFoundError:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": f"Tool '{tc['name']}' not available.",
                    "is_error": True,
                })

        # Continue the conversation with tool results
        extended_messages: list[LLMMessage] = [
            *messages,
            LLMMessage(role="assistant", content=prior_content or ""),
            LLMMessage(role="user", content=tool_results),
        ]

        client = self._router.get_client(model)
        follow_up_iter = await client.chat_stream(
            model=model,
            messages=extended_messages,
            system=system_prompt,
            max_tokens=_MAX_RESPONSE_TOKENS,
        )

        final_content = ""
        async for chunk in follow_up_iter:
            if isinstance(chunk, str):
                final_content += chunk
                await self._publish(ctx.session_id, {
                    "event": "token",
                    "data": {
                        "seat_id": ctx.seat_id,
                        "token": chunk,
                        "message_id": message_id,
                    },
                })

        return (prior_content + "\n\n" + final_content).strip(), sources

    async def _publish(self, session_id: str, event: dict[str, Any]) -> None:
        import json
        await self._redis.publish(f"discussion:{session_id}", json.dumps(event))
