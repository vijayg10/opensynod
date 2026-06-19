# Technical Stack

## Backend

| Component | Technology | Version / Notes |
|---|---|---|
| Web framework | FastAPI | Async-native, Pydantic v2 integration, auto-generates OpenAPI |
| ORM | SQLAlchemy | 2.x async; Alembic for migrations |
| Data validation | Pydantic v2 | Schemas double as OpenAPI contracts |
| ASGI server | Uvicorn | Multi-worker (ASGI) |
| Worker library | Arq | Async-native job queue; fits FastAPI's async model |
| Discussion state machine | LangGraph | AsyncPostgresSaver for durable checkpointing |
| Database | PostgreSQL 16 | ACID, full-text search (tsvector), JSONB for flexible columns |
| Pub-sub / job queue | Redis 7 | Arq job queue (`arq:queue`); pub/sub for real-time (SSE) fan-out; presence tracking |
| Auth | JWT (RS256) | Short-lived access tokens; refresh tokens in httpOnly cookies |
| Language | Python | 3.11+ (tooling targets 3.12) |

### Why FastAPI

FastAPI's native async model fits well with downstream LLM calls and database I/O. Pydantic v2 schemas serve double duty as OpenAPI contracts for the frontend, and strict typing pays off in a system with many event types and agent configurations.

### Why Arq over Celery

Arq is async-native, which avoids bridging async application code to a sync worker model. It is simpler and lighter than Celery while providing everything needed: job queuing, retries, scheduled jobs, and result storage.

### Why LangGraph

LangGraph models the discussion lifecycle as an explicit directed graph with nodes and edges. This provides:

- **Resilience:** `AsyncPostgresSaver` checkpoints graph state to PostgreSQL after every node. Worker pod death during a discussion is recoverable with no data loss.
- **Human-in-the-loop:** Human interventions are written to the `messages` table and picked up by the `check_interventions` node at the start of each agent turn, carrying them into the next turn's context.
- **Explicit state transitions:** The discussion phases (opening, exploration, debate, convergence, vote) are modeled as graph nodes with conditional edges, not as ad-hoc if/else logic.

### Why PostgreSQL Over NoSQL

The data is highly relational: discussions → messages → votes → outcomes. Audit integrity requires ACID guarantees. Full-text search via `tsvector` is sufficient for v1. PostgreSQL also handles JSONB well for flexible columns like agent config snapshots and tool call metadata.

### Why Arq + Redis Over RabbitMQ or Kafka

Arq uses Redis as its job queue backend, which means the system requires only one infrastructure dependency (Redis) instead of two. Redis already serves pub/sub and caching; using it for job queuing as well eliminates operational overhead. The throughput profile fits this product — hundreds to thousands of events per discussion — and Redis Streams / Arq is more than sufficient. Kafka is over-engineered for this scale.

---

## Frontend

| Component | Technology | Notes |
|---|---|---|
| UI framework | React 19 | |
| Build tool | Vite | Fast dev server, hot reload |
| Language | TypeScript | Strict mode |
| Routing | TanStack Router | Code-based, type-safe routes |
| Server state | TanStack Query v5 | Caching, optimistic updates, background refetch |
| Client state | Zustand | Lightweight; minimal boilerplate |
| Forms | React Hook Form + Zod | Validation co-located with schema |
| Styling | Tailwind CSS | |
| Component library | Material Tailwind + Heroicons | Prebuilt Tailwind-based components |
| Round-table visualization | SVG | Accessible (ARIA labels) |
| Virtual list | TanStack Virtual | Long transcript rendering without DOM bloat |
| Real-time | Native EventSource + WebSocket | Thin typed wrappers |

### Real-Time Architecture (Frontend)

The frontend uses two real-time channels:

- **SSE (Server-Sent Events):** One-way stream from server to client. Used for agent tokens, phase transitions, source citations, cost updates, and presence. Reconnects automatically; on reconnect, queries missed messages using `?since_message_id=`.
- **WebSocket:** Used for presence registration and heartbeats. Human interventions and votes are sent over REST.

This separation keeps reconnection logic simple and avoids coupling the high-frequency token stream to the low-frequency presence channel.

---

## LLM Providers

| Provider | Models (as configured) |
|---|---|
| Anthropic | claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5 |
| OpenAI | gpt-4o, gpt-4o-mini, o3 (via OpenAI-compatible endpoint) |
| Google | gemini-2.5-pro, gemini-2.0-flash |
| Ollama | Any locally-hosted model; base URL configurable |

The Ollama provider enables fully air-gapped deployment for organizations that cannot send data to cloud providers. By default, all panel seats are configured to use Ollama models when no cloud provider API keys are present.

An **OpenAI-compatible endpoint** setting (`openai_base_url`) allows routing to LiteLLM, OpenRouter, or any custom OpenAI-compatible proxy — useful for organizations that manage LLM access through a gateway.

---

## Tool System

The pluggable tool system allows agents to call external services during discussion turns.

### Web Search

Configurable via `SEARCH_PROVIDER` environment variable:

| Provider | Notes |
|---|---|
| Tavily | Default; optimized for LLM consumption |
| Brave | Privacy-focused |
| Serper | Google Search API |

All search results are sanitized before injection into LLM context (prompt injection defense).

### RAG (Retrieval-Augmented Generation)

Selectable via the `VECTOR_STORE` environment variable. Pluggable adapters are scaffolded for the backends below; Qdrant is wired to an external instance, while pgvector and Chroma are placeholders pending embedding integration.

| Backend | Notes |
|---|---|
| pgvector | Default; targets the existing PostgreSQL instance |
| Qdrant | External vector database |
| Chroma | Lightweight, good for development |

---

## Observability

| Component | Technology | Notes |
|---|---|---|
| Logging | Structured JSON to stdout (structlog) | Compatible with Loki, Splunk, ELK |

---

## Development Environment

| Tool | Purpose |
|---|---|
| Docker Compose | Local development (Postgres, Redis, API, worker, frontend) |
| Ruff | Python linter and formatter |
| mypy (strict) | Python type checking |
| ESLint | Frontend linting |
| pytest + pytest-asyncio | Backend testing |

---

See also: [Architecture](/technical/architecture.html) | [Configuration](/technical/configuration.html)
