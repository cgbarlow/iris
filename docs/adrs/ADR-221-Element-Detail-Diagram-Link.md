# ADR-221: Element → Detail Diagram Link (composite-element drill)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-221 |
| **Initiative** | Let an element declare a navigable "detail diagram" so users can drill in and out of the model |
| **Proposed By** | Engineering |
| **Date** | 2026-05-29 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** issue #242 — a user saw "10 capabilities" reported
against the element *CSE.04 Cyber Security* and expected to be able to
drill from there into the diagram that elaborates those capabilities
(*CSE.00 Security capability zone*), but found no link and an empty
Relationships panel; the user's framing is that iris is meant to let you
"drill in and out" and here discoverability failed,

**facing** that iris relationships are strictly **element ↔ element**
(`app/relationships/`, an edge between two element rows created from a
canvas edge), so there is no way to represent or surface a navigable link
from an element to a *diagram*. A view is not a valid relationship
endpoint, and overloading relationships to point at diagrams would muddy
their semantics and ripple through `relationship_count`, the canvas
edge → relationship auto-creation, and every relationship consumer. The
thing the user actually wants is a **navigation link** (drill-down), which
is a different concept from a semantic relationship. Sparx EA — which iris
imports (ADR-059/084/219) — models exactly this as a **composite element**
(`t_diagram.ParentID` points at the owning element), and iris currently
**discards** that information on import,

**we decided to**:
1. Add an optional, nullable **`detail_diagram_id`** column to the
   `elements` table (FK → `diagrams(id)`), carried on the element row
   exactly like `package_id` (ADR-184) — i.e. **not** versioned in
   `element_versions`. Migration `m080` (SQLite) + `m086` (Supabase
   mirror), idempotent, no back-fill (protocol §15).
2. Treat it as **tri-state on update** (omit = leave untouched, `null` =
   clear, string = set), reusing the `package_id` sentinel pattern in
   `ElementUpdate` / `update_element` / the `PUT` router.
3. Surface it across all three write surfaces (protocol §14): the
   `create_element` / `update_element` MCP tools and the `iris create
   element` / `iris update element` CLI commands gain a
   `detail_diagram_id` / `--detail-diagram-id` field. No new write *op*,
   so the parity script is unaffected, but the field must exist on all
   three surfaces.
4. Surface it for **reading** as a drill-in on the element detail page
   (a "Detail diagram" link to `/views/<id>`) and as a "Referenced by"
   list on the diagram (`get_diagram` gains `referenced_by_elements`,
   computed from `SELECT … FROM elements WHERE detail_diagram_id = ?`).
5. Let **smart-markdown** emit the drill inline: a new
   `{{element:<id>:detail_diagram}}` token resolves to a link to the
   element's detail diagram (`[name](iris://diagram/<id>)`), so authored
   views like the #242 demo can show a clickable drill beside a value.
6. **Preserve the link on Sparx import**: the `.qea` reader and the
   native XMI reader read `t_diagram.ParentID` / the composite parent,
   and `import_sparx_model` maps element `ea_guid` → diagram iris id to
   populate `detail_diagram_id` after diagrams are created. Composite
   elements imported from EA light up the drill automatically.

**to achieve** a first-class, queryable, navigable element → diagram
drill that matches the user's "drill in and out" mental model, restores
the discoverability gap from #242, and turns the previously-discarded
Sparx composite-element semantics into a real iris feature — without
distorting the element ↔ element relationship model.

**accepting** that:
- **Cross-set links are allowed.** The #242 demo links an element in the
  "Aggregation Demo" set to a diagram in the "GEANZ Sparx EA" set. The FK
  is to `diagrams(id)` with no same-set constraint; validation only checks
  the target diagram exists and is not soft-deleted. (Contrast ADR-178's
  no-cross-set-*move* rule — a navigation pointer is not a move.)
- It is a **single** pointer per element (one detail diagram), mirroring
  Sparx's one-composite-diagram-per-element. Multiple detail diagrams are
  out of scope; the `referenced_by_elements` direction is naturally
  many-to-one and needs no extra storage.
- The "10" in the #242 demo is a **hard-coded literal** in the
  smart-markdown source, not a computed count; making it a real count is a
  separate concern (aggregation, ADR-212) and explicitly **not** fixed
  here. This ADR fixes the *navigation* gap only.
- `detail_diagram_id` is **not** a relationship and does not affect
  `relationship_count` or canvas edge auto-creation.

## Rejected alternatives

- **Store the pointer in `elements.metadata` (JSON).** Cheaper (no
  migration) and the Sparx importer already writes `metadata.ea_guid`.
  Rejected: it is not first-class — not a validated field, not indexable,
  and the diagram-side "Referenced by" query would require scanning JSON
  blobs instead of an indexed column. "First-class drill link" was the
  explicit ask.
- **Generalise relationships to accept diagram endpoints
  (element↔diagram, diagram↔diagram).** This is literally what the issue
  asked for ("inbound diagram relationship"). Rejected: high blast radius
  (every relationship query and the canvas auto-creation assume
  element↔element) and conceptually muddy — a view is not a model element.
  Keep navigation links distinct from semantic relationships.
- **Smart-markdown authored link only (no schema).** A
  `{{diagram:<id>:name}}` token already produces a clickable diagram link
  today with zero code. Rejected as the *primary* solution: it is manual
  per-line, doesn't populate the element's drill affordance or the
  diagram's "Referenced by", and can't be auto-populated from Sparx
  imports. Retained as the *inline surfacing* of the real field (decision
  5), not as a substitute for it.

## Dependencies

- Builds on ADR-184 (`elements.package_id` — the column + tri-state
  pattern this mirrors).
- Builds on ADR-205/209/210 (smart-markdown tokens + `iris://` links) for
  the inline `detail_diagram` token.
- Builds on ADR-219/059/084 (Sparx import pipeline) for auto-population.
- Relates to ADR-023 (`linkedModelId` per-canvas-node drill) — a *node*
  level pointer; this ADR adds the *element* level pointer. They are
  distinct and complementary.

## Consequences

- Spec: see SPEC-221-A.
- Surface parity (§14) preserved: field added to API + MCP + CLI.
- Migration parity (§15): `m080` SQLite + `m086` Supabase ship together
  with a schema test.
