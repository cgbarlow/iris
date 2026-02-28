# SPEC-018-A: Model Creation Navigation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-018-A |
| **ADR Reference** | [ADR-018: Model Creation Navigation](../ADR-018-Model-Creation-Navigation.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the behaviour change for model creation: after a user successfully creates a model via the "New Model" dialog on the models list page, the application navigates to the new model's detail page instead of refreshing the models list.

---

## Current Behaviour

1. User clicks "New Model" on `/models`
2. User fills in name, type, and description in the `ModelDialog`
3. User clicks "Create"
4. `handleCreate()` calls `POST /api/models` via `apiFetch<Model>()`
5. On success, `showCreateDialog` is set to `false` and `loadModels()` is called
6. User remains on `/models` and must manually click the new model to navigate to it

---

## New Behaviour

1. User clicks "New Model" on `/models`
2. User fills in name, type, and description in the `ModelDialog`
3. User clicks "Create"
4. `handleCreate()` calls `POST /api/models` via `apiFetch<Model>()`
5. On success, `showCreateDialog` is set to `false`
6. `goto(`/models/${created.id}`)` navigates to the new model's detail page
7. User lands on `/models/{id}` and sees the model detail page with the model name as the heading

---

## Implementation

### File: `frontend/src/routes/models/+page.svelte`

**Import addition:**
```typescript
import { goto } from '$app/navigation';
```

**Function change in `handleCreate`:**

Replace:
```typescript
showCreateDialog = false;
await loadModels();
```

With:
```typescript
showCreateDialog = false;
await goto(`/models/${created.id}`);
```

The `created` variable captures the return value of `apiFetch<Model>()`, which includes the `id` field from the API response.

---

## API Contract

The `POST /api/models` endpoint returns the created model object including its `id` field. The `Model` type is defined in `$lib/types/api.ts`:

```typescript
interface Model {
    id: string;
    model_type: string;
    name: string;
    description: string | null;
    data: Record<string, unknown>;
    // ... other fields
}
```

No API changes are required.

---

## Error Handling

Error handling remains unchanged. If the `POST /api/models` call fails:
- `ApiError` instances display the server error message
- Other errors display "Failed to create model"
- The user stays on the models list page with the error visible
- Navigation only occurs on success

---

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | After creating a model, the user is navigated to the model detail page | BDD scenario: user creates model and lands on detail page |
| 2 | The model detail page displays the created model's name | BDD assertion: heading matches model name |
| 3 | The URL matches `/models/{id}` after creation | BDD assertion: URL pattern check |
| 4 | On creation error, the user stays on the models list | Manual verification: error handling unchanged |

---

*This specification implements [ADR-018](../ADR-018-Model-Creation-Navigation.md).*
