# SPEC-114-B: Model Selector in Ask AI Chat

**ADR:** ADR-114
**Component:** Backend router, frontend SetQA

## Backend: Public Active Providers Endpoint

New endpoint in `backend/app/ai/router.py`:

```
GET /api/ai/providers/active
```

- Auth: `_require_user()` (any authenticated user, not admin-only)
- Returns: `[{id, name, model, provider_type}]` for all active providers
- No sensitive data (no API keys, parameters, system prompts)
- Response model: `ActiveProviderResponse`

### New Pydantic Model

```python
class ActiveProviderResponse(BaseModel):
    id: str
    name: str
    model: str
    provider_type: str
```

## Frontend: SetQA.svelte

### State

```typescript
let activeProviders = $state<{id: string; name: string; model: string; provider_type: string}[]>([]);
let selectedProviderId = $state<string | null>(null);
```

### Data Loading

On mount, fetch `GET /api/ai/providers/active` to populate the provider list.

### UI

Insert `<select>` in the right toolbar group, before the History button:

```svelte
{#if activeProviders.length > 1}
  <select
    class="rounded border px-2 py-1 text-xs"
    style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
    bind:value={selectedProviderId}
  >
    <option value={null}>Default</option>
    {#each activeProviders as p}
      <option value={p.id}>{p.name} ({p.model})</option>
    {/each}
  </select>
{/if}
```

Only shown when more than one active provider exists.

### Request Wiring

In `askQuestion()`, add `provider_id: selectedProviderId` to the request body when non-null. The backend `MultiSetQARequest` already accepts this field.
