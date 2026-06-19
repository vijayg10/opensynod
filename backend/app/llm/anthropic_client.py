"""Anthropic (Claude) LLM client."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import anthropic
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall, ToolDefinition
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.pricing import calculate_cost


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (anthropic.RateLimitError, anthropic.InternalServerError))


class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str, max_retries: int = 3) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._max_retries = max_retries
        self.circuit_breaker = CircuitBreaker()

    def _build_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
            for t in tools
        ]

    def _build_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Split system message out (Anthropic uses a top-level system param)."""
        system: str | None = None
        converted: list[dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "system":
                system = str(msg["content"])
            else:
                converted.append({"role": msg["role"], "content": msg["content"]})
        return converted, system

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def chat(
        self,
        model: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        if self.circuit_breaker.is_open():
            raise RuntimeError(f"Circuit breaker open for Anthropic provider")

        converted, sys_from_messages = self._build_messages(messages)
        effective_system = system or sys_from_messages

        params: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
        }
        if effective_system:
            params["system"] = effective_system
        if tools:
            params["tools"] = self._build_tools(tools)

        start = time.monotonic()
        try:
            response = await self._client.messages.create(**params)
            self.circuit_breaker.record_success()
        except Exception as exc:
            self.circuit_breaker.record_failure()
            raise

        latency_ms = int((time.monotonic() - start) * 1000)
        content_text = ""
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, input=block.input)
                )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = calculate_cost(model, input_tokens, output_tokens)

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            model=model,
            latency_ms=latency_ms,
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
        if self.circuit_breaker.is_open():
            raise RuntimeError("Circuit breaker open for Anthropic provider")

        converted, sys_from_messages = self._build_messages(messages)
        effective_system = system or sys_from_messages

        params: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
        }
        if effective_system:
            params["system"] = effective_system
        if tools:
            params["tools"] = self._build_tools(tools)

        return self._stream_generator(params)

    async def _stream_generator(
        self, params: dict[str, Any]
    ) -> AsyncIterator[str | ToolCall]:
        try:
            async with self._client.messages.stream(**params) as stream:
                # Track current tool use block being assembled
                current_tool_id: str | None = None
                current_tool_name: str | None = None
                current_tool_input_json = ""

                async for event in stream:
                    event_type = type(event).__name__

                    if event_type == "RawContentBlockDeltaEvent":
                        delta = event.delta
                        if hasattr(delta, "type"):
                            if delta.type == "text_delta":
                                yield delta.text
                            elif delta.type == "input_json_delta":
                                current_tool_input_json += delta.partial_json

                    elif event_type == "RawContentBlockStartEvent":
                        block = event.content_block
                        if hasattr(block, "type") and block.type == "tool_use":
                            current_tool_id = block.id
                            current_tool_name = block.name
                            current_tool_input_json = ""

                    elif event_type == "RawContentBlockStopEvent":
                        if current_tool_id and current_tool_name:
                            import json
                            try:
                                tool_input = json.loads(current_tool_input_json) if current_tool_input_json else {}
                            except json.JSONDecodeError:
                                tool_input = {}
                            yield ToolCall(
                                id=current_tool_id,
                                name=current_tool_name,
                                input=tool_input,
                            )
                            current_tool_id = None
                            current_tool_name = None
                            current_tool_input_json = ""

            self.circuit_breaker.record_success()
        except Exception:
            self.circuit_breaker.record_failure()
            raise
