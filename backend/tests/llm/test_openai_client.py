"""Tests for the OpenAI LLM client using mocked HTTP."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.openai_client import OpenAIClient
from app.llm.base import LLMMessage, ToolDefinition


MOCK_MODEL = "gpt-4o"


def make_client() -> OpenAIClient:
    return OpenAIClient(api_key="test-key")


def _make_openai_response(content: str, input_tokens: int = 10, output_tokens: int = 5):
    choice = MagicMock()
    choice.message = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = None

    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(prompt_tokens=input_tokens, completion_tokens=output_tokens)
    return response


@pytest.mark.asyncio
async def test_chat_returns_content():
    client = make_client()
    mock_response = _make_openai_response("Hello from GPT-4o")

    with patch.object(
        client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)
    ):
        result = await client.chat(
            model=MOCK_MODEL,
            messages=[LLMMessage(role="user", content="Hello")],
        )

    assert result["content"] == "Hello from GPT-4o"
    assert result["model"] == MOCK_MODEL
    assert result["tool_calls"] == []


@pytest.mark.asyncio
async def test_chat_with_system_prompt():
    client = make_client()
    mock_response = _make_openai_response("OK")
    create_mock = AsyncMock(return_value=mock_response)

    with patch.object(client._client.chat.completions, "create", new=create_mock):
        await client.chat(
            model=MOCK_MODEL,
            messages=[LLMMessage(role="user", content="Hi")],
            system="You are a helpful assistant",
        )

    call_kwargs = create_mock.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a helpful assistant"


@pytest.mark.asyncio
async def test_chat_tool_call_round_trip():
    client = make_client()

    tc = MagicMock()
    tc.id = "call_abc123"
    tc.function = MagicMock()
    tc.function.name = "web_search"
    tc.function.arguments = json.dumps({"query": "AI news"})

    choice = MagicMock()
    choice.message = MagicMock()
    choice.message.content = ""
    choice.message.tool_calls = [tc]

    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(prompt_tokens=25, completion_tokens=10)

    tools = [
        ToolDefinition(
            name="web_search",
            description="Search",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        )
    ]

    with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=response)):
        result = await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Search AI news")], tools=tools)

    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "web_search"
    assert result["tool_calls"][0]["input"]["query"] == "AI news"


@pytest.mark.asyncio
async def test_cost_calculation_matches_expected():
    client = make_client()
    # gpt-4o: $2.50/M input, $10/M output
    mock_response = _make_openai_response("Test", input_tokens=2_000_000, output_tokens=1_000_000)

    with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)):
        result = await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Test")])

    # 2M input * $2.50 + 1M output * $10 = $5 + $10 = $15
    assert result["cost_usd"] == pytest.approx(15.0, rel=1e-5)


@pytest.mark.asyncio
async def test_circuit_breaker_trips_on_failures():
    client = make_client()
    client.circuit_breaker.failure_threshold = 2

    import openai
    with patch.object(
        client._client.chat.completions,
        "create",
        new=AsyncMock(side_effect=openai.InternalServerError(
            response=MagicMock(status_code=500, headers={}, request=MagicMock()),
            body=None,
            message="Server error",
        )),
    ):
        for _ in range(2):
            try:
                await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Hi")])
            except Exception:
                pass

    assert client.circuit_breaker.is_open()
