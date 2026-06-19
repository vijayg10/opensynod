# Architecture

## High-Level Overview

![High-Level Architecture](/opensynod-architecture.drawio.svg)

## Components

### React Frontend

The frontend is a React 19 single-page application built with Vite and TypeScript.

**Responsibilities:**
- Renders all UI screens
- Receives streamed agent tokens, phase changes, presence updates, intervention events, and vote events via SSE
- Maintains a WebSocket connection per active discussion for presence and participant events
- Sends user interventions and votes via REST
- Uses REST for all other non-real-time operations

The frontend never calls LLM providers directly. All inference is server-side.

### FastAPI Backend (REST API)

The REST API handles all CRUD operations and non-streaming endpoints.

**Responsibilities:**
- Session management
- Panel management
- Voting
- Export
- Audit log
- Authentication
- Cost estimation

**Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic migrations, Uvicorn workers.

Starting a discussion enqueues an Arq job to Redis (`arq:queue`); the API does not run the discussion loop itself.

### WebSocket Gateway

A FastAPI WebSocket endpoint (mounted on the API service) that handles long-lived bidirectional connections.

**Responsibilities:**
- Authenticate WebSocket connections via JWT handshake
- Register and track presence in Redis with TTL-based heartbeats, publishing presence updates to the discussion's Redis pub/sub channel
- Accept inbound user events (interventions, votes, presence pings, source flags), persist them, and publish them to the discussion's Redis pub/sub channel

Real-time outbound streaming (tokens, phase changes, presence, vote updates) is delivered to clients over SSE, which subscribes to the same `discussion:{id}` Redis pub/sub channel.


### Discussion Orchestrator (Worker Pool)

The core of the product. Arq async workers execute discussion state machines backed by LangGraph.

**Responsibilities:**
- Pick up `run_discussion` or `resume_discussion` jobs from the Arq Redis queue (`arq:queue`)
- Instantiate and run the LangGraph StateGraph for the discussion
- Execute the discussion lifecycle as explicit graph nodes:
  - `commit_phase` — hidden-position commitment protocol
  - `opening_phase` — transition to running, emit phase_change
  - `moderator_turn` — moderator decides next speaker, checks phase transitions and cost cap
  - `check_interventions` — query the DB for human interventions written since the last agent turn
  - `agent_turn` — build prompt, call LLM with streaming, persist message
  - `voting_phase` — collect agent votes, compute outcome, conclude session
- Handle web search and RAG tool calls inline within `agent_turn`
- Bridge LangGraph streaming events to Redis pub/sub

**Resilience via LangGraph checkpointing.** LangGraph's `AsyncPostgresSaver` checkpoints graph state to PostgreSQL after every completed node. If a worker pod dies mid-discussion, the next `resume_discussion()` call re-enters the graph at the last committed node automatically — no data loss, no manual reconstruction.

**Human-in-the-loop.** Human interventions are written to the `messages` table by the API (via REST or the WebSocket gateway). The `check_interventions` node runs at the start of every agent turn and queries the DB for any human messages added since the last agent turn, carrying them into the next `agent_turn` context. Because the discussion loop is naturally gated by LLM call latency, interventions written between turns are reliably collected without needing to suspend the graph.

---

### LLM Provider Abstraction Layer

A shared Python module used by the orchestrator. Provides a common interface across all four providers.

**Interface:**
```python
async def chat(model, messages, tools, system, max_tokens) -> LLMResponse
async def chat_stream(model, messages, tools, system, max_tokens) -> AsyncIterator[str | ToolCall]
```

**Each provider implementation handles:**
- Tool-use schema translation (Anthropic, OpenAI, and Google each use different formats)
- Streaming normalization (each provider streams differently)
- Exponential backoff retry on transient errors
- Rate limit header reading and back-off
- Token counting and cost calculation per pricing tables
- Timeout and circuit breaker per provider

The LLM Router maps model name prefixes (`claude-*`, `gpt-*`, `gemini-*`) to the appropriate client. Everything else routes to the Ollama client.

---

### PostgreSQL

The system of record for all durable data.

**Key schemas:**
- `users`, `teams`, `team_memberships` — identity
- `panels` — curated and custom panel definitions
- `sessions` — top-level discussion records
- `messages` — every agent and human message (append-only)
- `sources` — web search and RAG results cited during discussions
- `votes` — agent and human votes
- `outcomes` — final recommendation documents
- `audit_events` — complete audit log (append-only, no deletes ever)
- LangGraph checkpointer tables — execution state (not audit-relevant)

Full-text search on `messages.content` via PostgreSQL `tsvector`. Append-only enforcement via database-level triggers blocking UPDATE and DELETE on message and audit tables.

---

### Redis

Serves as both the job queue backend (via Arq) and the real-time pub/sub layer. Not a system of record — Redis data loss causes degradation but not data loss.

**Job queue (`arq:queue`):**
- `run_discussion` — start a new discussion
- `resume_discussion` — resume after pause or crash
- `inject_intervention` — push a human intervention into a suspended graph
- `run_voting` — run the voting phase after force-end

**Pub/sub (`discussion:{id}` channels):**
- Token streaming fan-out to all connected clients
- Phase change events, presence updates, intervention broadcasts, vote updates

**Other uses:**
- Presence tracking via TTL-keyed hashes

---

## Key Data Flows

### Starting a Discussion

1. User clicks Start on the Discussion Rules screen
2. Frontend POSTs to `POST /sessions/{id}/start`
3. FastAPI validates, updates session status to `queued`, enqueues a `run_discussion` Arq job on `arq:queue`
4. An orchestrator worker picks up the job, begins the LangGraph state machine
5. Frontend opens SSE stream and WebSocket connection to the session
6. Tokens stream as agents begin speaking

### Agent Turn Execution

1. Orchestrator `moderator_turn` node determines the next speaker
2. `agent_turn` node builds the agent's prompt from system prompt, persona, history, and any queued interventions
3. Calls the LLM via the provider abstraction with streaming
4. As tokens arrive, they are published to `discussion:{id}` on Redis pub/sub
5. The SSE stream forwards tokens to all connected clients
6. When the message is complete, the full message is written to PostgreSQL with metadata, cost, and source citations

### Human Intervention

1. User types an intervention and clicks Send
2. Frontend POSTs to `POST /sessions/{id}/interventions` (the WebSocket gateway also accepts interventions)
3. The API writes to the `messages` table and publishes to `discussion:{id}` on Redis pub/sub for live clients
4. On its next turn, the orchestrator's `check_interventions` node queries the DB and picks up the new message into `pending_interventions`
5. The intervention enters the next `agent_turn` context

### Voting and Outcome

1. Moderator determines discussion is complete
2. Orchestrator transitions to `voting` status, emits `phase_change` event
3. Each agent receives a structured voting prompt, returns a structured vote
4. Frontend navigates to the voting screen via `phase_change` SSE event
5. Humans cast votes via REST
6. When voting closes, orchestrator writes the `outcomes` row, transitions to `concluded`
7. Audit record is now immutable

---

## LangGraph Policy

`langgraph` and `langgraph-checkpoint-postgres` are pinned to minor-version ranges. LangGraph is still maturing; minor version bumps require staging tests against in-flight discussion checkpoints before production rollout.

`langchain`, `langchain-core`, and related LangChain packages are not application dependencies. If LangGraph pulls in `langchain-core` transitively, that is acceptable — but no LangChain abstractions appear in application code.
