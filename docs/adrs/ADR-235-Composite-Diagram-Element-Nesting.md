# ADR-235: Nest a composite diagram under its element via the EA `parent` attribute

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-235 |
| **Initiative** | Make imported GEANZ capability diagrams nest under their capability element, as Sparx shows them |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the GEANZ Common Business Capabilities model imported
into Iris, where the nav tree should show each capability diagram nested under
its capability element (the "CCO.08 Payroll capability area" diagram beneath
the "Payroll" element) exactly as Sparx EA's Project Browser does,

**facing** that all 40 diagrams instead appeared **flat under the root
package**, because the XMI importer derived a diagram's owning element only
from the `<model owner="...">` attribute — and in this model every diagram's
`owner` is the **root package** (the EA "filed-under" location), so the
ADR-221 composite-link logic (`owner != package`) never fired and
`detail_diagram_id` was never set,

**we decided to** read the diagram's `<model parent="...">` attribute as the
authoritative composite child-diagram link: EA records the Project-Browser
nesting there (it names the owning **element**), while `owner` only names the
package the diagram is filed under. The XMI reader now derives the diagram's
`ParentID` from `parent` first, falling back to a non-package `owner` for
exports that only set the latter. The existing orchestrator post-process
(ADR-221, service.py step 7) then sets the owning element's
`detail_diagram_id`, and `get_diagram_hierarchy`'s existing COALESCE nests the
diagram under that element node — no new schema, no name-matching heuristic.

**because** the link is structural and unambiguous: 39 of the 40 GEANZ
diagrams carry `parent="EAID_…"` pointing at a real element (the 1 without is
the top-level capability-zones map, a genuine root diagram), and that element
is already imported and nested by ADR-231. Matching diagram→element by name
was considered and rejected — only 13/40 names match cleanly (the EA code
prefix and the inconsistent "capability area"/"capability zone" suffixes make
it fragile), whereas `parent` resolves 39/40 deterministically.

## Consequences
- Imported GEANZ capability diagrams nest under their capability element in the
  hierarchy tree and become that element's drill-down (detail) diagram — the
  Sparx Project-Browser structure is reproduced.
- Applies to any Sparx XMI export that records composite diagrams via `parent`,
  not just GEANZ.
- Import-side only → existing sets must be **re-imported** to pick up the link
  (`detail_diagram_id` is back-filled idempotently on re-import of the same set).
- The top-level capability-zones map correctly stays at the package root (it has
  no parent element).

## Alternatives considered
- **Name-matching** diagram → element (strip code prefix / suffix): rejected —
  26/40 misses; fragile and locale-sensitive (e.g. "Māori-Crown Relations").
- **Leave diagrams flat** (faithful to `owner`): rejected — `owner` is only the
  filing package; `parent` is the nesting the user sees in Sparx and expects.
- **New explicit diagram→element column**: rejected — `detail_diagram_id`
  (ADR-221) already models exactly this composite child-diagram relationship.

## Surface parity (§14) / §15
Pure import-reader logic; reuses the ADR-221 `detail_diagram_id` post-process.
No schema, no new endpoints, no MCP/CLI surface, no migration.

## Dependencies
Builds on ADR-221 (composite `detail_diagram_id` drill-down), ADR-231
(element containment), and ADR-232 (hierarchy COALESCE nesting).
Spec: `docs/adrs/specs/SPEC-235-A-Composite-Diagram-Element-Nesting.md`.
