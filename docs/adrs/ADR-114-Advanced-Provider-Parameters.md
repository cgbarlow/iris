# ADR-114: Advanced Provider Parameters & Model Selector

- **Status:** Accepted
- **Date:** 2026-03-30
- **Relates to:** ADR-093 (AI Model Management Foundations)

## Context

The AI provider edit screen (ADR-093) currently exposes only `temperature` and `max_tokens` as tunable generation parameters, despite the backend `ModelParameters` already supporting `top_p`. Power users — especially those running local models via Ollama or LM Studio — need access to additional sampling parameters: Top-K, Min-P, frequency/presence penalties, and stop sequences. These parameters are standard across machine-dream's profile system and major LLM APIs.

Additionally, when multiple providers are configured, the Ask AI chat always uses the default provider with no way to switch at query time.

## Decision

### Part A: Advanced Settings Toggle

Add a collapsible "Advanced Settings" section to the provider edit modal, exposing six optional generation parameters:

| Parameter | Type | Range | Provider Support |
|-----------|------|-------|------------------|
| `top_p` | float | 0.0–1.0 | All |
| `top_k` | int | ≥ 1 | Anthropic, Ollama, some OpenRouter |
| `min_p` | float | 0.0–1.0 | Ollama/llama.cpp |
| `frequency_penalty` | float | -2.0–2.0 | OpenAI, Ollama, LMStudio, OpenRouter |
| `presence_penalty` | float | -2.0–2.0 | OpenAI, Ollama, LMStudio, OpenRouter |
| `stop` | string[] | — | All (Anthropic maps to `stop_sequences`) |

All parameters are optional (default null = provider-native defaults). The toggle defaults to collapsed and auto-expands when editing a provider with existing advanced parameters. No database migration is needed — the `parameters` JSON column already accepts arbitrary keys.

### Part B: Model Selector

Add a compact `<select>` dropdown (styled like `ThemeSelector.svelte`) to the Ask AI chat toolbar, placed left of the History button. A new lightweight public endpoint `GET /api/ai/providers/active` returns `[{id, name, model, provider_type}]` for active providers without exposing sensitive configuration. The backend `MultiSetQARequest` already accepts `provider_id` — only the frontend needs wiring.

## Consequences

- Admins gain full control over LLM generation behaviour without cluttering the default form
- Not all providers support all parameters; the backend silently omits unsupported ones per client type
- The UI does not indicate per-provider parameter compatibility (future enhancement)
- Both `admin/ai/+page.svelte` and `admin/settings/ai/+page.svelte` are near-identical duplicates that must receive the same changes (tech debt noted)
