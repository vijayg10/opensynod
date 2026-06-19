"""Google (Gemini) LLM client using the google-genai SDK."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types as genai_types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.llm.base import BaseLLMClient, LLMMessage, LLMResponse, ToolCall, ToolDefinition
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.pricing import calculate_cost


def _is_retryable(exc: BaseException) -> bool:
    exc_name = type(exc).__name__
    return "ResourceExhausted" in exc_name or "ServiceUnavailable" in exc_name or "TooManyRequests" in exc_name


class GoogleClient(BaseLLMClient):
    def __init__(self, api_key: str, max_retries: int = 3) -> None:
        # Use a placeholder when no key is configured so the constructor doesn't raise.
        # Actual API calls will fail with an auth error at call time if the key is invalid.
        self._client = genai.Client(api_key=api_key or "placeholder-not-configured")
        self._max_retries = max_retries
        self.circuit_breaker = CircuitBreaker()

    def _build_tools(self, tools: list[ToolDefinition]) -> list[genai_types.Tool]:
        function_declarations = []
        for t in tools:
            schema = dict(t["input_schema"])
            schema.pop("$schema", None)

            # Build parameter schema for Google
            properties = {}
            for prop_name, prop_def in schema.get("properties", {}).items():
                prop_type = prop_def.get("type", "string").upper()
                properties[prop_name] = genai_types.Schema(
                    type=getattr(genai_types.Type, prop_type, genai_types.Type.STRING),
                    description=prop_def.get("description", ""),
                )

            func_decl = genai_types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties=properties,
                    required=schema.get("required", []),
                ),
            )
            function_declarations.append(func_decl)

        return [genai_types.Tool(function_declarations=function_declarations)]

    def _build_contents(
        self, messages: list[LLMMessage], system: str | None
    ) -> tuple[str | None, list[genai_types.Content]]:
        """Convert LLMMessages to Google Content format."""
        system_text = system
        contents: list[genai_types.Content] = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_text = str(content)
                continue

            # Google uses "user" and "model" roles
            google_role = "model" if role == "assistant" else "user"
            contents.append(
                genai_types.Content(
                    role=google_role,
                    parts=[genai_types.Part.from_text(text=str(content))],
                )
            )

        return system_text, contents

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
            raise RuntimeError("Circuit breaker open for Google provider")

        system_text, contents = self._build_contents(messages, system)

        config_kwargs: dict[str, Any] = {"max_output_tokens": max_tokens}
        if system_text:
            config_kwargs["system_instruction"] = system_text
        if tools:
            config_kwargs["tools"] = self._build_tools(tools)

        gen_config = genai_types.GenerateContentConfig(**config_kwargs)

        start = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=gen_config,
            )
            self.circuit_breaker.record_success()
        except Exception:
            self.circuit_breaker.record_failure()
            raise

        latency_ms = int((time.monotonic() - start) * 1000)
        content_text = ""
        tool_calls: list[ToolCall] = []

        for part in response.candidates[0].content.parts if response.candidates else []:
            if hasattr(part, "text") and part.text:
                content_text += part.text
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append(
                    ToolCall(
                        id=fc.id or fc.name,
                        name=fc.name,
                        input=dict(fc.args) if fc.args else {},
                    )
                )

        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0

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
            raise RuntimeError("Circuit breaker open for Google provider")

        system_text, contents = self._build_contents(messages, system)

        config_kwargs: dict[str, Any] = {"max_output_tokens": max_tokens}
        if system_text:
            config_kwargs["system_instruction"] = system_text
        if tools:
            config_kwargs["tools"] = self._build_tools(tools)

        gen_config = genai_types.GenerateContentConfig(**config_kwargs)

        return self._stream_generator(model, contents, gen_config)

    async def _stream_generator(
        self,
        model: str,
        contents: list[genai_types.Content],
        config: genai_types.GenerateContentConfig,
    ) -> AsyncIterator[str | ToolCall]:
        try:
            async for chunk in await self._client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                for part in chunk.candidates[0].content.parts if chunk.candidates else []:
                    if hasattr(part, "text") and part.text:
                        yield part.text
                    elif hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        yield ToolCall(
                            id=fc.id or fc.name,
                            name=fc.name,
                            input=dict(fc.args) if fc.args else {},
                        )
            self.circuit_breaker.record_success()
        except Exception:
            self.circuit_breaker.record_failure()
            raise
