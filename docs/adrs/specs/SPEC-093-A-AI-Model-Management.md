# SPEC-093-A: AI Model Management Implementation

**ADR:** ADR-093
**Status:** Accepted
**Date:** 2026-03-19

## Scope

Full implementation spec for the `backend/app/ai/` module and frontend AI admin/Q&A surfaces.

---

## Database Schema

### `ai_providers`

```sql
CREATE TABLE ai_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    provider_type TEXT NOT NULL,   -- openai|anthropic|ollama|lmstudio|openrouter|custom
    base_url TEXT,                  -- NULL = provider default
    api_key_env_var TEXT,           -- env var name; NULL = no auth needed (e.g. local ollama)
    model TEXT NOT NULL,
    parameters TEXT NOT NULL DEFAULT '{}',   -- JSON: temperature, max_tokens, top_p etc.
    system_prompt TEXT,
    timeout_ms INTEGER NOT NULL DEFAULT 30000,
    retries INTEGER NOT NULL DEFAULT 3,
    is_default INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
```

### `ai_conversations`

```sql
CREATE TABLE ai_conversations (
    id TEXT PRIMARY KEY,
    set_id TEXT NOT NULL REFERENCES sets(id),
    user_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    context_summary TEXT,          -- brief of what context was sent
    model_used TEXT NOT NULL,
    provider_id TEXT REFERENCES ai_providers(id),
    tokens_in INTEGER,
    tokens_out INTEGER,
    duration_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
```

### `ai_usage_log`

```sql
CREATE TABLE ai_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT REFERENCES ai_providers(id),
    user_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    duration_ms INTEGER,
    status TEXT NOT NULL,          -- success|error
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
```

---

## File Structure

```
backend/app/ai/
    __init__.py
    models.py       — Pydantic schemas
    client.py       — AIClient ABC + concrete implementations + factory
    service.py      — CRUD + Q&A orchestration
    context.py      — Set context builder
    router.py       — FastAPI endpoints
backend/app/migrations/
    m026_ai_providers.py
```

---

## Pydantic Schemas (`models.py`)

### `ModelParameters`
```python
class ModelParameters(BaseModel):
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=200000)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
```

### `ProviderCreate`
```python
class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider_type: Literal["openai","anthropic","ollama","lmstudio","openrouter","custom"]
    base_url: str | None = None
    api_key_env_var: str | None = None
    model: str = Field(min_length=1, max_length=200)
    parameters: ModelParameters = Field(default_factory=ModelParameters)
    system_prompt: str | None = None
    timeout_ms: int = Field(30000, ge=1000, le=300000)
    retries: int = Field(3, ge=0, le=10)
    is_default: bool = False
    is_active: bool = True
```

### `ProviderUpdate` — same fields as `ProviderCreate`

### `ProviderResponse` — adds `id`, `created_by`, `created_at`, `updated_at`

### `ProviderTestResult`
```python
class ProviderTestResult(BaseModel):
    ok: bool
    latency_ms: int | None = None
    error: str | None = None
```

### `QARequest`
```python
class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    provider_id: str | None = None   # override default provider
```

### `QAResponse`
```python
class QAResponse(BaseModel):
    answer: str
    model_used: str
    provider_name: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    duration_ms: int
    conversation_id: str
```

### `ConversationResponse`
```python
class ConversationResponse(BaseModel):
    id: str
    set_id: str
    question: str
    answer: str
    model_used: str
    provider_id: str | None
    tokens_in: int | None
    tokens_out: int | None
    duration_ms: int | None
    created_at: str
```

---

## Client Abstraction (`client.py`)

### Base URL defaults per provider type
```python
DEFAULT_BASE_URLS = {
    "openai":     "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama":     "http://localhost:11434/v1",
    "lmstudio":   "http://localhost:1234/v1",
    "anthropic":  "https://api.anthropic.com",
}
```

### `AIClient` ABC
```python
class AIClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict]) -> tuple[str, int, int]: ...
    # returns (answer, tokens_in, tokens_out)

    @abstractmethod
    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]: ...

    @abstractmethod
    async def test_connection(self) -> ProviderTestResult: ...
```

### `OpenAICompatibleClient`
- POST `/chat/completions` with `{"model": ..., "messages": ..., "stream": false}`
- Auth: `Authorization: Bearer {api_key}` (omitted if no api_key_env_var)
- Retry logic: retry on `httpx.NetworkError`, `httpx.ConnectError`, HTTP 429/5xx; no retry on timeout or 4xx
- Streaming: POST with `stream: true`, parse `data: {...}` SSE lines, yield `delta.content`

### `AnthropicClient`
- POST `/v1/messages` with `{"model":..., "system":..., "messages":..., "max_tokens":...}`
- Auth: `x-api-key: {api_key}`, `anthropic-version: 2023-06-01`
- Streaming: parse `event: content_block_delta` + `data: {"delta":{"text":"..."}}` lines

### Factory
```python
def create_ai_client(provider_row: dict) -> AIClient:
    if provider_row["provider_type"] == "anthropic":
        return AnthropicClient(provider_row)
    return OpenAICompatibleClient(provider_row)
```

---

## Service Layer (`service.py`)

### Provider CRUD
- `create_provider(db, *, name, provider_type, ..., created_by) -> dict`
  - If `is_default=True`, clears existing default first
