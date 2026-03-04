# ADR-073: Import Idempotency and Import Set Cleanup

## Proposal: Re-importing the same .qea file skips existing items

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-073 |
| **Initiative** | SparxEA Gap Closure |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-04 |
| **Status** | Approved |
| **Dependencies** | ADR-072 |

---

## ADR (WH(Y) Statement format)

**In the context of** users re-importing the same .qea file (e.g., after updating a SparxEA project) and needing to avoid duplicate packages, elements, and diagrams,

**facing** the current import creating duplicate items on every re-import because there is no deduplication mechanism,

**we decided for** matching items by `ea_guid` stored in metadata, skipping creation of items that already exist in the target set, storing ea_guid in element and diagram metadata, and adding package cascade to force-delete set,

**and neglected** a database column approach (adding ea_guid columns to tables would require migration and schema changes),

**to achieve** idempotent re-imports where a second import of the same file creates zero new items,

**accepting that** metadata JSON LIKE queries are slower than indexed column lookups, but this is acceptable for the import use case which is not latency-sensitive.

---

## Decisions

1. **GUID index**: Build a lookup of existing ea_guid→iris_id before import from package/element/diagram metadata
2. **Skip logic**: Before creating each item, check if its ea_guid exists in the index; if so, reuse the existing ID
3. **ea_guid in metadata**: Store ea_guid in element and diagram metadata during import
4. **Skip counts**: Add `packages_skipped` and `diagrams_skipped` to ImportSummary
5. **Force-delete cascade**: Include packages and package_relationships in set force-delete
6. **Frontend**: Show skip counts on import results page

---

## Specification

See [SPEC-073-A](specs/SPEC-073-A-Import-Idempotency.md).
