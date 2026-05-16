# SPEC-187-A: Synthesised content on read

ADR: [ADR-187](../ADR-187-Synthesised-Content-On-Read.md)

## Summary

Defines the per-type compute hook in the diagram read service. Opt-in
diagram types register a compute function; the read path invokes it
and overlays `data.content` (and optionally `data.is_content_locked`)
on the response. Persisted rows do not contain those keys.

## Service hook

`backend/app/diagrams/service.py::get_diagram` adds a small dispatch:

```python
from app.diagrams.dynamic_list import compute_dynamic_list_content

# After base diagram dict is built…
data = diagram.get("data") or {}
if not isinstance(data, dict):
    data = {}

if diagram["diagram_type"] == "dynamic_list":
    src = data.get("dynamic_source") or {}
    rendered = await compute_dynamic_list_content(
        db, diagram["id"],
        mode=src.get("mode") or "diagram_relationships",
        package_id=src.get("package_id"),
        show_description=bool(src.get("show_description", False)),
    )
    data["content"] = rendered
    data["is_content_locked"] = True

diagram["data"] = data
```

The same overlay applies to:

- `list_diagrams` (each row, so search results carry the rendered
  text).
- The export bundle reader path (so md/docx/pdf exports pick up the
  synthesised content via the existing
  `_diagram_to_markdown` special case for `notation == "markdown"`).

## Frontend strip on PUT

Diagram update flows for compute-on-read types must strip the
synthesised keys before sending the PUT body:

```typescript
const data = { ...diagram.data };
delete data.content;
delete data.is_content_locked;
```

The frontend is the only place where this matters — backend ignores
extra keys but they would otherwise round-trip and grow the row.

## Tests

### `backend/tests/test_diagrams/test_dynamic_list_read.py`

- `test_get_diagram_synthesises_content_for_dynamic_list` — the
  response carries `data.content` and `data.is_content_locked`.
- `test_dynamic_list_raw_row_does_not_store_synthesised_keys` —
  direct DB read against `diagrams.data` confirms the keys are
  absent.
- `test_dynamic_list_defaults_when_keys_missing` — diagram with
  `data = {}` or `data.dynamic_source = {}` reads with all three
  defaults applied at compute time.

### `backend/tests/test_export/test_dynamic_list_export.py`

- `test_dynamic_list_export_matches_api_read` —
  `GET /api/export/diagram/{id}?format=md` returns the same text
  as the API read's `data.content`.

## Out of scope

- Caching the rendered string. Compute is cheap (one or two SQL
  queries); cache invalidation across relationship edits would be
  more complex than recomputing.
- Generalising the dispatch into a registry of `(diagram_type,
  compute_fn)` pairs. v1 has a single opt-in (`dynamic_list`); add
  the registry pattern when a second type lands.
- Versioning the synthesised content. The diagram's existing version
  history captures source-config changes; content is derived.

## Verification

- All pytest suites listed above pass.
- The export-equals-read assertion guards against any future
  divergence between the read path and the export path.
