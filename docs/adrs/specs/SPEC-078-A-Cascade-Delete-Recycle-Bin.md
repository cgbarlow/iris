# SPEC-078-A: Cascade Delete, Recycle Bin, and Bookmarks Set Filtering

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-078-A |
| **ADR Reference** | ADR-078 |
| **Date** | 2026-03-04 |
| **Status** | Approved |

---

## Overview

Three features addressing data lifecycle gaps:
1. Cascade soft-delete of packages with descendant count warnings
2. Recycle bin for browsing, restoring, and permanently deleting soft-deleted items
3. Set filtering on the bookmarks page

## Migration: m019_recycle_bin

Add `deleted_group_id TEXT` column to `packages`, `diagrams`, and `elements` tables with partial indexes for efficient recycle bin queries.

## Feature 1: Cascade Delete

### Backend

- `count_package_descendants(db, package_id)` — recursive CTE counting child packages and diagrams
- `cascade_delete_package(db, package_id, deleted_by, expected_version)` — OCC check, generate group UUID, recursive soft-delete all descendants
- `GET /api/packages/{id}/descendants/count` — returns child_packages and child_diagrams counts
- `DELETE /api/packages/{id}` — changed to call cascade_delete_package

### Frontend

- Package detail page fetches descendant counts before showing delete confirmation
- Dynamic message: "This will delete X child packages and Y diagrams"

## Feature 2: Recycle Bin

### Backend Module: `backend/app/recycle_bin/`

- `list_deleted_items(db, page, page_size)` — UNION ALL across tables where `is_deleted=1`
- `cascade_restore_by_group(db, group_id, restored_by)` — restore all items sharing a group ID
- `hard_delete_item(db, item_type, item_id)` — permanent deletion of soft-deleted items
- Restore functions in existing services: `restore_package`, `restore_diagram`, `restore_element`

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/recycle-bin` | List deleted items (paginated) |
| POST | `/api/recycle-bin/packages/{id}/restore` | Restore package |
| POST | `/api/recycle-bin/diagrams/{id}/restore` | Restore diagram |
| POST | `/api/recycle-bin/elements/{id}/restore` | Restore element |
| POST | `/api/recycle-bin/groups/{group_id}/restore` | Restore cascade group |
| DELETE | `/api/recycle-bin/{item_type}/{id}` | Permanently delete |

### Frontend

- New route: `/recycle-bin`
- Table with type badge, name, set, deleted date, deleted by
- Per-item restore and permanent delete actions
- Group restore button for cascade-deleted items
- Navigation item in AppShell after Bookmarks

## Feature 3: Bookmarks Set Filtering

- Import SetSelector and activeSet store
- Filter bookmarks client-side by set_id matching diagram or package set_id
- "No bookmarks in this set" empty state

## Acceptance Criteria

1. Deleting a package cascades to all descendant packages and diagrams
2. Warning dialog shows accurate descendant counts before deletion
3. All cascade-deleted items share the same `deleted_group_id`
4. Recycle bin lists all soft-deleted items across all types
5. Individual restore creates a version with `change_type='restore'` and clears `deleted_group_id`
6. Group restore restores all items in a cascade group
7. Permanent delete removes all database rows
8. Bookmarks page filters by active set
