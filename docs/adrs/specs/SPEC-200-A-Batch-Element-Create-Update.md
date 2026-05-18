# SPEC-200-A: Batch element create + update

Implements: [ADR-200](../ADR-200-Batch-Element-Create-Update-Tools.md)
Resolves: Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 6
Status: Living

## Surfaces

### REST

```
POST /api/batch/elements/create
Body: { "elements": [ ElementCreateItem, ... ] }   // 1..100 items
Response 200: { succeeded: int, failed: int, errors: string[], ids: string[] }
Response 422: empty array / payload shape violation
Response 401: not authenticated

POST /api/batch/elements/update
Body: { "updates": [ ElementUpdateItem, ... ] }    // 1..100 items
Response 200: { succeeded: int, failed: int, errors: string[], ids: string[] }
Response 422: empty array
Response 401: not authenticated
```

`ElementCreateItem` mirrors `ElementCreate` with all fields
optional at the model boundary (failure surfaces per-item, not
whole-batch):

```ts
{
  element_type?: string,
  name?: string,
  description?: string | null,
  data?: object,
  set_id?: string | null,
  package_id?: string | null,
  metadata?: object | null,
  notation?: string
}
```

`ElementUpdateItem`:

```ts
{
  element_id: string,            // required
  expected_version: int,         // required (per-item optimistic concurrency)
  name: string,                  // required, 1..255 chars
  description?: string | null,
  data?: object,
  change_summary?: string | null,
  metadata?: object | null,
  package_id?: string | null     // tri-state: omit / null / uuid (via _UNSET sentinel)
}
```

### MCP

```
create_elements(elements: list[<object>])
update_elements(updates: list[<object>])
```

Per-item schema is `additionalProperties: true` — the MCP client
constructs items matching the REST shapes. Handlers POST the
input verbatim to `/api/batch/elements/create` and
`/api/batch/elements/update` respectively and return the response
JSON.

### CLI

```
iris create elements --from-json <path|->
iris update elements --from-json <path|->
```

JSON-only input (per-field flags would be unusable across N rows
with up to 8 fields each). Reads from a file path or stdin (`-`).
Validates that the parsed payload is `{ "elements": [...] }` /
`{ "updates": [...] }` before posting.

## Behaviour

- **Per-item failure isolation.** Each item is wrapped in
  `try/except`. Failures accumulate into `errors` as
  `"Element at index <i>: <reason>"` / `"Update at index <i>: <reason>"`.
- **Version conflicts on update** surface as a per-item failure
  (the singular `update_element` returns `None` on stale version;
  the batch translates that into a `Version conflict (expected N)`
  error string).
- **Atomicity.** Per-item commit. No whole-batch transaction.
  Matches `batch_clone_elements` semantics.
- **Limits.** 1 ≤ items ≤ 100 per call (mirrors the
  `BatchIds` cap). Larger batches paginate client-side.

## DRY / surface parity

The new endpoints live under `/api/batch/` rather than
`/api/elements/`. The surface parity script
(`scripts/check_surface_parity.py`) tracks singular CRUD per
entity and correctly does not require `create_elements` /
`update_elements` as new parity entries — they're an additional
capability layer, not duplicate write paths. The MCP and CLI
sides are nevertheless added for **surface symmetry within the
batch capability** so the three-surface rule holds for the new
tools too.

## Tests

Backend — `backend/tests/test_batch/test_batch_create_update_elements.py`:

1. `test_create_three_elements_in_one_call` — happy path, 3
   items, all succeed, IDs returned, items visible in subsequent
   list.
2. `test_partial_failure_isolated_per_item` — 3 items, middle
   one invalid (`element_type=""`); 2 succeed, 1 fails with
   index-tagged error.
3. `test_empty_elements_returns_422` — empty array rejected at
   the validation layer.
4. `test_requires_auth` — unauthenticated POST returns 401.
5. `test_update_two_elements_in_one_call` — happy path, both
   reflect new names on subsequent GETs.
6. `test_version_conflict_isolated_per_item` — bump one element's
   version out from under the batch via a singular PUT; the
   batch update sees that item fail (version conflict) but the
   other succeeds.
7. `test_empty_updates_returns_422` — empty array rejected.

Plus parity check:

```
.venv/bin/python scripts/check_surface_parity.py
```

Must report `✅ Parity clean`.

## Acceptance criteria

1. A single REST POST creates N elements (1 ≤ N ≤ 100), returns
   per-item success/failure breakdown and the IDs of the
   created items.
2. A single REST POST updates N elements with per-item
   optimistic concurrency; one stale version doesn't fail the
   other items.
3. The MCP `create_elements` / `update_elements` tools accept the
   same payload shape and return the same envelope.
4. The CLI `iris create elements --from-json` / `iris update
   elements --from-json` round-trips the same payload from a file
   or stdin.
5. `scripts/check_surface_parity.py` stays green.
6. No regression to existing `create_element` / `update_element`
   singulars across any surface.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_batch/
.venv/bin/python scripts/check_surface_parity.py
.venv/bin/python -c "from iris_cli import main; print('OK')"
```

All green / OK. Manual smoke per ADR-200 verification section.
