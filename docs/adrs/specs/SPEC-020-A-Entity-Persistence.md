# SPEC-020-A: Entity Persistence

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-020-A |
| **ADR Reference** | [ADR-020: Entity Persistence from Model Editor](../ADR-020-Entity-Persistence-from-Model-Editor.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines how entities created within the model editor are persisted as first-class backend entities before being added to the canvas, ensuring they appear in the global entities list and have stable IDs for cross-referencing.

---

## Current Behaviour (Before)

1. User clicks "Add Entity" in model edit mode
2. `handleAddEntity()` creates a local `CanvasNode` with `crypto.randomUUID()` as the node ID
3. The node's `data` object contains `label`, `entityType`, and `description` but **no `entityId`**
4. The entity exists only as canvas data within the model's `data` JSON
5. The entity does **not** appear in `GET /api/entities` or the entities list page

---

## New Behaviour (After)

1. User clicks "Add Entity" in model edit mode
2. `handleAddEntity()` calls `POST /api/entities` with the entity details
3. On success, a `CanvasNode` is created with the API-returned entity ID stored in `data.entityId`
4. The entity immediately appears in `GET /api/entities` and the entities list page
5. On failure, an error message is displayed and no node is added to the canvas

---

## Implementation Detail

### Modified Function: `handleAddEntity`

**File:** `frontend/src/routes/models/[id]/+page.svelte`

| Aspect | Before | After |
|--------|--------|-------|
| Signature | `function handleAddEntity(...)` | `async function handleAddEntity(...)` |
| API call | None | `POST /api/entities` with `{ entity_type, name, description, data: {} }` |
| Node data | `{ label, entityType, description }` | `{ label, entityType, description, entityId: created.id }` |
| Error handling | None | Catches `ApiError` for message, generic fallback for other errors |
| Canvas update | Always adds node | Only adds node on API success |

### API Request

```
POST /api/entities
Content-Type: application/json

{
    "entity_type": "<entityType>",
    "name": "<name>",
    "description": "<description>",
    "data": {}
}
```

### API Response (used)

```json
{
    "id": "<uuid>",
    "entity_type": "<entityType>",
    "name": "<name>",
    ...
}
```

The `id` field from the response is stored as `data.entityId` on the canvas node.

### Error Handling

| Error Type | Behaviour |
|------------|-----------|
| `ApiError` | Display `e.message` in the page error alert |
| Other error | Display `"Failed to create entity"` in the page error alert |
| Any error | Node is **not** added to the canvas; dialog remains closed |

---

## Imports

No new imports are required. `Entity`, `ApiError`, and `apiFetch` are already imported in the target file.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| 1 | Adding an entity in the model editor creates a record in `GET /api/entities` |
| 2 | The canvas node's `data.entityId` matches the created entity's ID |
| 3 | The entity appears in the global entities list page |
| 4 | If the API call fails, an error message is shown and no node is added |
| 5 | The `handleLinkEntity` function (linking existing entities) is unaffected |

---

## Affected Components

| Component | Change |
|-----------|--------|
| `+page.svelte` (model detail) | `handleAddEntity` becomes async, calls API before adding node |
| Backend `/api/entities` | No change required (existing POST endpoint) |

---

*This specification implements [ADR-020](../ADR-020-Entity-Persistence-from-Model-Editor.md).*
