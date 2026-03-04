# SPEC-071-A: Database Schema Rename

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-071-A |
| **ADR** | [ADR-071](../ADR-071-Naming-Rename.md) |
| **Status** | Draft |
| **Date** | 2026-03-03 |

## Migration m016

Uses ALTER TABLE RENAME TO for simple renames, and CREATE TABLE + INSERT INTO for splits.

### Table Renames
- `entities` → `elements`
- `entity_versions` → `element_versions`
- `entity_tags` → `element_tags`
- `model_relationships` → `package_relationships`

### Table Splits
- `models` → `diagrams` (rows with canvas data) + `packages` (rows without canvas data)
- `model_versions` → `diagram_versions` + `package_versions`
- `model_tags` → `diagram_tags`

### Column Renames
- All `entity_id` references → `element_id`
- All `model_id` references → `diagram_id` or `package_id`

### FTS5 Index
- Rebuild `search_index` with new table/column names
- diagram_type validation accepts C4 types

### Note
User base is zero — no backwards compatibility needed.
