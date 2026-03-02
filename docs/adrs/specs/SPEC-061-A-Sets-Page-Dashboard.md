# SPEC-061-A: Sets Page & Dashboard Integration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-061-A |
| **ADR** | ADR-061 |
| **Date** | 2026-03-02 |

---

## Database Migration (m013)

Three new columns on `sets` table (idempotent via PRAGMA table_info check):

| Column | Type | Description |
|--------|------|-------------|
| `thumbnail_source` | `TEXT` | `'model'`, `'image'`, or `NULL` |
| `thumbnail_model_id` | `TEXT REFERENCES models(id)` | Model whose thumbnail to use (when source = `'model'`) |
| `thumbnail_image` | `BLOB` | Raw PNG/JPG bytes (when source = `'image'`) |

---

## API Endpoints

### Modified Endpoints

**`DELETE /api/sets/{set_id}`**
- New query parameter: `force: bool = false`
- When `force=false`: existing 204/409 behavior
- When `force=true`: soft-deletes all models, entities, and search indexes in the set, then soft-deletes the set. Returns 200 with `{ models_deleted: int, entities_deleted: int }`
- Default set always returns 403 regardless of force flag

**`PUT /api/sets/{set_id}`**
- New body fields: `thumbnail_source: str | null`, `thumbnail_model_id: str | null`
- Validates that `thumbnail_model_id` belongs to the set when source is `'model'`

**`GET /api/sets` and `GET /api/sets/{set_id}`**
- Response now includes: `thumbnail_source`, `thumbnail_model_id`, `has_thumbnail_image: bool`

### New Endpoints

**`POST /api/sets/{set_id}/thumbnail`**
- Accepts `UploadFile` (multipart form data)
- Validates: PNG or JPEG content type, max 2 MB
- Stores image BLOB, sets `thumbnail_source = 'image'`
- Returns updated `SetResponse`

**`GET /api/sets/{set_id}/thumbnail`**
- Returns raw image bytes with appropriate `Content-Type`
- Cache-Control: `public, max-age=300`
- If source is `'model'`: fetches from `model_thumbnails` (dark theme)
- If source is `'image'`: returns stored BLOB
- Returns 404 if no thumbnail configured

---

## Pydantic Models

```python
class SetUpdate(BaseModel):
    name: str
    description: str | None = None
    thumbnail_source: str | None = None
    thumbnail_model_id: str | None = None

class SetResponse(BaseModel):
    # ... existing fields ...
    thumbnail_source: str | None = None
    thumbnail_model_id: str | None = None
    has_thumbnail_image: bool = False

class SetForceDeleteResponse(BaseModel):
    models_deleted: int
    entities_deleted: int
```

---

## Frontend Components

### Sets Page (`/sets`)
- List and gallery view modes (persisted to localStorage)
- Client-side search filter on name and description
- Default click navigates to `/?set_id={id}` (dashboard filter)
- Edit mode click navigates to `/sets/{id}` (edit page)
- "Edit Sets" toggle button, "New Set" button
- Gallery view shows thumbnail or placeholder

### Set Edit Page (`/sets/[id]`)
- Edit form: name, description
- Thumbnail: radio group (none / model thumbnail / upload image)
- Model selection dropdown when source is 'model'
- File upload (PNG/JPG, max 2 MB) when source is 'image'
- Danger zone: force-delete with confirmation dialog showing counts

### SetDialog Component
- Modal dialog for creating new sets
- Name (required) and description (optional) fields
- DOMPurify sanitization on inputs

### Dashboard (`/`)
- Reads `set_id` from URL search params
- 3-column stats grid: Entities, Models, Sets
- When set filter active: shows set name, "(filtered)" labels, reset link
- Entity/Model card hrefs include `?set_id=` when filtered

### Sidebar (AppShell)
- Sets nav item added between Entities and Import
- `aria-current` uses `startsWith` for non-root paths

---

## TypeScript Types

```typescript
export interface IrisSet {
    // ... existing fields ...
    thumbnail_source: 'model' | 'image' | null;
    thumbnail_model_id: string | null;
    has_thumbnail_image: boolean;
}
```
