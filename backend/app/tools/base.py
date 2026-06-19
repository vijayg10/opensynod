"""Base interface for all pluggable tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class ToolOutput(TypedDict):
    content: str           # returned to LLM as tool_result
    metadata: dict[str, Any]  # stored on the Source row (URL, title, domain, etc.)
    error: str | None


class BaseTool(ABC):
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema — passed to LLM as ToolDefinition

    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> ToolOutput:
        """Execute the tool with the given input and return structured output."""
        ...
