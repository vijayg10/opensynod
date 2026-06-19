"""LLM Router: routes model names to the correct provider client."""

from __future__ import annotations

from app.llm.base import BaseLLMClient
from app.core.config import get_settings


class LLMRouter:
    """Routes LLM requests to the correct provider client based on model name prefix."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._clients: dict[str, BaseLLMClient] = {}

    def _build_anthropic(self) -> BaseLLMClient:
        from app.llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=self._settings.anthropic_api_key)

    def _build_openai(self) -> BaseLLMClient:
        from app.llm.openai_compat_client import OpenAICompatClient
        return OpenAICompatClient(
            base_url=self._settings.openai_base_url,
            api_key=self._settings.openai_api_key,
        )

    def _build_google(self) -> BaseLLMClient:
        from app.llm.google_client import GoogleClient
        return GoogleClient(api_key=self._settings.google_api_key)

    def _build_ollama(self) -> BaseLLMClient:
        from app.llm.ollama_client import OllamaClient
        return OllamaClient(base_url=self._settings.ollama_base_url)

    def get_client(self, model: str) -> BaseLLMClient:
        """Return the cached provider client for the given model name.

        If MOCK_LLM_CALLS is enabled, all requests are routed to the mock client.

        Routing rules:
          - "claude-*"                  → Anthropic (direct API)
          - "gemini-*"                  → Google (direct API)
          - "gpt-*" | "o3*" | "o1*" | "*:mlm"      → OpenAI-compatible endpoint
          - anything else               → Ollama
        """
        if self._settings.mock_llm_calls:
            if "mock" not in self._clients:
                from app.llm.mock_client import MockLLMClient
                self._clients["mock"] = MockLLMClient()
            return self._clients["mock"]

        provider = self._detect_provider(model)
        if provider not in self._clients:
            self._clients[provider] = self._build_client(provider)
        return self._clients[provider]

    def _detect_provider(self, model: str) -> str:
        lower = model.lower()
        if lower.endswith(":mlm"):
            return "openai"
        if lower.startswith("claude"):
            return "anthropic"
        if lower.startswith("gemini"):
            return "google"
        if lower.startswith(("gpt-", "o3", "o1", "o3-", "o1-")):
            return "openai"
        return "ollama"

    def _build_client(self, provider: str) -> BaseLLMClient:
        builders = {
            "anthropic": self._build_anthropic,
            "openai": self._build_openai,
            "google": self._build_google,
            "ollama": self._build_ollama,
        }
        return builders[provider]()
