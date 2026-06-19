"""OpenAI (GPT-4o, o3) LLM client."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import openai
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall, ToolDefinition
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.pricing import calculate_cost


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (openai.RateLimitError, openai.InternalServerError))


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, max_retries: int = 3) -> None:
        # Use a placeholder when no key is configured so the constructor doesn't raise.
        # Actual API calls will fail with an auth error at call time if the key is invalid.
        self._client = openai.AsyncOpenAI(api_key=api_key or "sk-placeholder-not-configured")
        self._max_retries = max_retries
        self.circuit_breaker = CircuitBreaker()

    def _build_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        # OpenAI uses "parameters" instead of "input_schema"
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    def _build_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for msg in messages:
            converted.append({"role": msg["role"], "content": msg["content"]})
        return converted

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
            raise RuntimeError("Circuit breaker open for OpenAI provider")

        all_messages = list(messages)
        if system:
            all_messages = [LLMMessage(role="system", content=system)] + all_messages

        converted = self._build_messages(all_messages)
        params: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = self._build_tools(tools)
            params["tool_choice"] = "auto"

        start = time.monotonic()
        try:
            response = await self._client.chat.completions.create(**params)
            self.circuit_breaker.record_success()
        except Exception:
            self.circuit_breaker.record_failure()
            raise

        latency_ms = int((time.monotonic() - start) * 1000)
        choice = response.choices[0]
        content_text = choice.message.content or ""
        tool_calls: list[ToolCall] = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    input_data = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    input_data = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, input=input_data)
                )

        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
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
            raise RuntimeError("Circuit breaker open for OpenAI provider")

        all_messages = list(messages)
        if system:
            all_messages = [LLMMessage(role="system", content=system)] + all_messages

        converted = self._build_messages(all_messages)
        params: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            params["tools"] = self._build_tools(tools)
            params["tool_choice"] = "auto"

        return self._stream_generator(params)

    async def _stream_generator(
        self, params: dict[str, Any]
    ) -> AsyncIterator[str | ToolCall]:
        # Track tool call accumulation across chunks
        tool_call_accum: dict[int, dict[str, Any]] = {}

        try:
            async with self._client.chat.completions.stream(**params) as stream:
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    if delta.content:
                        yield delta.content

                    if delta.tool_calls:
                        for tc_chunk in delta.tool_calls:
                            idx = tc_chunk.index
                            if idx not in tool_call_accum:
                                tool_call_accum[idx] = {
                                    "id": tc_chunk.id or "",
                                    "name": tc_chunk.function.name if tc_chunk.function else "",
                                    "arguments": "",
                                }
                            if tc_chunk.id:
                                tool_call_accum[idx]["id"] = tc_chunk.id
                            if tc_chunk.function:
                                if tc_chunk.function.name:
                                    tool_call_accum[idx]["name"] = tc_chunk.function.name
                                if tc_chunk.function.arguments:
                                    tool_call_accum[idx]["arguments"] += tc_chunk.function.arguments

            # Emit accumulated tool calls after stream completes
            for tc_data in sorted(tool_call_accum.values(), key=lambda x: list(tool_call_accum.keys()).index(
                next(k for k, v in tool_call_accum.items() if v is tc_data)
            )):
                try:
                    input_data = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                except json.JSONDecodeError:
                    input_data = {}
                yield ToolCall(id=tc_data["id"], name=tc_data["name"], input=input_data)

            self.circuit_breaker.record_success()
        except Exception:
            self.circuit_breaker.record_failure()
            raise
