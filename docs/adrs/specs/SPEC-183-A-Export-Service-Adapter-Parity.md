# SPEC-183-A: Export service uses positional row indexing

ADR: [ADR-183](../ADR-183-Export-Service-Adapter-Parity.md)

## Summary

Convert every row-column read in `backend/app/export/service.py` from
string-key (`row["col"]`) to positional (`row[N]`) indexing, matching
the convention already in use across the rest of the backend service
layer. Add a regression test that exercises the row helpers with
plain-tuple inputs so the SQLite-only test suite would catch the
defect a future maintainer would otherwise reintroduce.

## Touched files

### `backend/app/export/service.py`

- `_row_to_element(row)` → all 11 columns indexed by position
  (matches `_ELEMENT_SELECT` column order).
- `_row_to_diagram(row)` → all 12 columns indexed by position
  (matches `_DIAGRAM_SELECT` column order).
- `_row_to_package(row)` → all 9 columns indexed by position
  (matches `_PACKAGE_SELECT` column order).
- `_fetch_elements_for_diagram` inline `linked` comprehension —
  positional `(row[0], row[1])` for the `(id, data)` tuple.
- `_fetch_set` inline `SetResponse(...)` build — positional.
- `_fetch_collection` inline `CollectionResponse(...)` build — positional.
- `build_collection_export` `set_ids` comprehension — positional.
- `_descendant_package_ids` `children` comprehension — positional.

Type annotations on the three `_row_to_*` helpers widen from
`aiosqlite.Row` to `object` so the cross-adapter intent is visible at
the signature. A short comment notes that positional indexing works
on both `aiosqlite.Row` (SQLite) and plain `tuple` (Supabase via
`_AsyncpgCursor._normalize_row`).

### `backend/tests/test_export/test_service_tuple_rows.py` (new)

Three unit tests exercise `_row_to_diagram`, `_row_to_element`, and
`_row_to_package` with a plain tuple matching each SELECT's column
order. Pre-fix these tests raise `TypeError`; post-fix they pass.
The tests do not require a database connection — they are pure
function tests against the row-conversion helpers.

## Out of scope

- The Supabase adapter's row-normalisation strategy
  (`_normalize_row → tuple`) is not changed. ADR-183 documents why
  fixing the caller is preferred to changing the adapter.
- Other services already use positional indexing; no audit pass is
  required.

## Verification

- `uv run pytest tests/test_export/test_service_tuple_rows.py` — new
  tests pass.
- `uv run pytest tests/test_export/` — all 44 tests pass (no
  regression in the SQLite-backed integration tests).
- Manual smoke against the deployed iris-api once v6.6.5 ships:
  step 6 / Phase 1 of `docs/issue-133-deploy-verification.md` —
  `POST /api/export/diagram/{any-markdown-diagram-id}` with
  `{"format":"md"}` must return 200 + an artefact `web_url`.
