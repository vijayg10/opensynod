"""Ollama (local models) LLM client via OpenAI-compatible API."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall, ToolDefinition
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.pricing import calculate_cost


class OllamaClient(BaseLLMClient):
    """Uses Ollama's OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(self, base_url: str = "http://localhost:11434", max_retries: int = 3) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self.circuit_breaker = CircuitBreaker()

    def _build_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
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

    def _build_messages(
        self, messages: list[LLMMessage], system: str | None
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if system:
            result.append({"role": "system", "content": system})
        for msg in messages:
            content = msg["content"]
            # Ollama requires string content — serialize non-string payloads (e.g. tool results)
            if not isinstance(content, str):
                content = json.dumps(content) if content else ""
            result.append({"role": msg["role"], "content": content})
        return result

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
            )
            if response.status_code >= 400:
                import logging
                logging.getLogger(__name__).error(
                    "Ollama error %s: %s (model=%s, msgs=%d)",
                    response.status_code, response.text,
                    payload.get("model"), len(payload.get("messages", [])),
                )
            response.raise_for_status()
            return response.json()

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
            raise RuntimeError("Circuit breaker open for Ollama provider")

        converted = self._build_messages(messages, system)
        payload: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = self._build_tools(tools)

        start = time.monotonic()
        try:
            data = await self._post(payload)
            self.circuit_breaker.record_success()
        except Exception:
            self.circuit_breaker.record_failure()
            raise

        latency_ms = int((time.monotonic() - start) * 1000)
        choice = data["choices"][0]
        reasoning_text = choice["message"].get("reasoning") or choice["message"].get("reasoning_content") or ""
        content_text = choice["message"].get("content") or ""
        if reasoning_text:
            content_text = f"<think>\n{reasoning_text}\n</think>\n\n{content_text}" if content_text else f"<think>\n{reasoning_text}\n</think>"
        tool_calls: list[ToolCall] = []

        for tc in choice["message"].get("tool_calls") or []:
            try:
                input_data = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, KeyError):
                input_data = {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=tc["function"]["name"],
                    input=input_data,
                )
            )

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
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
            raise RuntimeError("Circuit breaker open for Ollama provider")

        converted = self._build_messages(messages, system)
        payload: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = self._build_tools(tools)

        return self._stream_generator(payload)

    async def _stream_generator(
        self, payload: dict[str, Any]
    ) -> AsyncIterator[str | ToolCall]:
        tool_call_accum: dict[int, dict[str, Any]] = {}
        in_reasoning = False

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        import logging
                        logging.getLogger(__name__).error(
                            "Ollama stream error %s: %s (model=%s, msgs=%d)",
                            response.status_code, body.decode(errors="replace"),
                            payload.get("model"), len(payload.get("messages", [])),
                        )
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if not chunk.get("choices"):
                            continue

                        delta = chunk["choices"][0].get("delta", {})
                        
                        # Handle reasoning tokens
                        reasoning = delta.get("reasoning") or delta.get("reasoning_content")
                        if reasoning:
                            if not in_reasoning:
                                yield "<think>\n"
                                in_reasoning = True
                            yield reasoning

                        # Handle content tokens
                        content = delta.get("content")
                        if content:
                            if in_reasoning:
                                yield "\n</think>\n\n"
                                in_reasoning = False
                            yield content

                        for tc_chunk in delta.get("tool_calls") or []:
                            idx = tc_chunk.get("index", 0)
                            if idx not in tool_call_accum:
                                tool_call_accum[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc_chunk.get("id"):
                                tool_call_accum[idx]["id"] = tc_chunk["id"]
                            func = tc_chunk.get("function", {})
                            if func.get("name"):
                                tool_call_accum[idx]["name"] = func["name"]
                            if func.get("arguments"):
                                tool_call_accum[idx]["arguments"] += func["arguments"]

            if in_reasoning:
                yield "\n</think>\n\n"

            # Emit accumulated tool calls
            for tc_data in tool_call_accum.values():
                try:
                    input_data = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                except json.JSONDecodeError:
                    input_data = {}
                yield ToolCall(id=tc_data["id"], name=tc_data["name"], input=input_data)

            self.circuit_breaker.record_success()
        except Exception:
            self.circuit_breaker.record_failure()
            raise
