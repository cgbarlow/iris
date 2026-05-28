# SPEC-218-a: Canvas shape normalization

Implements: [ADR-218](../ADR-218-Canvas-Shape-Normalization.md).

## 1. Problem

The shared creation prompt teaches the **flat** AI node shape:

```json
{ "id": "st1", "type": "stakeholder", "label": "Users",
  "position": {"x": 60, "y": 20},
  "size": {"width": 180, "height": 80}, "visual": {} }
```

`apply_diagram_creation` converts it (via `_build_canvas_nodes`) to the
**canvas** shape the frontend needs:

```json
{ "id": "st1", "type": "stakeholder",
  "position": {"x": 60, "y": 20}, "width": 180, "height": 80,
  "data": {"label": "Users", "entityType": "stakeholder"} }
```

`create_diagram` (ADR-162) persisted `data` verbatim, so flat nodes
reached storage with no `data` object and `UnifiedCanvas.svelte`
`fitViewOptions` crashed on `n.data.entityType` (issue #238).

## 2. Normalizer — `backend/app/diagrams/canvas_normalize.py`

### `flat_node_to_canvas(node, *, default_entity_type="") -> dict`

- `data.label` ← `node["label"]` (default `""`).
- `data.entityType` ← `node["type"]` or `default_entity_type`.
- top-level `type` ← same resolved entity type (renderer dispatch).
- `width`/`height` ← `node["size"].{width,height}` (defaults 200 / 86)
  when not already top-level.
- `data.description` ← `node["description"]` only when truthy.
- `data.visual` ← `node["visual"]` only when truthy (empty `{}` dropped).
- `position` defaults to `{"x":0,"y":0}` when absent.
- Unknown top-level keys (e.g. `parentId`) are preserved; relocated
  keys (`label`, `size`, `visual`, `description`) are removed from the
  top level.

### `flat_edge_to_canvas(edge, *, default_relationship_type="") -> dict`

- `data.relationshipType` ← `edge["type"]` or `default_relationship_type`.
- top-level `type` ← same resolved value.
- `data.visual` ← `edge["visual"]` only when truthy.
- `sourceHandle` / `targetHandle` default to `"center"`.

### `needs_normalization(data) -> bool`

True iff `data` is a dict with a `nodes` or `edges` list containing at
least one dict item lacking a dict `data` key.

### `normalize_canvas_data(data) -> data`

- Non-dict input → returned unchanged.
- dict without `nodes`/`edges` lists (markdown `{content}`, sequence
  `{participants, ...}`) → returned unchanged.
- Otherwise returns a shallow copy with each node/edge passed through
  the per-item helper **only when it is flat** (no dict `data`);
  already-canvas items pass through identically.
- **Idempotent**: `normalize(normalize(x)) == normalize(x)`.
- **Non-mutating**: the input object is not modified in place.

## 3. Wiring

| Boundary | Location | Behaviour |
|---|---|---|
| Write | `service.create_diagram` | `data = normalize_canvas_data(data)` before serialize / detect / thumbnail |
| Write | `service.update_diagram` | same, before serialize |
| Read | `service.get_diagram` | `result["data"] = normalize_canvas_data(result["data"])` before `_maybe_synthesise_content` (non-destructive auto-heal) |
| DRY | `ai/creation.py::_build_canvas_nodes` / `_build_canvas_edges` | delegate per-item conversion to the shared helpers; keep doview defaults + `_linkedDiagramIndex` stash |
| Frontend | `UnifiedCanvas.svelte` `fitViewOptions` | `n.data?.entityType !== 'diagram_frame'` (defense-in-depth) |

## 4. Repair script — `scripts/repair_flat_diagram_shape.py`

- `repair_diagram(db, diagram_id, *, dry_run=False)` normalises **every
  version** of one diagram in place (no version bump, no commit — caller
  commits once). Returns `{found, diagram_type, current_version,
  total_versions, versions_changed, current_data}`.
- `regenerate_thumbnails(db, diagram_id, diagram_type, data)` rebuilds
  all-theme thumbnails from the normalized current-version data.
- `main()` requires ≥1 `--diagram-id`; errors out otherwise. Never scans
  all diagrams. Supports `--dry-run` and `--skip-thumbnails`. Connects
  via `app.config.get_config` + `DatabaseManager` so it runs against both
  SQLite and Supabase.
- **Issue #238 scope (the only diagrams to repair):**
  - `13024153-b328-41a4-bd37-0cbc6d2fbedc`
  - `330fe369-0b03-457c-8692-62e67f9fcdb0`
  - `6b9917d7-f7c9-4dfc-a769-49fa571f28e5`

## 5. Acceptance criteria

1. Posting flat `{nodes, edges}` to `POST /api/diagrams` round-trips as
   canvas shape on `GET` — every node has `data.entityType`. ✓
   (`test_shape_normalization.py`)
2. A diagram whose stored data is flat is auto-healed on `GET` without
   mutating storage. ✓
3. `PUT /api/diagrams/{id}` with flat `data` persists canvas shape. ✓
4. `normalize_canvas_data` is idempotent and leaves markdown/sequence
   and already-canvas payloads untouched. ✓ (`test_canvas_normalize.py`)
5. The apply path (`create_diagrams_from_ai`) still materialises
   elements/relationships and emits `data.entityId` /
   `data.relationshipType`. ✓ (`test_creation.py` unchanged & green)
6. `repair_diagram` normalises all versions in place, is idempotent,
   honours `--dry-run`, and reports (never guesses) an unknown id. ✓
   (`test_repair_flat_diagram_shape.py`)
7. Surface parity (§14) stays clean — no new write endpoint. ✓
