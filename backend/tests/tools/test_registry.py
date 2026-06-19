"""Tests for the ToolRegistry."""

import pytest
from app.tools.registry import ToolRegistry, ToolNotFoundError
from app.tools.base import BaseTool, ToolOutput
from app.llm.base import ToolDefinition


class MockTool(BaseTool):
    name = "mock_tool"
    description = "A mock tool for testing"
    input_schema = {
        "type": "object",
        "properties": {"input": {"type": "string"}},
        "required": ["input"],
    }

    async def execute(self, input: dict) -> ToolOutput:
        return ToolOutput(content=f"Result: {input.get('input', '')}", metadata={}, error=None)


class AnotherMockTool(BaseTool):
    name = "another_tool"
    description = "Another mock tool"
    input_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self, input: dict) -> ToolOutput:
        return ToolOutput(content="Another result", metadata={}, error=None)


def test_register_and_get():
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)
    retrieved = registry.get("mock_tool")
    assert retrieved is tool


def test_get_missing_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get("nonexistent_tool")


def test_names_returns_registered_names():
    registry = ToolRegistry()
    registry.register(MockTool())
    registry.register(AnotherMockTool())
    names = registry.names()
    assert "mock_tool" in names
    assert "another_tool" in names
    assert len(names) == 2


def test_all_definitions_returns_correct_format():
    registry = ToolRegistry()
    registry.register(MockTool())
    defs = registry.all_definitions()
    assert len(defs) == 1
    d = defs[0]
    assert d["name"] == "mock_tool"
    assert d["description"] == "A mock tool for testing"
    assert "properties" in d["input_schema"]


def test_contains():
    registry = ToolRegistry()
    registry.register(MockTool())
    assert "mock_tool" in registry
    assert "nonexistent" not in registry


def test_len():
    registry = ToolRegistry()
    assert len(registry) == 0
    registry.register(MockTool())
    assert len(registry) == 1
    registry.register(AnotherMockTool())
    assert len(registry) == 2


def test_register_overwrites():
    registry = ToolRegistry()
    tool1 = MockTool()
    tool2 = MockTool()
    registry.register(tool1)
    registry.register(tool2)
    assert registry.get("mock_tool") is tool2


@pytest.mark.asyncio
async def test_tool_execute():
    registry = ToolRegistry()
    registry.register(MockTool())
    tool = registry.get("mock_tool")
    result = await tool.execute({"input": "test value"})
    assert result["content"] == "Result: test value"
    assert result["error"] is None
