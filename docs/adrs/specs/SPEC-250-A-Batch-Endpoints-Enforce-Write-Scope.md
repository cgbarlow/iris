# SPEC-250-A: Batch Endpoints Enforce Collection Write-Scope Per Item

Implements **[ADR-250](../ADR-250-Batch-Endpoints-Enforce-Write-Scope.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `backend/app/batch/service.py` | New `_require_writable(db, user, collection_id)`: calls `assert_write_allowed`, re-raising its `HTTPException` as `ValueError(detail)` so the item loop records a per-item error. Every batch function now takes keyword `user: dict` (replacing `deleted_by` / `cloned_by` / `modified_by` / `created_by` / `updated_by`; the actor id is `user["id"]`) and gates each item after its existence check, before any write. |
| `backend/app/batch/router.py` | Each endpoint passes `user=current_user`. The two `set` endpoints now bind `current_user` (previously `_current_user`, unused). |
| `backend/tests/test_authz/conftest.py`, `scope_helpers.py` | The scoped-user fixtures and helpers previously private to `test_collection_scope.py`, shared by both scope suites (DRY). |

Per-operation gates:

| Function | Gate(s) |
|----------|---------|
| `batch_delete_elements`, `batch_tags_elements`, `batch_clone_elements` | `collection_of_element(item)` |
| `batch_update_elements` | `collection_of_element(element_id)` |
| `batch_set_elements` | `collection_of_element(item)` and `collection_of_set(target set)` |
| `batch_create_elements` | `collection_of_set(resolve_effective_set(set_id, package_id))` |
| `batch_delete_diagrams`, `batch_tags_diagrams`, `batch_clone_diagrams` | `collection_of_diagram(item)` |
| `batch_set_diagrams` | `collection_of_diagram(item)` and `collection_of_set(target set)` |
| `batch_create_relationships` (ADR-249) | unchanged rule (`collection_of_element(source)`), now via the shared helper |

Error text per item keeps each function's existing prefix, for example
`Element <id>: Outside your collection write-scope` or
`Update at index <n>: Outside your collection write-scope`.

## 2. Tests (TDD)

`backend/tests/test_authz/test_batch_write_scope.py` (new). The setup has
collections A and B, admin-seeded elements and diagrams in each, and an
architect scoped to A. Each test sends a mixed batch (one A item, one B item)
and asserts: exactly one success and one failure, the failure carries the
scope error, and the B item is unchanged (not deleted, retagged, renamed,
cloned into B or moved).

- Elements: `delete`, `clone`, `tags`, `set` (move out of scope and pull in
  from out of scope), `create`, `update`.
- Diagrams: `delete`, `clone`, `tags`, `set` (both directions).
- Bypass: an unscoped architect and an admin still write across collections.

Red before the change: all 11 scoped tests failed (the scoped user's writes
into B succeeded). Green after. The existing `tests/test_authz`,
`tests/test_batch` and `tests/test_relationships` suites stay green.

## 3. Acceptance criteria

- A scoped user cannot write outside their scope through any `/api/batch/*`
  endpoint.
- Out-of-scope items fail individually. The rest of the batch proceeds.
- Unscoped users and admins are unaffected.
