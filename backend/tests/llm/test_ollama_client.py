"""Tests for the Ollama LLM client using mocked HTTP."""

from __future__ import annotations

import json
import pytest
import respx
import httpx

from app.llm.ollama_client import OllamaClient
from app.llm.base import LLMMessage, ToolDefinition


MOCK_MODEL = "llama3"
BASE_URL = "http://localhost:11434"


def make_client() -> OllamaClient:
    return OllamaClient(base_url=BASE_URL)


def _non_streaming_payload(content: str, input_tokens: int = 10, output_tokens: int = 5) -> dict:
    return {
        "id": "chatcmpl-test",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": None,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
        },
    }


@pytest.mark.asyncio
async def test_chat_returns_content():
    client = make_client()

    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_non_streaming_payload("Hello from Ollama"))
        )
        result = await client.chat(
            model=MOCK_MODEL,
            messages=[LLMMessage(role="user", content="Hello")],
        )

    assert result["content"] == "Hello from Ollama"
    assert result["model"] == MOCK_MODEL
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 5


@pytest.mark.asyncio
async def test_chat_with_tool_definition():
    client = make_client()
    payload = _non_streaming_payload("")
    payload["choices"][0]["message"]["tool_calls"] = [
        {"id": "tc-1", "function": {"name": "web_search", "arguments": json.dumps({"query": "test"})}}
    ]

    tools = [
        ToolDefinition(
            name="web_search",
            description="Search",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        )
    ]

    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/v1/chat/completions").mock(return_value=httpx.Response(200, json=payload))
        result = await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Search")], tools=tools)

    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "web_search"
    assert result["tool_calls"][0]["input"] == {"query": "test"}


@pytest.mark.asyncio
async def test_streaming_tokens_arrive_in_order():
    client = make_client()

    chunks = ["Hello", " world", "!"]
    sse_lines = []
    for i, token in enumerate(chunks):
        sse_lines.append(f'data: {json.dumps({"choices": [{"delta": {"content": token}, "index": 0}]})}\n')
    sse_lines.append("data: [DONE]\n")
    sse_body = "\n".join(sse_lines)

    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(200, text=sse_body, headers={"Content-Type": "text/event-stream"})
        )
        stream = await client.chat_stream(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Hi")])
        tokens = [item async for item in stream if isinstance(item, str)]

    assert tokens == chunks
    assert "".join(tokens) == "Hello world!"


@pytest.mark.asyncio
async def test_circuit_breaker_trips_on_failures():
    client = make_client()
    client.circuit_breaker.failure_threshold = 2

    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/v1/chat/completions").mock(return_value=httpx.Response(500, text="Server error"))
        for _ in range(2):
            try:
                await client.chat(model=MOCK_MODEL, messages=[LLMMessage(role="user", content="Hi")])
            except Exception:
                pass

    assert client.circuit_breaker.is_open()
