# SPEC-221-A: Element → Detail Diagram Link

Implements **[ADR-221](../ADR-221-Element-Detail-Diagram-Link.md)**.
Status: living document.

## 1. Data model

`elements` gains a nullable `detail_diagram_id TEXT REFERENCES diagrams(id)`
column plus an index `idx_elements_detail_diagram`. Carried on the element
row (like `package_id`), **not** in `element_versions`.

- SQLite migration `m080_element_detail_diagram.py` — `PRAGMA table_info`
  guard + `ALTER TABLE elements ADD COLUMN detail_diagram_id …`, idempotent;
  registered in `app/startup.py` after `m079_up`.
- Supabase mirror `m086_element_detail_diagram.sql` — `ADD COLUMN IF NOT
  EXISTS` + `CREATE INDEX IF NOT EXISTS`. Header: `-- Mirrors SQLite m080.`
- Schema test `backend/tests/test_migrations/test_element_detail_diagram_schema.py`.

## 2. Backend API

- `ElementCreate`: add `detail_diagram_id: str | None = None`.
- `ElementUpdate`: add `detail_diagram_id: Any = _UNSET` (tri-state).
- `ElementResponse`: add `detail_diagram_id: str | None = None`.
- `create_element(...)`: new `detail_diagram_id` kwarg → persisted in the
  `elements` INSERT; validated (target diagram must exist + not deleted)
  via `_validate_detail_diagram_exists`; returned in the dict.
- `get_element(...)` / `list_elements(...)`: select `e.detail_diagram_id`
  and include in the returned dict.
- `update_element(...)`: tri-state `detail_diagram_id` kwarg (sentinel =
  leave untouched, `None` = clear, str = set + validate). The `UPDATE`
  `SET` clause is built dynamically so `package_id` and `detail_diagram_id`
  can each be touched independently.
- `PUT /api/elements/{id}`: forward `body.detail_diagram_id` only when not
  `_UNSET` (mirrors `package_id`). Validation error → HTTP 422 via a new
  `ElementDetailDiagramError(ValueError)`.

Validation: a missing/deleted target diagram raises
`ElementDetailDiagramError` → 422. Cross-set is allowed (no set check).

## 3. Diagram "Referenced by"

`get_diagram(...)` gains `referenced_by_elements: list[{id, name}]` from
`SELECT e.id, ev.name FROM elements e JOIN element_versions ev … WHERE
e.detail_diagram_id = ? AND e.is_deleted = 0`. Positional row access only
(Supabase parity, §15). `DiagramResponse` gains the field (default `[]`).

## 4. Smart-markdown token

`{{element:<id>:detail_diagram}}` (ADR-205/209). In `_resolve_one`, a
special case for `entity_type == "element"` and `field_spec ==
"detail_diagram"` resolves the element's `detail_diagram_id`, looks up the
target diagram name via `_fetch_entity_display_name(db, "diagram", …)`, and
returns `[name](iris://diagram/<id> "name")`. No detail diagram / missing
/ deleted target → `None` → strikethrough fallback (consistent with other
unresolvable tokens).

## 5. MCP + CLI (§14)

- MCP `create_element` / `update_element` (`mcp/src/iris_mcp/tools.py`):
  add `detail_diagram_id` to the input schema and request body. `update`
  uses the same tri-state merge as `package_id` (explicit key forwarded,
  including `null`).
- CLI (`cli/src/iris_cli/main.py`): `create element` and `update element`
  gain `--detail-diagram-id`. Tri-state on update mirrors `--package-id`.
- `scripts/check_surface_parity.py`: no change (no new write op).

## 6. Sparx import auto-population

- `.qea`: `QeaDiagram` gains `parent_element_id: int | None`; `read_diagrams`
  adds `ParentID` to its SELECT.
- Native XMI (`app/import_sparx_xml/reader.py`): extract the composite
  parent element for a diagram where present; set `parent_element_id`.
- `import_sparx_model(...)`: after diagrams are created and the
  element-guid → iris-id and diagram maps exist, for each diagram with a
  `parent_element_id`, resolve the owning element's iris id and set its
  `detail_diagram_id` to the diagram's iris id (idempotent; skip if the
  element or diagram is missing).

## 7. Frontend

- `routes/elements/[id]/+page.svelte`: a "Detail diagram" section (reuse
  the "Used in Views" pattern) showing a drill link to
  `/views/{detail_diagram_id}` when set; an edit control to set/clear it
  reusing the `DiagramPicker` used by `LinkedDiagramPanel.svelte`. The
  `ElementDetail`/types gain `detail_diagram_id`.
- Diagram/view side: render `referenced_by_elements` as a "Referenced by"
  list linking back to `/elements/{id}`.

## 8. Acceptance criteria

1. Creating/updating an element with `detail_diagram_id` persists and is
   returned by `get_element`; clearing with `null` works; setting a
   missing diagram → 422.
2. `get_diagram` lists referencing elements under `referenced_by_elements`.
3. `{{element:<id>:detail_diagram}}` renders a link to the target view;
   no/deleted target → strikethrough.
4. MCP + CLI can set/clear `detail_diagram_id`.
5. Element page shows + edits the drill; diagram shows "Referenced by".
6. Importing a Sparx model with composite elements populates
   `detail_diagram_id`.
7. SQLite + Supabase migrations both add the column idempotently; schema
   test passes.

## 9. Tests

- `backend/tests/test_elements/`: create/update/get round-trip, tri-state
  clear, missing-diagram 422, cross-set allowed.
- `backend/tests/test_diagrams/`: `referenced_by_elements`.
- `backend/tests/test_diagrams/` (smart-markdown): `detail_diagram` token
  render + strikethrough.
- `backend/tests/test_migrations/test_element_detail_diagram_schema.py`.
- `backend/tests/test_import_sparx*/`: composite-element population.
- Frontend: element drill + diagram referenced-by.
