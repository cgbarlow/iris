# SPEC-148-A: ArchiMate Open Exchange XML Import

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-148-A |
| **Implements** | [ADR-148](../ADR-148-ArchiMate-OEX-Import.md) |
| **Status** | Implemented (v5.6.0) |
| **Date** | 2026-05-07 |

---

## Scope

Backend reader, mapper, service, and router for The Open Group ArchiMate®
Model Exchange File Format (OEX), versions 3.0 / 3.1 / 3.2; frontend file
picker extension; UAT Playwright verification spec.

Out of scope: OEX export.

---

## File format reference

```xml
<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       identifier="model-id">
  <name>...</name>
  <documentation>...</documentation>
  <elements>
    <element identifier="el-1" xsi:type="BusinessActor">
      <name>...</name>
      <documentation>...</documentation>
    </element>
  </elements>
  <relationships>
    <relationship identifier="rel-1" source="el-1" target="el-2" xsi:type="Serving"/>
  </relationships>
  <organizations> ... </organizations>     <!-- ignored -->
  <views>
    <diagrams>
      <view identifier="v-1" xsi:type="Diagram">
        <name>...</name>
        <node identifier="n-1" elementRef="el-1" x="..." y="..." w="..." h="..."/>
        <connection identifier="c-1" relationshipRef="rel-1" source="n-1" target="n-2"/>
      </view>
    </diagrams>
  </views>
</model>
```

Accepted namespaces (regex `^http://www\.opengroup\.org/xsd/archimate/3\.\d+/?$`):

- `http://www.opengroup.org/xsd/archimate/3.0/`
- `http://www.opengroup.org/xsd/archimate/3.1/`
- `http://www.opengroup.org/xsd/archimate/3.2/`

---

## Element type mapping

OEX `xsi:type` values are unprefixed (e.g. `BusinessActor`). The mapper
prefixes them with `ArchiMate_` and delegates to the existing
[`ARCHIMATE_STEREOTYPE_MAP`](../../backend/app/import_sparx/mapper.py)
for the 40+ ArchiMate types. Local overrides for non-stereotype xsi types:

| OEX `xsi:type` | iris element_type |
|---|---|
| `Note` | `note` |
| `Group` | `boundary` |
| `Junction` | `junction` |
| `AndJunction` | `junction` |
| `OrJunction` | `junction` |

Unknown types yield an `unmapped_element_type` warning and are skipped.

---

## Relationship type mapping

`backend/app/import_archimate/mapper.py:RELATIONSHIP_TYPE_MAP`:

| OEX `xsi:type` | iris relationship_type |
|---|---|
| `Composition` | `composition` |
| `Aggregation` | `aggregation` |
| `Assignment` | `assignment` |
| `Realization` / `Realisation` | `realization` |
| `Serving` / `Used` / `UsedBy` | `serving` |
| `Triggering` | `triggering` |
| `Flow` | `flow` |
| `Specialization` / `Specialisation` | `specialization` |
| `Access` | `access` |
| `Influence` | `influence` |
| `Association` | `association` |

Unknown relationship types yield an `unmapped_relationship` warning and
are skipped. Relationships whose source or target element wasn't created
yield a `dangling_relationship` warning.

---

## View import

For each OEX `<view>`:

1. Walk every `<node>` (recursively — nested children represent
   ArchiMate compound nodes); flatten to absolute coordinates by summing
   parent offsets.
2. Map `elementRef` → already-created iris element id; build a canvas
   node `{id, type, position: {x, y}, data: {label, entityType, entityId, visual: {width, height}}, measured}`.
3. For each `<connection>` with both endpoints resolvable: build a
   canvas edge `{id, source, target, type: "default", data}`.
4. Persist via `create_diagram(...)` with `notation="archimate"`,
   `diagram_type="free_form"`, parented under the per-import package.

## Auto-generated Overview (model-only OEX)

When `model.views` is empty:

1. Sort imported element ids by `(iris_type, name)` so same-type
   elements cluster.
2. Compute `cols = ceil(sqrt(n))`.
3. Place node `i` at `(col=i%cols, row=i//cols)` with cell size
   220×140 px. Default node size 120×60.
4. Build edges from the iris `relationships` table for the imported
   element ids — one SQL query, O(R).
5. Persist as `"<model name> — Overview"` with notation `archimate`.
6. Emit an `auto_layout` warning so the operator knows the diagram
   was synthesised.

---

## API

### `POST /api/import/archimate`

| Field | Value |
|---|---|
| Auth | Required (Bearer JWT) |
| Body | `multipart/form-data` |
| Form fields | `file` (the .xml/.archimate/.oex), `set_id` (optional) |

Behaviour:
- Reject 400 if filename does not end with `.xml`, `.archimate`, or `.oex`.
- Reject 400 if the OEX namespace string isn't in the first 4 KiB of the
  file (content sniff guards against accidental SVG/XHTML/etc upload).
- Reject 400 if `set_id` is supplied but doesn't reference an existing
  set.
- On success, return JSON:
  ```json
  {
    "packages_created": 1,
    "elements_created": 127,
    "elements_skipped": 0,
    "relationships_created": 977,
    "relationships_skipped": 0,
    "diagrams_created": 1,
    "warnings": [
      { "category": "auto_layout", "message": "..." }
    ]
  }
  ```

---

## Frontend

`frontend/src/routes/import/+page.svelte` extended:
- File `<input>` `accept` attribute lists `.xml,.archimate,.oex` in
  addition to the existing `.qea,.eap,.pptx`.
- Help text mentions "ArchiMate Open Exchange (.xml, .archimate, .oex)".
- Single-file selection routes to `/api/import/archimate` via a new
  `isArchimate` derived state.

---

## Test fixtures

Both committed under `docs/reference/ArchiMate/`:

- `sample-with-view.xml` — hand-authored, 3 elements / 2 relationships /
  1 view. Exercises the view-import path.
- `msd-map.xml` — snapshot of
  https://github.com/1punchtan/msd-business-architecture (CC0 / public
  MSD policy material). 127 elements, 977 relationships, 0 views.
  Exercises the auto-layout path and proves the importer scales.

---

## Verification

Backend:

```bash
cd backend && .venv/bin/python -m pytest tests/test_import_archimate -q
```

Expected: ~32 tests green.

Frontend (run from a Node ≥20 environment — vite-plugin-svelte requires
`node:util.styleText`):

```bash
cd frontend && npm run test:unit -- importPageAcceptsArchimate
```

UAT (post-promotion):

```bash
cd frontend && npm run test:uat -- issue-52-archimate-import
```

Expected: 3 specs green; screenshots under
`frontend/tests/e2e/uat/screenshots/52-*.png` show the 127-node
Overview diagram and a populated elements list.

Manual smoke (local dev):

1. Start the backend + frontend.
2. Drag `docs/reference/ArchiMate/msd-map.xml` onto `/import`.
3. Pick a target set, click Import.
4. Click "Browse Views" → open the imported "MSD MAP Business
   Architecture — Overview" diagram → 127 nodes render in a grid.
