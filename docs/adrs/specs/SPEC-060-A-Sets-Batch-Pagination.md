# SPEC-060-A: Sets, Batch Operations & Pagination

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-060-A |
| **ADR** | ADR-060 |
| **Date** | 2026-03-02 |
| **Status** | Implemented |

---

## Database Schema

### Sets Table

```sql
CREATE TABLE sets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_deleted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_sets_name ON sets(name);
```

### Column Additions

```sql
ALTER TABLE models ADD COLUMN set_id TEXT REFERENCES sets(id);
CREATE INDEX idx_models_set ON models(set_id);

ALTER TABLE entities ADD COLUMN set_id TEXT REFERENCES sets(id);
CREATE INDEX idx_entities_set ON entities(set_id);
```

### Default Set

- Well-known UUID: `00000000-0000-0000-0000-000000000001`
- All existing models/entities backfilled to Default set on migration

---

## API Endpoints

### Sets CRUD

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/api/sets` | 201 | Create set (name, description) |
| GET | `/api/sets` | 200 | List all sets with model_count, entity_count |
| GET | `/api/sets/{id}` | 200 | Get single set |
| PUT | `/api/sets/{id}` | 200 | Update name/description |
| DELETE | `/api/sets/{id}` | 204 | 409 if non-empty; 403 if Default |
| GET | `/api/sets/{id}/tags` | 200 | Unique tags within this set |

### Batch Operations

All accept `{ ids: string[] }` (max 100). All return `{ succeeded, failed, errors }`.

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/api/batch/models/delete` | `{ ids }` | Soft-delete |
| POST | `/api/batch/models/clone` | `{ ids }` | Shallow copy, name + " (Copy)" |
| POST | `/api/batch/models/set` | `{ ids, set_id }` | Reassign set |
| POST | `/api/batch/models/tags` | `{ ids, add_tags, remove_tags }` | Add/remove tags |
| POST | `/api/batch/entities/delete` | `{ ids }` | Soft-delete |
| POST | `/api/batch/entities/clone` | `{ ids }` | Shallow copy |
| POST | `/api/batch/entities/set` | `{ ids, set_id }` | Reassign set |
| POST | `/api/batch/entities/tags` | `{ ids, add_tags, remove_tags }` | Add/remove tags |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `GET /api/models` | Added `set_id` query parameter |
| `POST /api/models` | Added `set_id` in request body |
| `GET /api/entities` | Added `set_id` query parameter |
| `POST /api/entities` | Added `set_id` in request body |
| `GET /api/entities/tags/all` | Added `set_id` query parameter for scoped tags |
| `POST /api/import/sparx` | Added `set_id` form field |

### Response Extensions

Model and Entity responses now include:
- `set_id: string` — the set this item belongs to
- `set_name: string` — the human-readable set name (from JOIN)

---

## Frontend Components

### New Components

| Component | Purpose |
|-----------|---------|
| `Pagination.svelte` | Page size selector (25/50/100), prev/next, page number links |
| `SetSelector.svelte` | Dropdown loading sets from `/api/sets` with "All sets" option |
| `BatchToolbar.svelte` | Sticky bottom bar with Clone, Move to Set, Tags, Delete, Cancel |
| `BatchSetDialog.svelte` | Dialog with set dropdown for batch move |
| `BatchTagDialog.svelte` | Dialog for adding/removing tags in batch |

### Page Changes

**Models page** (`/models`):
- Set selector in filter bar
- Pagination controls below list
- Select mode toggle with checkboxes on each item
- Batch toolbar when items selected

**Entities page** (`/entities`):
- Same pattern as models page

**Import page** (`/import`):
- Set selector between file drop zone and Import button
- `set_id` sent as form field in upload

**Model detail** (`/models/[id]`):
- Set name displayed in overview tab

---

## Auto-Membership

When `update_model()` saves canvas data, it iterates node entity IDs and runs:
```sql
UPDATE entities SET set_id = ? WHERE id = ? AND set_id != ?
```
This ensures entities placed on a model's canvas are moved to the model's set.

---

## TypeScript Types

```typescript
interface IrisSet {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  created_by: string;
  updated_at: string;
  is_deleted: boolean;
  model_count: number;
  entity_count: number;
}

interface BatchResult {
  succeeded: number;
  failed: number;
  errors: string[];
}
```
