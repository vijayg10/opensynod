# Configuration

OpenSynod is configured via environment variables. In local development, these are loaded from a `.env` file in the backend directory.

## Application

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `API_PREFIX` | `/api/v1` | URL prefix for all REST endpoints |

## Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/opensynod` | PostgreSQL connection string. Must use the `asyncpg` driver. |

## Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |

## Authentication

JWT signing uses RS256 (asymmetric). Generate a key pair and provide the PEM-encoded values.

| Variable | Default | Description |
|---|---|---|
| `JWT_PRIVATE_KEY` | _(required)_ | PEM-encoded RSA private key for signing JWTs |
| `JWT_PUBLIC_KEY` | _(required)_ | PEM-encoded RSA public key for verification |
| `JWT_ALGORITHM` | `RS256` | Signing algorithm (do not change) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime in days |

**Generating keys:**
```bash
openssl genrsa -out private.pem 4096
openssl rsa -in private.pem -pubout -out public.pem
```

## LLM Providers

At least one LLM provider must be configured.

### Anthropic

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |

### OpenAI / Compatible Endpoint

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_BASE_URL` | Override base URL for OpenAI-compatible endpoints (LiteLLM, OpenRouter, custom proxy) |

If `OPENAI_BASE_URL` is set, all OpenAI client calls use this base URL instead of the default OpenAI endpoint.

### Google

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Google AI API key (Gemini) |

### Ollama

| Variable | Description |
|---|---|
| `OLLAMA_BASE_URL` | Ollama server URL |
| `OLLAMA_MODEL_PRIMARY` | Model for moderator and advocate roles |
| `OLLAMA_MODEL_REASONING` | Model for devil's advocate / skeptic roles |
| `OLLAMA_MODEL_EXPERT` | Model for neutral expert roles |
| `OLLAMA_MODEL_SUPPORT` | Model for secondary / support roles |


## Tool System — Web Search

| Variable | Default | Description |
|---|---|---|
| `SEARCH_PROVIDER` | `tavily` | Search provider: `tavily`, `brave`, `bing`, `serper` |
| `TAVILY_API_KEY` | _(empty)_ | Tavily API key (used when `SEARCH_PROVIDER=tavily`) |
| `BRAVE_API_KEY` | _(empty)_ | Brave Search API key |
| `SERPER_API_KEY` | _(empty)_ | Serper API key |

## Cost Control

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_ORG_COST_LIMIT_USD` | `100.0` | Default monthly LLM spend limit per organization in USD |

## Development

| Variable | Default | Description |
|---|---|---|
| `MOCK_LLM_CALLS` | `false` | When `true`, replaces all LLM calls with a mock client that returns canned responses. Useful for frontend development and integration testing without API keys. |

---

## Local Development (.env)

Copy `.env.example` to `.env` in the `backend/` directory and fill in the values.

::: tip Ollama in Docker Compose
When running Ollama locally and accessing it from within Docker Compose, use `http://host.docker.internal:<port>` as the `OLLAMA_BASE_URL`. This resolves to the host machine from within a Docker container on macOS and Windows.
:::
