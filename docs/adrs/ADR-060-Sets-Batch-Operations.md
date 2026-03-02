# ADR-060: Sets, Batch Operations & Pagination

## Proposal: Add Sets for Workspace Grouping, Batch Operations, and Pagination Controls

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-060 |
| **Initiative** | Sets & Batch Operations |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Approved |
| **Dependencies** | ADR-037 (Tags), ADR-055 (Model Hierarchy) |

---

## ADR (WH(Y) Statement format)

**In the context of** managing growing numbers of models and entities in Iris where users need to organise items into independent workspaces and perform bulk actions efficiently,

**facing** the limitation that Iris has a flat tag system with no higher-level grouping, no way to perform operations on multiple items simultaneously, and frontend list pages are hardcoded to 50 items with no pagination controls,

**we decided for** introducing a "Set" concept as a top-level grouping (each model/entity belongs to exactly one set), adding batch API endpoints for delete/clone/set-reassignment/tag-modification on up to 100 items at a time, and exposing existing backend pagination through frontend page controls,

**and neglected** multi-set membership (adds complexity with tag scoping), hierarchical sets/folders (sets are flat by design — hierarchy exists at the model level via ADR-055), and server-side search pagination (frontend client-side filtering is sufficient at current scale),

**to achieve** clean workspace isolation where tags are scoped per-set, efficient bulk management of items, and user-controlled page sizes with navigation for large datasets,

**accepting that** existing items are migrated to a "Default" set (cannot be deleted), auto-membership moves entities to their model's set on canvas save, and clone operations are shallow copies that do not clone linked entities.

---

## Decisions

1. **One set per item**: Models and entities belong to exactly one set (like folders, not labels)
2. **Default set**: Migration creates a well-known "Default" set (UUID `00000000-0000-0000-0000-000000000001`) and backfills all existing data
3. **Tag scoping**: Tags are stored the same way but UI/API filters by set — "v1.0" in Set A is independent from "v1.0" in Set B
4. **Auto-membership**: When a model's canvas is saved, entities on it are reassigned to the model's set
5. **Shallow clone**: Batch clone copies metadata with new ID, version 1, preserves tags and set; does not clone linked entities
6. **Import assignment**: Import page gets a set selector — all imported items go into the chosen set
7. **Max 100 per batch**: Batch operations limited to 100 IDs per request to prevent abuse
8. **Soft delete protection**: Default set cannot be deleted; non-empty sets cannot be deleted

---

## References

- SPEC-060-A: Sets, Batch Operations & Pagination specification
