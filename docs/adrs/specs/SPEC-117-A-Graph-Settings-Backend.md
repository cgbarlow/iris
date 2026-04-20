# SPEC-117-A: Graph Settings Backend

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-117-A |
| **ADR** | [ADR-117](../ADR-117-Graph-Settings-Admin-Defaults.md) |
| **Status** | Approved |
| **Date** | 2026-04-03 |

## Overview

A `graph_settings` database table storing admin-configurable graph physics and display defaults, scoped by global, collection, or set. A service layer provides cascaded reads and upserts, exposed via two REST endpoints guarded by admin role.

## Backend

### Database: `graph_settings` table

**Migration:** `backend/app/migrations/supabase/m039_graph_settings.sql`

```sql
CREATE TABLE IF NOT EXISTS graph_settings (
    scope_type  TEXT        NOT NULL CHECK (scope_type IN ('global', 'collection', 'set')),
    scope_id    TEXT,
    settings    JSONB       NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  TEXT,
    PRIMARY KEY (scope_type, scope_id)
);
```

**Key design:**
- `scope_type` is one of `'global'`, `'collection'`, or `'set'`.
- `scope_id` is `NULL` for the global scope, otherwise the UUID of the collection or set.
- The composite primary key `(scope_type, scope_id)` ensures one row per scope.
- `settings` is a JSONB column containing a flat object with the four physics fields and the node/edge visibility maps.
- `updated_by` stores the user ID of the admin who last saved.

### Settings JSON shape

The `settings` JSONB column stores this structure:

| Key | Type | Default | Range | Description |
|-----|------|---------|-------|-------------|
| `label_density` | `integer` | `10` | 1 -- 50 | Maximum labels drawn per node-type tier in `onRenderFramePost`. Maps to the `MAX_PER_TIER` constant. |
| `node_spacing` | `number` | `1.0` | 0.2 -- 3.0 | Multiplier applied to all `d3Force('charge').strength()` values. Higher values push nodes further apart. |
| `size_contrast` | `number` | `1.0` | 0.0 -- 1.0 | Interpolation factor between uniform node size and the full type-based size scale. `0.0` = all nodes equal size, `1.0` = full differentiation. |
| `link_length` | `number` | `1.0` | 0.2 -- 3.0 | Multiplier applied to all `d3Force('link').distance()` values. Higher values stretch links. |
| `nodes` | `Record<string, boolean>` | all `true` | -- | Per-node-type visibility. Keys match `NODE_TYPE_LABELS` (e.g. `collection`, `set`, `package`, `diagram`, `element`). |
| `edges` | `Record<string, boolean>` | all `true` | -- | Per-edge-type visibility. Keys match edge group items (e.g. `hierarchy`, `element_relationship`, `diagram_element`). |

### Default values

Seeded into the global scope row during startup if no global row exists:

```python
GRAPH_SETTINGS_DEFAULTS = {
    "label_density": 10,
    "node_spacing": 1.0,
    "size_contrast": 1.0,
    "link_length": 1.0,
    "nodes": {
        "collection": True,
        "set": True,
        "package": True,
        "diagram": True,
        "element": True,
    },
    "edges": {
        "collection_membership": True,
        "set_membership": True,
        "direct_diagram_links": True,
        "hierarchy": True,
        "package_relationship": True,
        "diagram_element": True,
        "diagram_package": True,
        "diagram_link": True,
        "element_relationship": True,
    },
}
```

### Module: `backend/app/graph_settings/`

**Service** (`service.py`):

| Function | Signature | Description |
|----------|-----------|-------------|
| `seed_defaults` | `async (db) -> None` | Inserts the global defaults row if it does not yet exist. Called from `startup.py`. |
| `get_cascaded` | `async (db, scope_type, scope_id) -> dict` | Returns the merged settings for a given scope. Merge order: hard-coded defaults, then global DB row, then collection DB row (if scope is set), then the target scope DB row. Each layer overrides only the keys it defines. |
| `upsert` | `async (db, scope_type, scope_id, settings, user_id) -> dict` | Upserts the settings row for the given scope, sets `updated_at` and `updated_by`. Returns the saved row. |

**Cascade logic in `get_cascaded`:**

```
result = copy(GRAPH_SETTINGS_DEFAULTS)
result.update(global_db_row.settings)          # if exists
if scope_type == 'set':
    collection_id = lookup set's collection
    result.update(collection_db_row.settings)  # if exists
result.update(scope_db_row.settings)           # if exists
return result
```

For nested keys (`nodes`, `edges`), the merge is shallow per-key within the dict — individual visibility toggles override, not the entire map.

**Models** (`models.py`):

| Model | Fields |
|-------|--------|
| `GraphSettingsResponse` | `scope_type`, `scope_id`, `settings: dict`, `updated_at`, `updated_by` |
| `GraphSettingsUpdate` | `settings: dict` |

### Router (`router.py`)

| Method | Path | Auth | Admin | Description |
|--------|------|------|-------|-------------|
| GET | `/api/graph/settings` | Required | No | Returns cascaded settings for the requested scope |
| PUT | `/api/graph/settings` | Required | Yes | Upserts admin defaults for the requested scope |

**Query parameters** (both endpoints):

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `scope_type` | `string` | Yes | One of `global`, `collection`, `set` |
| `scope_id` | `string` | No | UUID of collection or set. Required when scope_type is not `global`. |

**Admin guard:** The PUT endpoint reuses the existing `_require_admin` pattern from `backend/app/settings/router.py` — checks `current_user["role"] != "admin"` and raises HTTP 403.

**GET response:** Always returns a fully-merged settings object (never partial), so the frontend does not need to implement its own cascade for the DB layer.

### Router registration

Add `from app.graph_settings.router import router as graph_settings_router` and `app.include_router(graph_settings_router)` in `backend/app/main.py`.

### Startup

Call `await seed_defaults(db)` from `backend/app/startup.py` alongside existing seed functions.

## Tests

**File:** `backend/tests/test_graph_settings/test_api.py`

| Test | Assertion |
|------|-----------|
| `test_get_defaults_returns_all_keys` | GET with `scope_type=global` returns all six keys with default values |
| `test_get_requires_auth` | 401 without token |
| `test_put_requires_admin` | 403 for non-admin user |
| `test_put_upserts_global` | PUT with `scope_type=global` stores and returns updated settings |
| `test_put_upserts_set` | PUT with `scope_type=set&scope_id=<uuid>` stores set-level overrides |
| `test_cascade_global_then_set` | After setting global `node_spacing=2.0` and set `link_length=1.5`, GET for that set returns both overrides merged |
| `test_cascade_collection_in_between` | Global + collection + set layers merge in correct order |
| `test_partial_update_preserves_other_keys` | PUT with only `{label_density: 20}` does not erase other keys |
| `test_nodes_edges_merge_per_key` | Overriding `nodes.diagram=false` at set level does not reset other node visibility flags |
