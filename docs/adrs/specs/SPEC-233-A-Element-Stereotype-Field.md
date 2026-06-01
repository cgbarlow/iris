# SPEC-233-A: Element stereotype field

Implements **[ADR-233](../ADR-233-Element-Stereotype-Field.md)**.

## Backend
- `backend/app/elements/models.py`: `ElementResponse` gains `stereotype: str | None = None`.
- `backend/app/elements/service.py`: in `get_element` and `list_elements`, after parsing `metadata`, set `"stereotype": (metadata or {}).get("stereotype")`.

## Frontend
- `frontend/src/lib/types/api.ts`: `Element` gains `stereotype?: string | null`.
- `frontend/src/routes/elements/[id]/+page.svelte`: show a stereotype chip in the header next to the element-type/notation chips (the detail-row already exists). Optionally render it on the tree element label.

## Acceptance
- AC1 `GET /api/elements/{id}` and the list endpoint return `stereotype` derived from `metadata.stereotype`; `null` when absent.
- AC2 element header shows the stereotype chip for an imported capability.
- No schema change; reads only (no surface-parity impact).
