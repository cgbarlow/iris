# ADR-198: Cloning an element preserves its source's set

Status: Accepted (2026-05-18)

## Context

Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 1
— the user reported that cloning an element did not put the clone
in the same set as the original. Plan-time research suggested
this might be a no-op (the backend's `batch_clone_elements` reads
and re-uses the source's `set_id`, see
`backend/app/batch/service.py:308,331`). Reproduce-first turned up
a real bug — but in a different code path.

### Two clone paths

1. **Batch clone** — `POST /api/batch/elements/clone`, called
   from the elements list page's bulk-action toolbar
   (`frontend/src/routes/elements/+page.svelte:223-234`). Backend
   `batch_clone_elements` selects `e.set_id` from the source and
   passes it back in the INSERT. **Correct.**
2. **Single-element clone** — the "Clone" button on the element
   detail page (`/elements/{id}`,
   `frontend/src/routes/elements/[id]/+page.svelte:320-336`).
   Sends `POST /api/elements` with only `element_type`, `name`,
   `description`, `data` — **no `set_id`**. The backend's
   `create_element` falls back to `DEFAULT_SET_ID` when the body
   omits `set_id`, so the clone lands in the default set rather
   than the source's. **The bug.**

The user's clone button on a per-element detail page hit path #2;
the symptom matched their report exactly.

## Decision

`handleClone` in
`frontend/src/routes/elements/[id]/+page.svelte` includes
`set_id: entity.set_id` in the POST body. The fix is intentionally
narrow — `set_id` only, matching the field the issue calls out.
Other attributes (`notation`, `metadata`, `package_id`, tags) are
left to follow-up if the user reports they should also propagate;
this matches the batch path, which also doesn't copy those fields
into the clone today.

We also add a backend regression test
(`backend/tests/test_batch/test_clone_preserves_set.py`) that
locks in the batch-path invariant explicitly — the existing
`test_clone_elements` only asserts the clone name appears in the
list, not which set it lives in.

## Why not generalise the clone to copy everything

The existing batch clone path is the historical "shallow copy"
shape (element_type + set_id + name + description + data + tags).
The user reported a narrow problem ("same set"); the surgical fix
keeps the behaviour consistent across both paths without expanding
clone semantics in a UAT patch release. If the user wants notation
/ metadata / package_id preserved, that's an ADR-198 follow-up.

## Why not move the single-clone path through `batch_clone_elements`

Reasonable suggestion — eliminates the duplication and the bug at
the same time. Skipped for this PR because (a) the batch endpoint
returns a `BatchResult` envelope that the detail-page UX would
have to unwrap, and (b) it would change the response shape that
`apiFetch<Element>` expects, requiring a typed wrapper change.
Bigger blast radius than a one-line body addition. Filed as a
candidate refactor; not done here.

## Consequences

- `frontend/src/routes/elements/[id]/+page.svelte:320-336` —
  `handleClone` includes `set_id: entity.set_id` in the POST body.
- `frontend/tests/unit/elementClonePreservesSet.test.ts` — new
  static-parser test (3 assertions).
- `backend/tests/test_batch/test_clone_preserves_set.py` — new
  pytest module, 1 case, locks in the batch-path invariant.
- No backend code change; no migration; no MCP / CLI changes.
- CHANGELOG `[6.8.7]`.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_batch/test_clone_preserves_set.py backend/tests/test_batch/test_operations.py
cd frontend && npx vitest run tests/unit/elementClonePreservesSet.test.ts
```

All green. Manual smoke: navigate to an element in a non-default
set, click "Clone", confirm the new element appears in the same
set's listing.

## See also

- Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 1.
- Batch clone backend: `backend/app/batch/service.py:295-364`.
