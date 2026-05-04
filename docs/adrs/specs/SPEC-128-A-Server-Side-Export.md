# SPEC-128-A: Server-Side Export

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-128-A |
| **ADR** | [ADR-128](../ADR-128-Server-Side-Export.md) |
| **Status** | Proposed |
| **Date** | 2026-04-22 |

## Overview

Headless export of Iris entities as JSON or Markdown. One new router
(`/api/export/*`) covering five entity granularities. Reuses existing
response models for JSON; adds a deterministic Markdown templater.

## Endpoints

Router: `backend/app/export/router.py` mounted at `/api/export`.

| Method | Path | Bundle |
|---|---|---|
| `GET` | `/api/export/diagrams/{id}?format=json\|markdown` | Diagram + nodes + edges + linked elements + inter-entity relationships. |
| `GET` | `/api/export/elements/{id}?format=…` | Element + tags + usage stats + linked diagrams. |
| `GET` | `/api/export/packages/{id}?format=…` | Package + descendant packages/diagrams/elements. |
| `GET` | `/api/export/sets/{id}?format=…` | All packages/diagrams/elements in the set + set relationships. |
| `GET` | `/api/export/collections/{id}?format=…` | All sets in the collection (each set's bundle). |

**Auth:** `Depends(get_optional_user)` (anonymous allowed per ADR-123).

**Query params:** `format` (required; one of `json`, `markdown`).
Unrecognised `format` → 400.

**Response headers:**

```
Content-Type: application/json | text/markdown; charset=utf-8
Content-Disposition: attachment; filename="<kebab-name>-<id>.<ext>"
```

**Bundle size cap:** 10,000 elements per bundle. Exceeding returns
`413 Payload Too Large` with body `{"detail": "Export exceeds 10000
elements; use pagination on the list endpoints instead.", "count": N}`.

## JSON format

Bundle schemas under `backend/app/export/schemas.py` (Pydantic v2):

```python
class DiagramExport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    diagram: DiagramResponse
    nodes: list[DiagramNode]
    edges: list[DiagramEdge]
    elements: list[ElementResponse]          # only those referenced on the canvas
    relationships: list[RelationshipResponse]

class ElementExport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    element: ElementResponse
    tags: list[str]
    stats: ElementStats
    linked_diagrams: list[DiagramSummary]

class PackageExport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    package: PackageResponse
    descendant_packages: list[PackageResponse]
    diagrams: list[DiagramExport]            # inline, bounded by the cap
    elements: list[ElementResponse]          # all elements owned by the subtree

class SetExport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    set_: SetResponse = Field(alias="set")
    packages: list[PackageResponse]
    diagrams: list[DiagramExport]
    elements: list[ElementResponse]
    relationships: list[RelationshipResponse]

class CollectionExport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    collection: CollectionResponse
    sets: list[SetExport]
```

`schema_version` is a string literal so downstream consumers can
branch on it if we ship 2.0 later.

## Markdown format

One template function per entity type in
`backend/app/export/markdown.py`. Deterministic — no timestamps inside
the body, no GUIDs as identifiers unless the entity's name is empty.
Tests snapshot the exact string.

### Diagram template

```markdown
# {diagram.name}

**Type:** {diagram.diagram_type}
**Set:** {set.name}
**Tags:** {tags, comma-separated, or "_none_"}
**Version:** {diagram.version}

## Description

{diagram.description or "_No description._"}

## Nodes ({len(nodes)})

| Name | Type | Element |
|---|---|---|
| {node.label} | {node.node_type} | {element.name or "—"} |
...

## Edges ({len(edges)})

| From | To | Relationship | Label |
|---|---|---|---|
| {edge.source_name} | {edge.target_name} | {edge.relationship_type} | {edge.label or "—"} |
...

## Linked Elements ({len(elements)})

- **{element.name}** ({element.element_type}) — {element.description_oneline}
...
```

Other templates follow the same structure: H1 title, key metadata
table, description, then children/relationships as tables or
bulleted lists. Full templates live in
`backend/app/export/markdown.py`; snapshot tests under
`backend/tests/export/snapshots/`.

## Services

`backend/app/export/service.py`:

```python
async def build_diagram_bundle(db, diagram_id: str) -> DiagramExport: ...
async def build_element_bundle(db, element_id: str) -> ElementExport: ...
async def build_package_bundle(db, package_id: str, cap: int = 10_000) -> PackageExport: ...
async def build_set_bundle(db, set_id: str, cap: int = 10_000) -> SetExport: ...
async def build_collection_bundle(db, collection_id: str, cap: int = 10_000) -> CollectionExport: ...
```

The package / set / collection builders track cumulative element
count and raise `ExportTooLargeError(count)` when the cap is exceeded.
The router catches it and returns 413.

## Wiring

`backend/app/main.py` — mount the router:

```python
from app.export.router import router as export_router
app.include_router(export_router, prefix="/api/export", tags=["Export"])
```

## Testing (TDD)

### Snapshot tests

`backend/tests/export/test_markdown_snapshots.py` — one test per
entity type with a fixture entity and a committed
`.snapshot.md` file. Run via `pytest --snapshot-update` to refresh.

### JSON schema tests

- `test_diagram_export_roundtrips` — build bundle → serialise →
  `DiagramExport.model_validate_json()` → equal.
- `test_package_export_descendants_complete` — every diagram and
  element in the package subtree appears exactly once.
- `test_set_export_cap_exceeded_raises_413`.

### Router tests

- `test_format_query_required` — missing `?format=` → 400.
- `test_invalid_format` → 400.
- `test_content_disposition_filename` — matches kebab-case pattern.
- `test_anonymous_export_diagram` — per ADR-123, no auth needed.
- `test_export_404_for_missing_id`.

## Acceptance criteria

1. `GET /api/export/diagrams/{id}?format=json` returns a
   `DiagramExport` JSON body with `schema_version: "1.0"`.
2. `GET /api/export/sets/{id}?format=markdown` returns a
   `text/markdown` body with a deterministic filename header.
3. Anonymous callers can export (subject to rate-limit bucket).
4. Exporting a set with > 10,000 elements returns 413 with a count
   hint.
5. Snapshot tests pass; no stdin-generated randomness leaks into the
   output.
6. Existing client-side export (ADR-039, `frontend/src/lib/canvas/export.ts`)
   is unchanged and continues to work in the browser.
