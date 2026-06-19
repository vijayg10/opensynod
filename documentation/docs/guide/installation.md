# Installation Guide

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Docker + Docker Compose v2 | Latest | Required for the infrastructure stack |
| Python | 3.11+ | Backend development only |
| Node.js | 20+ | Frontend development only |
| `uv` | Latest | Recommended Python package manager (or use `pip`) |


## Clone the Repository

```bash
git clone https://github.com/vijayg10/opensynod
cd opensynod
```

## Environment Configuration

Copy the example environment file and fill in the required values:

```bash
cp .env.example .env
```

**Minimum required variables for local development:**

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/opensynod
REDIS_URL=redis://localhost:6379/0
JWT_PRIVATE_KEY=<generated>
JWT_PUBLIC_KEY=<generated>
MOCK_LLM_CALLS=true   # or provide at least one LLM API key
```

### Generating JWT Keys

```bash
openssl genrsa -out private.pem 4096
openssl rsa -in private.pem -pubout -out public.pem
```

Copy contents into `.env`:

```bash
JWT_PRIVATE_KEY="$(cat private.pem)"
JWT_PUBLIC_KEY="$(cat public.pem)"
```

### LLM Provider Keys

Set at least one provider key, or set `MOCK_LLM_CALLS=true` to run without API keys:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434   # for local models
```

---

## Option 1: Docker Compose (Recommended)

The fastest way to run the full stack locally:

```bash
docker compose -f infra/docker-compose.yml up
```

This starts:

| Service | Port |
|---|---|
| PostgreSQL | 5432 |
| Redis | 6379 |
| FastAPI backend | 8000 |
| Arq worker | — |
| React frontend | 5173 |

Alembic migrations run automatically on startup. Open `http://localhost:5173` to use the app.


## Option 2: Backend Without Docker

For faster backend iteration, run infrastructure services in Docker and the Python app directly:

```bash
# Start infrastructure only
docker compose -f infra/docker-compose.yml up postgres redis -d

# Install Python dependencies
cd backend
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the API server
uv run uvicorn app.main:app --reload --port 8000

# Start the worker (separate terminal)
uv run arq app.workers.arq_settings.WorkerSettings
```

Swagger UI available at `http://localhost:8000/docs`.


## Option 3: Frontend Without Docker

```bash
cd frontend
npm install
npm run dev
```

The dev server at `http://localhost:5173` proxies `/api` and `/ws` requests to `localhost:8000`.


## Running Tests

**Backend:**
```bash
cd backend
uv run pytest tests/ -v
```

**Frontend:**
```bash
cd frontend
npm run test
```

**End-to-end (Playwright):** Requires the full Docker Compose stack running with `MOCK_LLM_CALLS=true`:
```bash
cd frontend
npx playwright test
```
