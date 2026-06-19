"""Tests for the Anthropic LLM client using mocked HTTP."""

from __future__ import annotations

import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMMessage, ToolDefinition


MOCK_MODEL = "claude-sonnet-4-6"


def make_client() -> AnthropicClient:
    return AnthropicClient(api_key="test-key")


@pytest.mark.asyncio
async def test_chat_returns_llm_response():
    client = make_client()

    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Hello, I am Claude.")]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)

    with patch.object(client._client.messages, "create", new=AsyncMock(return_value=mock_response)):
        result = await client.chat(
            model=MOCK_MODEL,
            messages=[LLMMessage(role="user", content="Hello")],
        )

    assert result["content"] == "Hello, I am Claude."
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 5
    assert result["model"] == MOCK_MODEL
    assert result["cost_usd"] >= 0
    assert result["latency_ms"] >= 0
    assert result["tool_calls"] == []


@pytest.mark.asyncio
async def test_chat_with_system_message():
    client = make_client()

    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Response")]
    mock_response.usage = MagicMock(input_tokens=20, output_tokens=10)

    create_mock = AsyncMock(return_value=mock_response)
    with patch.object(client._client.messages, "create", new=create_mock):
        await client.chat(
            model=MOCK_MODEL,
            messages=[
                LLMMessage(role="system", content="You are helpful"),
                LLMMessage(role="user", content="Hello"),
            ],
        )

    call_kwargs = create_mock.call_args[1]
    assert call_kwargs.get("system") == "You are helpful"
    # system message should not appear in messages list
    for msg in call_kwargs.get("messages", []):
        assert msg.get("role") != "system"


@pytest.mark.asyncio
async def test_chat_with_tool_call():
    client = make_client()

    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.id = "tool-123"
    tool_use_block.name = "web_search"
    tool_use_block.input = {"query": "latest news"}

    mock_response = MagicMock()
    mock_response.content = [tool_use_block]
    mock_response.usage = MagicMock(input_tokens=30, output_tokens=15)

    tools = [
        ToolDefinition(
            name="web_search",
            description="Search the web",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        )
    ]

    with patch.object(client._client.messages, "create", new=AsyncMock(return_value=mock_response)):
        result = await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Search for news")], tools=tools)

    assert len(result["tool_calls"]) == 1
    tc = result["tool_calls"][0]
    assert tc["id"] == "tool-123"
    assert tc["name"] == "web_search"
    assert tc["input"] == {"query": "latest news"}


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    client = make_client()
    client.circuit_breaker.failure_threshold = 2

    import anthropic
    with patch.object(
        client._client.messages,
        "create",
        new=AsyncMock(side_effect=anthropic.InternalServerError(
            response=MagicMock(status_code=500, headers={}),
            body="Server error",
            message="Server error",
        )),
    ):
        for _ in range(2):
            try:
                await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Hi")])
            except Exception:
                pass

    assert client.circuit_breaker.is_open()


@pytest.mark.asyncio
async def test_chat_raises_when_circuit_breaker_open():
    client = make_client()
    client.circuit_breaker._state = __import__("app.llm.circuit_breaker", fromlist=["CircuitState"]).CircuitState.OPEN
    client.circuit_breaker._failure_count = 99

    with pytest.raises(RuntimeError, match="Circuit breaker open"):
        await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Hi")])


@pytest.mark.asyncio
async def test_cost_calculation_matches_expected():
    client = make_client()
    # claude-sonnet-4-6: $3/M input, $15/M output
    # 1M input + 1M output = $18
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Test")]
    mock_response.usage = MagicMock(input_tokens=1_000_000, output_tokens=1_000_000)

    with patch.object(client._client.messages, "create", new=AsyncMock(return_value=mock_response)):
        result = await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Test")])

    assert result["cost_usd"] == pytest.approx(18.0, rel=1e-5)