- `get_provider(db, provider_id) -> dict | None`
- `list_providers(db, *, active_only=False) -> list[dict]`
- `update_provider(db, provider_id, **updates) -> dict | None`
- `delete_provider(db, provider_id) -> bool` — refuses if is_default
- `set_default_provider(db, provider_id) -> dict | None`
- `get_default_provider(db) -> dict | None`

### Connection Test
- `test_provider(db, provider_id) -> ProviderTestResult`
  - Creates client, calls `test_connection()`, returns result

### Q&A Orchestration
- `ask_question(db, *, set_id, question, user_id, provider_id=None) -> dict`
  1. Resolve provider (specified or default)
  2. Build set context via `build_set_context()`
  3. Construct messages: system=context, user=question
  4. Call `client.chat(messages)`
  5. Store conversation in `ai_conversations`
  6. Log to `ai_usage_log`
  7. Return conversation dict

### Conversation History
- `get_conversations(db, *, set_id, limit=50, offset=0) -> list[dict]`

### Usage Logging
- `log_usage(db, *, provider_id, user_id, endpoint, model, tokens_in, tokens_out, duration_ms, status, error=None) -> None`

---

## Context Builder (`context.py`)

### `build_set_context(db, set_id, *, max_tokens=8000) -> str`

Queries:
1. Set metadata (name, description)
2. All elements in set (via `set_elements` join), current version (name, type, description, data)
3. All relationships between set elements
4. All diagrams in set, current version (name, type, description)

Output format:
```
SET: {name}
{description}

ELEMENTS ({count}):
- [{type}] {name}: {description}
  ...

RELATIONSHIPS ({count}):
- {source_name} --[{type}]--> {target_name}
  ...

DIAGRAMS ({count}):
- [{type}] {name}: {description}
  ...
```

Token budget: ~4 chars/token. If over budget, truncate proportionally across sections.

---

## API Endpoints (`router.py`)

### Admin endpoints (require `_require_admin`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/ai/providers` | List all providers |
| POST | `/api/ai/providers` | Create provider |
| GET | `/api/ai/providers/{id}` | Get provider |
| PUT | `/api/ai/providers/{id}` | Update provider |
| DELETE | `/api/ai/providers/{id}` | Delete provider |
| POST | `/api/ai/providers/{id}/test` | Test connection |
| POST | `/api/ai/providers/{id}/default` | Set as default |
| GET | `/api/ai/usage` | Usage log (with pagination) |

### User endpoints (require `get_current_user`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/ai/sets/{set_id}/ask` | Ask question (non-streaming) |
| GET | `/api/ai/sets/{set_id}/conversations` | Conversation history |

Streaming variant (SSE):
- POST `/api/ai/sets/{set_id}/ask?stream=true` — returns `text/event-stream`
- Each chunk: `data: {"chunk": "..."}\n\n`
- Final event: `data: {"done": true, "conversation_id": "..."}\n\n`

---

## Frontend

### Types (`frontend/src/lib/types/api.ts`)
```typescript
export interface AIProvider {
    id: string;
    name: string;
    provider_type: string;
    base_url: string | null;
    api_key_env_var: string | null;
    model: string;
    parameters: Record<string, unknown>;
    system_prompt: string | null;
    timeout_ms: number;
    retries: number;
    is_default: boolean;
    is_active: boolean;
    created_by: string | null;
    created_at: string;
    updated_at: string;
}

export interface QAResponse {
    answer: string;
    model_used: string;
    provider_name: string;
    tokens_in: number | null;
    tokens_out: number | null;
    duration_ms: number;
    conversation_id: string;
}

export interface AIConversation {
    id: string;
    set_id: string;
    question: string;
    answer: string;
    model_used: string;
    provider_id: string | null;
    tokens_in: number | null;
    tokens_out: number | null;
    duration_ms: number | null;
    created_at: string;
}
```

### Admin AI page (`/admin/ai`)
- Provider list table: name, type, model, default badge, active toggle, test button, edit/delete
- Add/edit modal with all provider fields
- Test connection shows latency or error inline
- Set default: radio-style selection

### SetQA component
- Chat-style interface: conversation history above, text input below
- DOMPurify sanitization on ALL AI output before `{@html}` (Protocol 7)
- Streaming: `EventSource` for streamed responses, progressive text display
- Metadata footer per message: model name, token counts, latency
- Loading state with spinner
- Collapsible "Ask AI" panel in Set detail page

---

## Security Checklist

- [x] API keys: env var names in DB only, resolved at runtime
- [x] Admin-only provider CRUD via `_require_admin()`
- [x] DOMPurify on all AI-generated content before `{@html}`
- [x] Input length cap: 4000 chars via Pydantic `max_length`
- [x] Context token budget prevents excessive LLM costs
- [x] All AI calls logged to `ai_usage_log` + audit trail
- [x] No hardcoded secrets anywhere in codebase

---

## Tests

### Backend (`backend/tests/test_ai/`)
- `test_models.py` — Pydantic validation (valid/invalid payloads, parameter ranges, max_length)
- `test_client.py` — client abstraction with mocked HTTP (`httpx.MockTransport`)
- `test_service.py` — provider CRUD, usage logging, conversation storage (real SQLite in-memory)
- `test_context.py` — set context retrieval, truncation, empty set handling
- `test_router.py` — endpoint integration (admin CRUD lifecycle, Q&A with mocked client)

### Frontend
- `SetQA.test.ts` — question submission, streaming display, DOMPurify application
- Admin AI page test — provider list, create/edit modal, test connection
