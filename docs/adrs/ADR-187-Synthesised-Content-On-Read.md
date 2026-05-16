# ADR-187: Synthesised `data.content` for compute-on-read diagram types

Status: Accepted (2026-05-16)
Relates to: [ADR-137](ADR-137-Text-Diagram-Class.md), [ADR-179](ADR-179-Renderer-And-Artefact-Store.md)

## Context

ADR-137 / m044 added the `text` diagram type, where the markdown
content lives in `data.content` on the diagram's current version. The
export pipeline (`backend/app/export/router.py::_diagram_to_markdown`,
lines 217–233) special-cases `notation == "markdown"` and returns
`data.content` verbatim — fast, simple, no transformation.

ADR-186 introduces `dynamic_list`, where the markdown is *computed*
from other graph state (intra-diagram relationships or package
membership) rather than stored. We could implement that two ways:

1. Store a snapshot on each save and require explicit refresh.
2. Compute at read time and never store.

Option (1) goes stale silently when the underlying data shifts; (2)
keeps content consistent at zero cost but requires deciding *where*
to compute. Three plausible locations:

- The frontend, before rendering — duplicates logic for export and
  MCP `render_diagram`.
- The export pipeline only — frontend has to re-implement the same
  query path.
- The backend's diagram read service — single source of truth,
  reused by export, MCP, and the UI through one API.

We pick (2) + the third location. The reusable pattern is "synthesise
`data.content` at read-time for diagram types that opt in," and it
deserves its own decision record so future computed types (e.g.
auto-generated tables, computed glossaries) inherit it.

## Decision

**For diagram types that opt in, the diagram-read service layer
populates `data.content` (and optionally `data.is_content_locked`) on
every read.** The persisted `data` JSON does not contain those keys;
they appear only on the response.

### Service hook signature

`backend/app/diagrams/service.py::get_diagram` (and the equivalent
list/bundle paths) inspects `diagram_type` after building the base
response. For each opt-in type, it invokes a per-type compute
function:

```python
if diagram_type == "dynamic_list":
    src = data.get("dynamic_source") or {}
    data["content"] = await compute_dynamic_list_content(
        db, diagram_id,
        mode=src.get("mode") or "diagram_relationships",
        package_id=src.get("package_id"),
        show_description=bool(src.get("show_description", False)),
    )
    data["is_content_locked"] = True
```

Defaults applied at compute time when any key is missing
(backwards-compat with rows created before the field existed).

### `data.is_content_locked`

A synthesised boolean (never stored) hinting to the frontend that the
content textarea should be hidden. Optional — only opt-in types that
also want the read-only canvas UX emit it. ADR-186's `dynamic_list`
emits it; future computed types may or may not.

### Export contract

The export pipeline reads diagrams through the same service path, so
the synthesised `data.content` arrives "for free." The existing
`_diagram_to_markdown` special case
(`notation == "markdown"` → return `data.content`) covers all current
opt-in types. **Export MUST NOT duplicate the compute path** — any
file that imports `compute_dynamic_list_content` (or its peers) must
go through the read service, not call it directly inside an export
handler. This keeps the compute path single-sourced (protocols §13
DRY) and avoids divergence.

### Frontend contract

The frontend reads `data.is_content_locked` and routes to the
appropriate canvas (`<DynamicListCanvas>` for dynamic_list, etc.).
When the flag is absent or false, the existing canvas selection logic
applies. **PUT bodies MUST NOT include synthesised keys.** The
frontend strips `data.content` and `data.is_content_locked` from
write paths for compute-on-read types so the persisted row stays
clean.

## Why not store snapshots with a refresh button

- The refresh UX is a maintenance burden: users have to remember,
  and stale snapshots silently mislead readers.
- Storing means writing on every related change (relationships add,
  package membership update) or accepting staleness — both are worse
  than compute-on-read.
- Snapshots inflate `data` JSON and complicate `diagram_versions`
  semantics.

## Why not compute in the export pipeline only

- MCP `render_diagram` and the frontend would have to re-implement
  the same query path.
- Single-source-of-truth wins: one compute function, one consumer
  (the read service), one rendered string in `data.content`.

## Why not a frontend-only compute

- Export and MCP paths don't run frontend code.
- Backend ownership keeps the rendered text consistent across
  surfaces — exactly the issue ADR-179 set out to solve for the
  inverse direction (renderer in backend, surfaces consume).

## Consequences

- `backend/app/diagrams/service.py::get_diagram` gains an opt-in
  branch for `dynamic_list` (and future computed types).
- New compute module `backend/app/diagrams/dynamic_list.py`
  (per-type compute lives in the diagram module that introduced
  it).
- Frontend strips `content` + `is_content_locked` from `data` on
  PUT bodies for `dynamic_list` (and equivalents).
- Tests assert (a) the synthesised keys are absent from the DB row
  but present on the API response, and (b) export markdown matches
  the API read's `data.content` byte-for-byte.

## Verification

- `pytest backend/tests/test_diagrams/test_dynamic_list_read.py`
  exercises both halves: read populates the keys, raw row doesn't
  contain them.
- `pytest backend/tests/test_export/test_dynamic_list_export.py`
  asserts export equals API read content.

## See also

- [ADR-186](ADR-186-Dynamic-List-Diagram-Type.md) — first opt-in
  consumer.
- [ADR-179](ADR-179-Renderer-And-Artefact-Store.md) — the parallel
  renderer single-source pattern.
- [SPEC-187-A](specs/SPEC-187-A-Synthesised-Content-On-Read.md).
- Issue [#147](https://github.com/cgbarlow/iris/issues/147).
