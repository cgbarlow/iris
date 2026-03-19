# ADR-093: AI Model Management Foundations

**Status:** Accepted
**Date:** 2026-03-19
**Depends on:** ADR-001 (RBAC), ADR-012 (Sets), ADR-021 (Settings)

## Context

Iris needs AI capabilities — Q&A over sets of architectural elements, generation assistance, and
analysis. Multiple LLM providers exist (OpenAI, Anthropic, Ollama, LM Studio, OpenRouter, custom
OpenAI-compatible endpoints) and the right choice varies by deployment context: cloud deployments
may use OpenAI or Anthropic, air-gapped enterprise deployments need Ollama/LM Studio.

The machine-dream_ag project has proven patterns for multi-provider LLM management: a profile
system for named configurations, a client abstraction with provider-specific implementations, a
factory function, and retry logic distinguishing retryable (network/5xx) from non-retryable
(timeout/auth) errors. These patterns need translation from TypeScript/JSON-file (per-user CLI
profiles) to Python/SQLite (system-wide admin-managed providers).

The first consumer feature is **Set-scoped Q&A** — users ask natural language questions about
entities and diagrams within a Set, with the AI given structured context derived from that Set.

## Decision

Introduce `backend/app/ai/` module implementing:

### Provider Registry (DB-backed)

All providers stored in `ai_providers` table with:
- Named configurations (admin creates "Production GPT-4o", "Local Llama 3" etc.)
- Provider type enum: `openai | anthropic | ollama | lmstudio | openrouter | custom`
- API key stored as **env var name only** (e.g. `OPENAI_API_KEY`) — resolved via `os.environ.get()` at call time, never stored as a value
- Per-provider model, base URL, parameters (JSON: temperature, max_tokens etc.), system prompt, timeout, retry count
- One default provider flag

### Client Abstraction

`AIClient` abstract base class with:
- `chat(messages) -> str` — blocking chat completion
- `chat_stream(messages) -> AsyncIterator[str]` — streaming via SSE
- `test_connection() -> ProviderTestResult` — health check

Two concrete implementations:
- `OpenAICompatibleClient` — covers openai, lmstudio, ollama, openrouter, custom (all expose `/v1/chat/completions`)
- `AnthropicClient` — Anthropic Messages API (`/v1/messages`; system as top-level param; `content_block_delta` stream format)

Factory function `create_ai_client(provider_row) -> AIClient` selects implementation by `provider_type`.

Uses `httpx.AsyncClient` for all HTTP — no vendor SDKs. Keeps the abstraction clean and avoids SDK version conflicts.

### Retry Logic (translated from machine-dream's `isRetryableError`)

Retry on: socket errors, network errors, HTTP 429, HTTP 5xx.
Do **not** retry on: timeouts (fast-fail), HTTP 4xx auth errors.
Exponential backoff: 1s, 2s, 4s (configurable retries, default 3).

### Service Layer

CRUD for providers (admin-only), Q&A orchestration, usage logging, conversation storage.

### Set Context Retrieval

`build_set_context(db, set_id)` queries elements, relationships, and diagrams in the Set, formats
as structured text for the LLM system prompt, truncated to a token budget (~4 chars/token heuristic).

### Admin-Only Provider Management

All provider CRUD endpoints require admin role via existing `_require_admin()` pattern.
Users can only call the Q&A endpoint for sets they have access to.

### Audit Trail

All AI calls logged to `ai_usage_log` table + `iris_audit.db` via `write_audit_entry()`.

## Options Considered

| Option | Verdict |
|---|---|
| Vendor SDKs (openai, anthropic Python packages) | Rejected — SDK version conflicts, heavier deps, breaks abstraction |
| httpx + thin abstraction (chosen) | Clean, uniform, no vendor lock-in |
| Single OpenAI-compat client for all | Rejected — Anthropic API is structurally different (system param, stream format) |
| File-based provider config (like machine-dream) | Rejected — DB-backed needed for admin CRUD UI |
| Per-user provider configs | Rejected — Iris is multi-user; system-wide admin config is appropriate |

## Consequences

- `httpx>=0.27` already in pyproject.toml — no new dependency needed
- API keys never stored in DB — admins must set env vars on the server
- Admin UI in `/admin/ai` for provider management
- Set-scoped Q&A becomes available to all authenticated users once a provider is configured
- Usage log enables cost visibility and audit
- Streaming responses via SSE require frontend `EventSource` handling
