# SPEC-097-A: Relationship Field Fix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-097-A |
| **ADR** | [ADR-097](../ADR-097-Entity-Relationship-Display-Fix.md) |
| **Status** | Draft |
| **Date** | 2026-03-22 |

---

## Overview

Fix the field name mismatch in `list_element_relationships_for_diagram()` that prevents entity-to-entity relationships from being displayed in the diagram Relationships tab.

## Root Cause

In `backend/app/package_relationships/service.py`, line 113:

```python
eid = node_data.get("elementId")  # ← incorrect field name
```

The canonical field name used everywhere else in the codebase is `entityId`:

| File | Usage |
|------|-------|
| `frontend/src/lib/types/canvas.ts:85` | `entityId?: string` in `CanvasNodeData` |
| `backend/app/diagrams/service.py:347` | `node["data"].get("entityId")` |
| `backend/app/diagrams/service.py:366` | `node["data"].get("entityId")` |
| `backend/app/import_sparx/service.py:587` | `"entityId": element_id` |
| `backend/app/elements/service.py:531` | `n["data"].get("entityId")` |
| `backend/app/seed/example_models.py` | `"entityId": eids.get(...)` (multiple) |

## Fix

Change line 113 of `backend/app/package_relationships/service.py`:

```python
# Before
eid = node_data.get("elementId")

# After
eid = node_data.get("entityId")
```

## Acceptance Criteria

1. `GET /api/diagrams/{id}/relationships` returns non-empty `element_relationships` when the diagram canvas contains entity nodes linked to elements that have relationships in the `relationships` table
2. The Relationships tab on the diagram page displays element relationships
3. Existing tests continue to pass
4. New test covers the fix: create elements with a relationship, create a diagram referencing those elements, verify the relationships endpoint returns them

## Test Plan

- New test file: `backend/tests/test_diagram_relationships.py`
- Test: create two elements, create a relationship between them, create a diagram with canvas nodes referencing those elements via `entityId`, call `GET /api/diagrams/{id}/relationships`, assert `element_relationships` contains the relationship
