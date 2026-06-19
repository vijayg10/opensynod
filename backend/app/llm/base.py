"""Common interface for all LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Literal, TypedDict


class LLMMessage(TypedDict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[Any]  # supports tool_result content blocks


class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema


class ToolCall(TypedDict):
    id: str
    name: str
    input: dict[str, Any]


class LLMResponse(TypedDict):
    content: str
    tool_calls: list[ToolCall]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str
    latency_ms: int


class BaseLLMClient(ABC):
    """Abstract base for all LLM provider clients."""

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Non-streaming completion. Returns full response."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        model: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[str | ToolCall]:
        """Streaming completion. Yields str tokens, then ToolCall objects if tool use triggered."""
        ...
