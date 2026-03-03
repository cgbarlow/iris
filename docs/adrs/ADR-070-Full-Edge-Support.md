# ADR-070: Full Edge Support from SparxEA

## Proposal: Extend SparxEA connector import to capture full edge metadata

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-070 |
| **Initiative** | SparxEA Import Fidelity |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-066 (Import All Skipped Items), ADR-069 (Note/Boundary Label Derivation) |

---

## ADR (WH(Y) Statement format)

**In the context of** SparxEA connectors containing rich metadata (direction, cardinality, roles, stereotypes, route styling, and navigability) in the `t_connector` table that is currently discarded during import, resulting in edges that only carry type and label,

**facing** loss of semantic information on imported relationships and canvas edges, preventing accurate rendering of cardinality labels, directional arrows, role annotations, and routing styles in the Iris model editor,

**we decided for** extending `QeaConnector` with Direction, SourceCard, DestCard, SourceRole, DestRole, Stereotype, RouteStyle, SourceIsNavigable, and DestIsNavigable fields; adding Nesting-to-contains mapping; and populating both relationship data dicts and canvas edge data dicts with this metadata,

**and neglected** importing only a subset of fields (incomplete), importing all 70+ columns from t_connector (over-engineering), and post-processing edges after import (fragile),

**to achieve** full-fidelity edge import from SparxEA that preserves cardinality, direction, roles, stereotypes, and routing information for both relationship records and canvas visualisation,

**accepting that** not all metadata may be rendered in the UI immediately (fields are stored and available for future frontend work).

---

## Decisions

1. **Reader extension**: Add 9 new fields to `QeaConnector` dataclass and extend SQL query
2. **Nesting mapping**: Map SparxEA `Nesting` connector type to Iris `contains` relationship type
3. **Relationship metadata**: Populate relationship `data` dict with direction, cardinality, roles, and stereotype
4. **Canvas edge metadata**: Populate edge `data` dict with cardinality, roles, stereotype, direction, and routingType
5. **Route style mapping**: Map RouteStyle 0 to `bezier`, RouteStyle 3 to `step`, default to `bezier`

---

## Specification

See [SPEC-070-A](specs/SPEC-070-A-Edge-Import-Metadata.md).
