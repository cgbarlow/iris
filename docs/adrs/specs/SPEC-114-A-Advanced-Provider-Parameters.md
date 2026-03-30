# SPEC-114-A: Advanced Provider Parameters

**ADR:** ADR-114
**Component:** Backend models, client, frontend admin

## Backend: ModelParameters Extension

In `backend/app/ai/models.py`, extend `ModelParameters`:

```python
class ModelParameters(BaseModel):
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=200000)
    top_p: float | None = Field(None, ge=0.0, le=1.0)       # existing
    top_k: int | None = Field(None, ge=1)
    min_p: float | None = Field(None, ge=0.0, le=1.0)
    frequency_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    stop: list[str] | None = None
```

No database migration — `parameters` column stores JSON text.

## Backend: Client Payload Construction

### OpenAICompatibleClient._payload()

Pass all new params when non-null, following existing if-not-None pattern:
- `top_k`, `min_p`, `frequency_penalty`, `presence_penalty`, `stop`

### AnthropicClient._payload()

- Pass `top_k` (natively supported)
- Map `stop` → `stop_sequences` (Anthropic's key name)
- Silently omit `frequency_penalty`, `presence_penalty`, `min_p` (unsupported)

## Frontend: Provider Edit Modal

### Form State

Add to `form` object:
- `top_p: ''`, `top_k: ''`, `min_p: ''`, `frequency_penalty: ''`, `presence_penalty: ''`, `stop: ''`

Add toggle: `showAdvanced = $state(false)`

### UI Layout

Insert between Performance Parameters and System Prompt:

```
[▶ Advanced Settings (optional)]

  When expanded:
  ┌─────────────────────────────────────────────────┐
  │  Top P (0–1)    │  Top K (≥1)    │  Min P (0–1)  │
  │  Freq. penalty  │  Pres. penalty │               │
  │  Stop sequences (comma-separated)               │
  └─────────────────────────────────────────────────┘
```

- Toggle button: `aria-expanded`, ▶/▼ chevron
- Section: `{#if showAdvanced}` with `pl-4 border-l-2` indent
- Auto-expand when editing provider with existing advanced params

### Save Logic

Extend `parameters` object construction:
- Parse numeric fields with `Number()`
- Parse `stop` as comma-separated string → `string[]`
- Type: `Record<string, number | string[]>`

## Tests

### Backend model tests (test_models.py)
- Valid/invalid ranges for each new field
- Round-trip via `model_dump(exclude_none=True)`

### Backend client tests (test_client.py)
- OpenAI payload includes all advanced params when set
- OpenAI payload omits null advanced params
- Anthropic payload includes `top_k`, maps `stop` → `stop_sequences`
- Anthropic payload omits unsupported params
