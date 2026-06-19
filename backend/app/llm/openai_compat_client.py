"""OpenAI-compatible LLM client.

Talks to any endpoint that implements the /v1/chat/completions API:
OpenAI, LiteLLM, OpenRouter, or a custom agent wrapper service.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class OpenAICompatClient(BaseLLMClient):
    """OpenAI-compatible HTTP client."""

    def __init__(self, base_url: str, api_key: str = "") -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

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
            if not isinstance(content, str):
                content = json.dumps(content) if content else ""
            result.append({"role": msg["role"], "content": content})
        return result

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            if response.status_code >= 400:
                logger.error(
                    "Gateway error %s: %s (model=%s)",
                    response.status_code, response.text[:500],
                    payload.get("model"),
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
        data = await self._post(payload)
        latency_ms = int((time.monotonic() - start) * 1000)

        choice = data["choices"][0]
        content_text = choice["message"].get("content") or ""
        tool_calls: list[ToolCall] = []

        for tc in choice["message"].get("tool_calls") or []:
            try:
                input_data = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, KeyError):
                input_data = {}
            tool_calls.append(
                ToolCall(id=tc.get("id", ""), name=tc["function"]["name"], input=input_data)
            )

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
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

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    logger.error(
                        "Gateway stream error %s: %s (model=%s)",
                        response.status_code, body.decode(errors="replace")[:500],
                        payload.get("model"),
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
                    if delta.get("content"):
                        yield delta["content"]

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

        for tc_data in tool_call_accum.values():
            try:
                input_data = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
            except json.JSONDecodeError:
                input_data = {}
            yield ToolCall(id=tc_data["id"], name=tc_data["name"], input=input_data)
