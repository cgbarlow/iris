# ADR-059: SparxEA Import

## Proposal: Import SparxEA .qea Files into Iris

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-059 |
| **Initiative** | SparxEA Integration |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** migrating enterprise architecture models from Sparx Enterprise Architect to Iris, where organisations have significant investment in SparxEA repositories,

**facing** the need to import complex model hierarchies, elements, connectors, and diagrams from SparxEA's `.qea` file format (SQLite 3 databases since EA 16+),

**we decided for** implementing a backend import module (`app/import_sparx/`) that reads `.qea` files directly via `aiosqlite`, maps SparxEA types to Iris types, converts coordinates, and creates Iris models/entities/relationships with a single-file upload API endpoint,

**and neglected** implementing SparxEA's XMI export format (XML-based, less reliable than direct DB access), and a streaming/chunked import (unnecessary for typical repository sizes),

**to achieve** one-click import of SparxEA repositories with automatic type mapping, hierarchy preservation via `parent_model_id`, and diagram layout conversion,

**accepting that** unmapped types (Note, Boundary, Text, NoteLink) are skipped with warnings, BPMN diagrams are not imported (per ADR-058), and the import is a one-time operation (no ongoing synchronisation).

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-055 | Model Hierarchy | Package hierarchy maps to parent_model_id |
| Depends On | ADR-056 | ArchiMate Full Specification | ArchiMate type mapping |
| Depends On | ADR-057 | UML Type Expansion | UML type mapping |
| Relates To | ADR-058 | BPMN Deferral | BPMN diagrams skipped during import |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-059-A | Import Architecture | Technical Specification | [specs/SPEC-059-A-Import-Architecture.md](./specs/SPEC-059-A-Import-Architecture.md) |
| SPEC-059-D | Import UI | Technical Specification | [specs/SPEC-059-D-Import-UI.md](./specs/SPEC-059-D-Import-UI.md) |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | 2026-03-02 | Approved | Implementation | 6 months | 2026-09-02 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Architecture Team | 2026-03-02 |
