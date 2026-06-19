from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/opensynod")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # JWT — RS256 keys (PEM-encoded)
    jwt_private_key: str = Field(default="")
    jwt_public_key: str = Field(default="")
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # LLM Provider API Keys
    anthropic_api_key: str = Field(default="")
    google_api_key: str = Field(default="")
    ollama_base_url: str = Field(default="http://localhost:11434")

    # OpenAI-compatible endpoint (OpenAI, LiteLLM, OpenRouter, or custom wrapper)
    openai_base_url: str = Field(default="")
    openai_api_key: str = Field(default="")

    # Default Ollama models (used when no cloud provider keys are set)
    ollama_model_primary: str = Field(default="gemma4:e4b")       # moderator + advocate roles
    ollama_model_reasoning: str = Field(default="gemma4:e4b")  # devil's advocate / skeptic
    ollama_model_expert: str = Field(default="gemma4:e4b")        # neutral expert roles
    ollama_model_support: str = Field(default="gemma4:e4b")  # secondary / support roles

    # Tool / Search
    search_provider: str = Field(default="tavily")  # tavily | brave | bing | serper
    tavily_api_key: str = Field(default="")
    brave_api_key: str = Field(default="")
    serper_api_key: str = Field(default="")

    # Vector Store
    vector_store: str = Field(default="pgvector")  # pgvector | qdrant | chroma
    qdrant_url: str = Field(default="http://localhost:6333")
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8000)

    # Proxy
    https_proxy: str = Field(default="")

    # Development
    mock_llm_calls: bool = Field(default=False)

    # Cost caps
    default_org_cost_limit_usd: float = Field(default=100.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
