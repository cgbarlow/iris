# ADR-200: Batch element create + update tools across REST, MCP, CLI

Status: Accepted (2026-05-18)
Related: [ADR-182](ADR-182-Surface-Parity-Discipline.md) (surface parity)

## Context

Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 6
— creating (or updating) a long list of elements via the
`create_element` MCP tool requires one tool call per item. For a
grocery-list-sized batch (10–50 items) this is slow,
context-burny, and noisy in the assistant's transcript.

The existing batch surface (`POST /api/batch/elements/*`) covers
clone / delete / set-membership / tag operations but stops short
of create and update. Adding them rounds out the bulk-ops
toolkit.

## Decision

Add `create_elements` and `update_elements` (plural) across all
three Iris surfaces, per Protocol §14 (surface parity, ADR-182).

### REST

- `POST /api/batch/elements/create` — body `{ elements: ElementCreateItem[] }`.
- `POST /api/batch/elements/update` — body `{ updates: ElementUpdateItem[] }`.

Both return a `BatchResultWithIds` envelope:

```json
{ "succeeded": N, "failed": M, "errors": ["Element at index 1: ..."], "ids": ["<uuid>", ...] }
```

Per-item failure isolation. One bad row gets reported as
`Element at index <i>: <reason>` and the rest of the batch
proceeds. The HTTP status stays 200 — the caller reads
`failed`/`errors` to decide.

Per-item update payload carries its own `element_id` +
`expected_version` (per-item optimistic concurrency). A stale
version surfaces as a per-item failure, not a whole-batch 409 —
this is the only sensible behaviour for batches, since one stale
row shouldn't reject the other 99.

### MCP

- `create_elements(elements: list[...])` — handler calls the REST
  endpoint and returns the response verbatim.
- `update_elements(updates: list[...])` — same.

Both tools accept a free-form `additionalProperties: True` schema
per-item so the MCP client can construct any subset of the
`create_element` / `update_element` fields without us re-stating
the full schema in the array item.

### CLI

- `iris create elements --from-json path.json` (or `--from-json -`
  for stdin).
- `iris update elements --from-json path.json`.

Payload format mirrors the REST body. JSON-only — no per-field
CLI flags. The shape can have dozens of fields per row; flags
would be unusable. Files / stdin are the natural input.

## Atomicity: per-item, not whole-batch

Two choices considered:

1. **Whole-batch transactional.** One DB transaction wraps every
   row; any failure rolls the lot back. *Skipped.*
2. **Per-item commit (chosen).** Each `create_element` /
   `update_element` call commits its own row. Failures are
   isolated.

Per-item is right for the actual use case (ingesting a long list
that the model assembled from a chat — most rows are
independent). Whole-batch atomicity would make the "one bad row
ruins everything" failure mode a lot worse, with no real
trade-off benefit: there's no consistency invariant across the
elements in a typical batch.

This matches the existing `batch_clone_elements` semantics —
loop, try, accumulate errors.

## Surface parity script

`scripts/check_surface_parity.py` tracks singular CRUD per entity
(`create_element`, `update_element` etc., scoped to
`/api/elements/`). The new endpoints live under `/api/batch/` and
the script's parser correctly ignores them as batch operations.

No script change required — the new tools are an additional
capability layer, not duplicate write paths for the existing
parity contract. Verified locally with `scripts/check_surface_parity.py`.

## Why not extend `create_element` to accept arrays

Considered. Polymorphic input (single object OR array). Rejected
because:

- Type signature gets uglier across all three surfaces.
- Clients have to handle two response shapes (single
  `ElementResponse` vs `BatchResultWithIds`).
- Surface parity check treats `create_element` and
  `create_elements` as distinct verbs anyway; adding a sibling
  tool is structurally cleaner.

Singular `create_element` stays as-is for callers that only need
to create one.

## Why no batch delete with this PR

`batch_delete_elements` already exists (`/api/batch/elements/delete`).
Scope of this issue was create + update; delete was already
covered.

## Consequences

- `backend/app/batch/models.py` — new `BatchElementCreateItem`,
  `BatchElementsCreate`, `BatchElementUpdateItem`,
  `BatchElementsUpdate`, `BatchResultWithIds`. Re-exports the
  `_UNSET` sentinel from `ElementUpdate`.
- `backend/app/batch/service.py` — new `batch_create_elements`
  and `batch_update_elements`, each looping over the input list
  and accumulating failures.
- `backend/app/batch/router.py` — two new endpoints wired to the
  service functions.
- `backend/tests/test_batch/test_batch_create_update_elements.py`
  — new pytest module, 7 cases (happy path, partial failure,
  empty payload validation, auth, batch update, version
  conflict isolation, empty update validation).
- `mcp/src/iris_mcp/tools.py` — two new `Tool` registrations
  (`create_elements`, `update_elements`) + two new handlers
  (`_create_elements`, `_update_elements`).
- `cli/src/iris_cli/main.py` — two new commands (`iris create
  elements`, `iris update elements`) plus `_load_batch_payload`
  helper.
- CHANGELOG `[6.10.0]`. Minor bump — new feature surface.
- No backend migration, no schema change. Pure code addition on
  top of the existing element schema.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_batch/
.venv/bin/python scripts/check_surface_parity.py  # ✅ Parity clean
```

Manual smoke:
```
# Create 3 elements
echo '{"elements":[{"element_type":"component","name":"A","data":{}},
                  {"element_type":"component","name":"B","data":{}},
                  {"element_type":"component","name":"C","data":{}}]}' \
  | iris create elements --from-json -

# Or from an MCP client, invoke create_elements with the same payload.
```

## See also

- Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 6.
- [ADR-182](ADR-182-Surface-Parity-Discipline.md) — the surface
  parity discipline this PR satisfies.
- Existing batch operations: `backend/app/batch/router.py`,
  `backend/app/batch/service.py`.
