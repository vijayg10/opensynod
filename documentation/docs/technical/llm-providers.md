# LLM Providers

OpenSynod supports four LLM provider categories through a unified abstraction layer. Application code never imports provider SDKs directly — all inference goes through a common interface.

## Supported Providers

| Provider | Models |
|---|---|
| Anthropic | Claude Opus, Claude Sonnet, Claude Haiku |
| OpenAI | GPT-4o, GPT-4o mini, o3 |
| Google | Gemini 2.5 Pro, Gemini 2.0 Flash |
| Ollama | Any locally-hosted model (Llama, Mistral, Gemma, etc.) |

For organizations that cannot send data to cloud providers, Ollama support enables fully air-gapped operation with locally-hosted models.

---

## Provider Abstraction Interface

All providers implement:

```python
async def chat(model, messages, tools, system, max_tokens) -> LLMResponse
async def chat_stream(model, messages, tools, system, max_tokens) -> AsyncIterator[str | ToolCall]
```

Each provider implementation handles:
- Tool-use schema translation (Anthropic, OpenAI, and Google each use different formats)
- Streaming normalization
- Exponential backoff retry on transient and rate-limit errors (via tenacity)
- Token counting and cost calculation per pricing tables
- Timeout and circuit breaker per provider

---

## Model Resolution

The LLM Router maps model name prefixes to provider clients:

| Model prefix | Provider |
|---|---|
| `claude-*` | Anthropic |
| `gpt-*`, `o3*` | OpenAI |
| `gemini-*` | Google |
| Anything else | Ollama |

Routing is by model-name prefix only — each seat's configured `model` determines its provider.

---

## Configuring Provider Keys

Set keys in `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
```

Set `MOCK_LLM_CALLS=true` to replace all calls with canned streaming responses — useful for development and CI without spending API credits.
