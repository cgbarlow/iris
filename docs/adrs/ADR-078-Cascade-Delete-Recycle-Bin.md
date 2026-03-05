# ADR-078: Cascade Delete, Recycle Bin, and Bookmarks Set Filtering

## Proposal: Cascade package deletion with recycle bin and bookmarks set filter

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-078 |
| **Initiative** | Data Lifecycle |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-04 |
| **Status** | Approved |
| **Dependencies** | ADR-071, ADR-077 |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris managing hierarchical packages containing child packages and diagrams,

**facing** the problem that deleting a package leaves orphaned children, soft-deleted items cannot be recovered, and the bookmarks page ignores the global set filter,

**we decided for** implementing cascade soft-delete that marks all descendant packages and diagrams as deleted with a shared group ID, a recycle bin UI for browsing and restoring deleted items, and adding SetSelector filtering to the bookmarks page,

**and neglected** hard-delete cascades (irreversible), individual-only deletion (tedious for large trees), and a separate trash database (over-engineered),

**to achieve** safe bulk deletion with full recovery capability, consistent set filtering across all list pages, and a complete data lifecycle from creation through deletion to restoration,

**accepting that** the recycle bin must be manually emptied for permanent deletion, cascade restore re-creates the full hierarchy, and the deleted_group_id column adds minimal storage overhead.

---

## Decisions

1. **Cascade soft-delete**: Deleting a package soft-deletes all descendant packages and their diagrams in a single transaction
2. **Deletion group ID**: A shared UUID (`deleted_group_id`) links all items deleted in one cascade, enabling grouped restore
3. **Child count warning**: Before deletion, the UI fetches descendant counts and shows a confirmation dialog with specific numbers
4. **Recycle bin**: A dedicated page lists all soft-deleted items with restore and permanent delete actions
5. **Grouped restore**: Items sharing a `deleted_group_id` can be restored together in one action
6. **Restore versioning**: Restoring an item creates a new version with `change_type='restore'`
7. **Bookmarks set filtering**: The bookmarks page uses the same SetSelector pattern as other list pages

---

## Specification

See [SPEC-078-A](specs/SPEC-078-A-Cascade-Delete-Recycle-Bin.md).
