# SPEC-032-A: PNG Thumbnail Fix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-032-A |
| **ADR Reference** | [ADR-032: PNG Thumbnail Startup Regeneration and Frontend Fallback](../ADR-032-PNG-Thumbnail-Startup-Regeneration.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification defines the changes needed to fix PNG gallery mode, which currently shows no images due to three root causes: `cairosvg` not being installed, pre-existing models having no thumbnail entries, and the frontend having no error fallback for broken images.

---

## Backend: Dependency Addition

### pyproject.toml

Add `cairosvg` as a required dependency:

```toml
dependencies = [
    ...
    "cairosvg>=2.8.2",
]
```

This was done by `uv add cairosvg` which also updates `uv.lock`.

---

## Backend: Startup Thumbnail Regeneration

### New Function in `thumbnail.py`

```python
async def regenerate_all_thumbnails(db: aiosqlite.Connection) -> None:
```

**Behaviour:**
1. Query all non-deleted models: `SELECT m.id, m.model_type, mv.data FROM models m JOIN model_versions mv ON m.id = mv.model_id AND m.current_version = mv.version WHERE m.is_deleted = 0`
2. For each model, call `generate_and_store_thumbnail(db, model_id, data, model_type)`
3. Log count of regenerated thumbnails (via print for simplicity, matching existing patterns)

### Startup Integration in `startup.py`

After migrations and search index rebuild, before seeding:

```python
from app.models_crud.thumbnail import regenerate_all_thumbnails

# After rebuild_search_index:
await regenerate_all_thumbnails(db_manager.main_db)
```

This ensures all models have up-to-date PNG thumbnails on every startup.

---

## Frontend: Image Error Fallback

### `+page.svelte` Changes

Replace the static `<img>` tag in PNG mode with a pattern that falls back to the `<ModelThumbnail>` SVG component when the image fails to load:

```svelte
{#if thumbnailMode === 'png'}
    {#if thumbnailErrors.has(model.id)}
        <ModelThumbnail data={model.data} modelType={model.model_type} />
    {:else}
        <img
            src="/api/models/{model.id}/thumbnail"
            alt="Thumbnail for {model.name}"
            class="h-full w-full object-cover"
            loading="lazy"
            onerror={() => { thumbnailErrors = new Set([...thumbnailErrors, model.id]); }}
        />
    {/if}
{:else}
    <ModelThumbnail data={model.data} modelType={model.model_type} />
{/if}
```

A `Set<string>` tracks which model IDs have had thumbnail load failures, triggering a re-render to show the SVG fallback.

---

## Test Plan

### Backend Tests

| # | Test | File |
|---|------|------|
| 1 | Thumbnail endpoint returns valid PNG bytes after model creation | `tests/test_models/test_thumbnails.py` |
| 2 | Thumbnail has PNG magic bytes (not SVG) | `tests/test_models/test_thumbnails.py` |
| 3 | `regenerate_all_thumbnails` creates entries for models without thumbnails | `tests/test_models/test_thumbnails.py` |
| 4 | `regenerate_all_thumbnails` updates stale SVG-byte thumbnails to PNG | `tests/test_models/test_thumbnails.py` |
| 5 | Startup regeneration produces thumbnails for pre-existing models | `tests/test_models/test_thumbnails.py` |

---

## File Inventory

| File | Change |
|------|--------|
| `backend/pyproject.toml` | Add `cairosvg>=2.8.2` to dependencies |
| `backend/app/models_crud/thumbnail.py` | Add `regenerate_all_thumbnails()` function |
| `backend/app/startup.py` | Call `regenerate_all_thumbnails()` after migrations |
| `frontend/src/routes/models/+page.svelte` | Add `onerror` fallback on `<img>` tags |
| `backend/tests/test_models/test_thumbnails.py` | New test file for thumbnail generation |

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| 1 | `cairosvg` is a required dependency in `pyproject.toml` |
| 2 | `GET /api/models/{id}/thumbnail` returns `image/png` content type with valid PNG bytes |
| 3 | Models created before thumbnail migration get thumbnails on startup |
| 4 | Frontend PNG mode falls back to SVG component when thumbnail fails to load |
| 5 | All backend tests pass |

---

*This specification implements [ADR-032](../ADR-032-PNG-Thumbnail-Startup-Regeneration.md).*
