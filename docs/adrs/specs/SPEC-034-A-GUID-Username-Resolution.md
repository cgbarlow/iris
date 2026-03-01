# SPEC-034-A: GUID Username Resolution

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-034-A |
| **ADR Reference** | [ADR-034: GUID to Username Resolution](../ADR-034-GUID-Username-Resolution.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification covers completing the GUID-to-username resolution across all API response schemas. The service layer already JOINs the users table and returns `created_by_username` for entities, models, and their versions, but the Pydantic schemas strip the field. Additionally, the relationships list endpoint does not resolve source/target entity names.

---

## A. Backend: Add `created_by_username` to Pydantic Response Schemas

### Entity Schemas (`backend/app/entities/models.py`)

Add `created_by_username: str = "Unknown"` to:
- `EntityResponse` — the service `get_entity()` already returns this field
- `EntityVersionResponse` — the service `get_entity_versions()` already returns this field

### Model Schemas (`backend/app/models_crud/models.py`)

Add `created_by_username: str = "Unknown"` to:
- `ModelResponse` — the service `get_model()` already returns this field
- `ModelVersionResponse` — the service `get_model_versions()` already returns this field

---

## B. Backend: Resolve Entity Names in Relationship Responses

### Pydantic Schema (`backend/app/relationships/models.py`)

Add to `RelationshipResponse`:
- `source_entity_name: str = ""`
- `target_entity_name: str = ""`

### Service Layer (`backend/app/relationships/service.py`)

Modify `list_relationships()` to JOIN entities and entity_versions to resolve source and target entity names:

```sql
SELECT r.id, r.source_entity_id, r.target_entity_id,
       r.relationship_type, r.current_version,
       rv.label, rv.description, rv.data,
       r.created_at, r.created_by, r.updated_at, r.is_deleted,
       sev.name, tev.name
FROM relationships r
JOIN relationship_versions rv ON r.id = rv.relationship_id
  AND r.current_version = rv.version
LEFT JOIN entities se ON r.source_entity_id = se.id
LEFT JOIN entity_versions sev ON se.id = sev.entity_id
  AND se.current_version = sev.version
LEFT JOIN entities te ON r.target_entity_id = te.id
LEFT JOIN entity_versions tev ON te.id = tev.entity_id
  AND te.current_version = tev.version
WHERE r.is_deleted = 0
ORDER BY r.updated_at DESC
```

Return dict additions per row: `"source_entity_name": row[12] or ""`, `"target_entity_name": row[13] or ""`

Modify `get_relationship()` with the same JOIN pattern to also return entity names.

---

## C. Frontend: Type Definitions (`frontend/src/lib/types/api.ts`)

Add to `Relationship` interface:
- `source_entity_name?: string`
- `target_entity_name?: string`

---

## D. Frontend: Entity Detail Page (`frontend/src/routes/entities/[id]/+page.svelte`)

In the Relationships tab, replace the GUID fallback logic:

**Before:**
```svelte
{rel.source_entity_id === entity.id ? entity.name : rel.source_entity_id}
```

**After:**
```svelte
{rel.source_entity_id === entity.id ? entity.name : (rel.source_entity_name || rel.source_entity_id)}
```

Same pattern for target entity.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Entity GET returns `created_by_username` | GET /api/entities/{id} response includes `created_by_username` with admin username |
| Entity versions return `created_by_username` | GET /api/entities/{id}/versions each version has `created_by_username` |
| Model GET returns `created_by_username` | GET /api/models/{id} response includes `created_by_username` with admin username |
| Model versions return `created_by_username` | GET /api/models/{id}/versions each version has `created_by_username` |
| Relationship list returns entity names | GET /api/relationships?entity_id={id} items include `source_entity_name` and `target_entity_name` |
| Relationship GET returns entity names | GET /api/relationships/{id} response includes `source_entity_name` and `target_entity_name` |
| Frontend shows entity names in relationships | Relationships tab shows entity names instead of GUIDs for non-current entities |
| API backward compatibility | Existing fields unchanged; new fields are additive with defaults |

---

*This specification implements [ADR-034](../ADR-034-GUID-Username-Resolution.md).*
