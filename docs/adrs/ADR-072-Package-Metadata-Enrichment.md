# ADR-072: Package Metadata Enrichment

## Proposal: Capture full SparxEA package metadata during import

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-072 |
| **Initiative** | SparxEA Gap Closure |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-04 |
| **Status** | Approved |
| **Dependencies** | ADR-071 |

---

## ADR (WH(Y) Statement format)

**In the context of** importing SparxEA `.qea` files where packages carry rich metadata (ea_guid, dates, scope, version, author, stereotype, tagged values) that is currently discarded during import,

**facing** loss of valuable metadata that users need for traceability and auditing,

**we decided for** enriching the import pipeline to capture all available package metadata fields from both the `t_package` and `t_object` (package-type element) tables, including tagged values from `t_objectproperties`, and displaying them in an Extended accordion on the package detail page,

**and neglected** a minimal approach capturing only Status/Stereotype (insufficient for AIXM-scale imports),

**to achieve** full metadata fidelity for imported packages matching the existing element metadata pattern,

**accepting that** this adds more data to the database but provides essential traceability.

---

## Decisions

1. **Import enrichment**: Capture ea_guid, Status, Stereotype, Version, Scope, Author, Complexity, Phase, CreatedDate, ModifiedDate, GenType, and tagged values into package metadata
2. **Package detail page**: Create `/packages/[id]` route with Overview, Details, and Extended accordion sections matching the element detail page pattern
3. **Extended accordion**: Display all enriched metadata fields and tagged values table

---

## Specification

See [SPEC-072-A](specs/SPEC-072-A-Package-Metadata-Enrichment.md).
