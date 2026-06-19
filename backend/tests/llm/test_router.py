"""Tests for the LLM Router."""

import pytest
from app.llm.router import LLMRouter
from app.llm.anthropic_client import AnthropicClient
from app.llm.openai_client import OpenAIClient
from app.llm.google_client import GoogleClient
from app.llm.ollama_client import OllamaClient


def make_router() -> LLMRouter:
    return LLMRouter()


def test_routes_claude_to_anthropic():
    router = make_router()
    client = router.get_client("claude-opus-4-7")
    assert isinstance(client, AnthropicClient)


def test_routes_sonnet_to_anthropic():
    router = make_router()
    client = router.get_client("claude-sonnet-4-6")
    assert isinstance(client, AnthropicClient)


def test_routes_gpt4o_to_openai():
    router = make_router()
    client = router.get_client("gpt-4o")
    assert isinstance(client, OpenAIClient)


def test_routes_o3_to_openai():
    router = make_router()
    client = router.get_client("o3")
    assert isinstance(client, OpenAIClient)


def test_routes_gemini_to_google():
    router = make_router()
    client = router.get_client("gemini-2.5-pro")
    assert isinstance(client, GoogleClient)


def test_routes_unknown_to_ollama():
    router = make_router()
    client = router.get_client("llama3")
    assert isinstance(client, OllamaClient)


def test_routes_mistral_to_ollama():
    router = make_router()
    client = router.get_client("mistral-7b")
    assert isinstance(client, OllamaClient)


def test_caches_clients():
    router = make_router()
    c1 = router.get_client("claude-sonnet-4-6")
    c2 = router.get_client("claude-haiku-4-5")
    # Same provider → same cached instance
    assert c1 is c2


def test_different_providers_have_different_clients():
    router = make_router()
    anthropic_client = router.get_client("claude-sonnet-4-6")
    openai_client = router.get_client("gpt-4o")
    assert anthropic_client is not openai_client
