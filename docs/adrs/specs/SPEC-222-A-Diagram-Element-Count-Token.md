# SPEC-222-A: Smart-markdown diagram element-count token

Implements **[ADR-222](../ADR-222-Diagram-Element-Count-Token.md)**.

## Token

`{{diagram:<diagram-id>:element_count}}`

Renders the count of element nodes on the diagram's current-version
canvas, wrapped as `[<count>](iris://diagram/<id> "<diagram name>")`.

## Counting rule

A node counts when `node.data.entityType` is truthy and **not** in the
structural set `{"diagram_frame", "note"}`. Implemented in
`backend/app/diagrams/smart_markdown.py`:

- `_STRUCTURAL_NODE_TYPES = {"diagram_frame", "note"}`
- `_fetch_diagram_element_count(db, diagram_id)` reads the current
  `diagram_versions.data`, iterates `data.nodes`, returns the count as a
  string; `None` if the diagram is missing/deleted (→ strikethrough);
  `"0"` if the canvas has no nodes.
- `_resolve_one` routes the `diagram` + `element_count` field-spec to the
  helper; all other `diagram` field-specs still go to `_fetch_named_field`
  (name/description). The result flows through the existing
  link-wrapping.

## Acceptance criteria

1. `{{diagram:<id>:element_count}}` renders the number of element nodes,
   excluding `diagram_frame` and `note` nodes.
2. The rendered count links to `iris://diagram/<id>`.
3. A missing/deleted diagram → strikethrough (`~~…~~`), no link.

## Tests

`backend/tests/test_diagrams/test_smart_markdown.py`:
- `test_diagram_element_count_excludes_notes_and_frame`
- `test_diagram_element_count_links_to_the_diagram`
- `test_diagram_element_count_missing_diagram_strikes_through`
