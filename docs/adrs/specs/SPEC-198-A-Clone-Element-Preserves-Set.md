# SPEC-198-A: Clone element preserves source set

Implements: [ADR-198](../ADR-198-Clone-Element-Preserves-Set.md)
Resolves: Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 1
Status: Living

## Invariant

For every code path that creates an element from another element
(clone), the new element's `set_id` equals the source's `set_id`.

Two paths today:

| Path | Surface | Behaviour |
|---|---|---|
| Batch clone | `POST /api/batch/elements/clone` | `batch_clone_elements` selects source `set_id` and re-inserts it. **Was already correct.** Regression test added in this PR. |
| Single clone (detail page) | `POST /api/elements` from `/elements/{id}` Clone button | Frontend body now includes `set_id: entity.set_id`. **Was the bug.** |

## Frontend shape

`frontend/src/routes/elements/[id]/+page.svelte`:

```ts
async function handleClone() {
  if (!entity) return;
  try {
    const created = await apiFetch<Element>('/api/elements', {
      method: 'POST',
      body: JSON.stringify({
        element_type: entity.element_type,
        name: `${entity.name} (Copy)`,
        description: entity.description ?? '',
        data: entity.data ?? {},
        set_id: entity.set_id,   // ← added
      }),
    });
    await goto(`/elements/${created.id}`);
  } catch (e) {
    error = e instanceof ApiError ? e.message : 'Failed to clone element';
  }
}
```

## Out of scope

Notation, metadata, package_id, and tags are not propagated.
Matches the batch path's existing behaviour. Filed for follow-up
if a user wants those preserved too.

## Acceptance criteria

1. Cloning an element from `/elements/{id}` produces an element
   whose `set_id` equals the source's `set_id`.
2. Cloning an element via the batch endpoint
   (`POST /api/batch/elements/clone`) produces a clone in the
   source's set (preserved invariant — backed by a new regression
   test).
3. The clone name remains `"{source.name} (Copy)"` on both paths.
4. No other fields change behaviour.

## Tests

Frontend — `frontend/tests/unit/elementClonePreservesSet.test.ts`:

1. `handleClone` still POSTs to `/api/elements`.
2. Body includes `set_id: entity.set_id`.
3. Basic fields (element_type, name with `(Copy)`, data) still
   present.

Backend — `backend/tests/test_batch/test_clone_preserves_set.py`:

1. `test_clone_inherits_source_set_id` — create a set, create an
   element in that set, batch-clone it, list elements filtered by
   that set, assert both source and clone appear.

## Verification

```
.venv/bin/python -m pytest \
  backend/tests/test_batch/test_clone_preserves_set.py \
  backend/tests/test_batch/test_operations.py

cd frontend && npx vitest run tests/unit/elementClonePreservesSet.test.ts
```

Green. Manual smoke per ADR-198 verification section.
