# SPEC-019-A: Metadata Display

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-019-A |
| **ADR Reference** | [ADR-019: Metadata and User Attribution Display](../ADR-019-Metadata-and-User-Attribution-Display.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification covers resolving created_by UUIDs to usernames in entity and model API responses, and displaying user attribution and modification timestamps on frontend detail pages and version history tables.

---

## A. Backend: Resolve Usernames in Entity Service

### get_entity() — JOIN users table

Modify the SELECT query to LEFT JOIN the users table and include `u.username` in the result set. Add `created_by_username` to the returned dictionary, falling back to `"Unknown"` if the user account no longer exists.

```python
cursor = await db.execute(
    "SELECT e.id, e.entity_type, e.current_version, "
    "ev.name, ev.description, ev.data, "
    "e.created_at, e.created_by, e.updated_at, e.is_deleted, "
    "u.username "
    "FROM entities e "
    "JOIN entity_versions ev ON e.id = ev.entity_id "
    "AND e.current_version = ev.version "
    "LEFT JOIN users u ON e.created_by = u.id "
    "WHERE e.id = ? AND e.is_deleted = 0",
    (entity_id,),
)
```

Return dict addition: `"created_by_username": row[10] or "Unknown"`

### get_entity_versions() — JOIN users table

Modify the query to LEFT JOIN users and include `u.username` for each version row. Add `created_by_username` to each version dictionary.

```python
cursor = await db.execute(
    "SELECT ev.entity_id, ev.version, ev.name, ev.description, ev.data, "
    "ev.change_type, ev.change_summary, ev.rollback_to, "
    "ev.created_at, ev.created_by, "
    "u.username "
    "FROM entity_versions ev "
    "LEFT JOIN users u ON ev.created_by = u.id "
    "WHERE ev.entity_id = ? "
    "ORDER BY ev.version DESC",
    (entity_id,),
)
```

Return dict addition per row: `"created_by_username": r[10] or "Unknown"`

---

## B. Backend: Resolve Usernames in Model Service

### get_model() — JOIN users table

Same pattern as `get_entity()`. LEFT JOIN users on `m.created_by = u.id`. Add `created_by_username` to the returned dictionary.

### get_model_versions() — JOIN users table

Same pattern as `get_entity_versions()`. LEFT JOIN users on `mv.created_by = u.id`. Add `created_by_username` to each version dictionary.

---

## C. Frontend: Type Definitions

Add `created_by_username?: string` to:
- `Entity` interface
- `Model` interface
- `EntityVersion` interface
- `ModelVersion` interface

The field is optional (`?`) because older API responses or list endpoints may not include it.

---

## D. Frontend: Entity Detail Page

### Details Tab

After the "Created" row in the `<dl>`, add:
- **Created By** — displays `entity.created_by_username` with fallback to `entity.created_by` (UUID)
- **Modified** — displays `entity.updated_at` with fallback to `'N/A'`

### Version History Tab

Add a "User" column header to the table and a corresponding `<td>` in each version row displaying `v.created_by_username` with fallback to `v.created_by`.

---

## E. Frontend: Model Detail Page

### Overview Tab

After the "Created" row in the `<dl>`, add:
- **Created By** — displays `model.created_by_username` with fallback to `model.created_by` (UUID)
- **Modified** — displays `model.updated_at` with fallback to `'N/A'`

### Version History Tab

Add a "User" column header and data cell, same pattern as entity detail page.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Entity detail page shows created_by username | Create entity; view detail page; verify username displayed (not UUID) |
| Entity detail page shows updated_at | Update entity; verify "Modified" field shows timestamp |
| Entity version history shows User column | View entity versions tab; verify "User" column with usernames |
| Model detail page shows created_by username | Create model; view detail page; verify username displayed |
| Model detail page shows updated_at | Update model; verify "Modified" field shows timestamp |
| Model version history shows User column | View model versions tab; verify "User" column with usernames |
| Fallback to UUID when user deleted | If user account removed, detail page shows UUID instead of blank |
| API backward compatibility | Existing fields unchanged; new field is additive |

---

*This specification implements [ADR-019](../ADR-019-Metadata-and-User-Attribution-Display.md).*
