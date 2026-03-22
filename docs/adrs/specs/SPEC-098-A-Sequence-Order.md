# SPEC-098-A: Sequence Order

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-098-A |
| **ADR** | [ADR-098](../ADR-098-Diagram-Sequence-Order.md) |
| **Status** | Draft |
| **Date** | 2026-03-22 |

---

## Overview

Add user-controllable ordering for diagrams and packages in the navigation hierarchy tree. Users can drag items up/down within a parent package to reorder them.

## Database Changes

### SQLite Migration (m029)

```sql
ALTER TABLE diagrams ADD COLUMN sequence_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE packages ADD COLUMN sequence_order INTEGER NOT NULL DEFAULT 0;
```

Backfill existing rows by rowid to preserve creation order.

### Supabase Migration (m032)

```sql
ALTER TABLE diagrams ADD COLUMN sequence_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE packages ADD COLUMN sequence_order INTEGER NOT NULL DEFAULT 0;
```

Backfill using `row_number() OVER (ORDER BY created_at)`.

## API Changes

### `PUT /api/diagrams/reorder`

Request body:
```json
{
  "parent_package_id": "string | null",
  "ordered_ids": ["id1", "id2", "id3"]
}
```

- `parent_package_id`: the parent package containing the siblings (null for root-level items)
- `ordered_ids`: array of diagram and package IDs in desired order

The endpoint updates `sequence_order` for each item to match its array index position. Items not in the list retain their current `sequence_order`.

### Hierarchy query update

`get_diagram_hierarchy()` ORDER BY changes from:
```sql
ORDER BY t.node_type, t.name
```
to:
```sql
ORDER BY t.node_type, t.sequence_order, t.name
```

## Frontend Changes

### TreeNode drag-and-drop

- Each tree node row gets a drag handle (grip icon) visible on hover
- `draggable="true"` on the row element
- `ondragstart`: set drag data (node ID, parent package ID)
- `ondragover`: show drop indicator line between nodes; only allow drops within same parent
- `ondrop`: compute new order, call `PUT /api/diagrams/reorder`, update local state
- Visual feedback: blue line between nodes during drag

### DiagramHierarchyNode type

Add `sequence_order: number` to the TypeScript interface and Pydantic model.

## Default Ordering

- New diagrams/packages get `sequence_order = max(sibling sequence_orders) + 1`
- This is handled in `create_diagram()` and `create_package()` service functions

## Acceptance Criteria

1. Diagrams/packages display in `sequence_order` order (then by name as tiebreaker)
2. Users can drag items up/down within a package to reorder
3. Reorder persists across page reloads
4. New items appear at the end of their sibling group
5. Existing items get creation-order sequence on migration
