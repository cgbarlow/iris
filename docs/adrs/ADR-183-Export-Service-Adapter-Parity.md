# ADR-183: Export service uses positional row indexing for adapter parity

Status: Accepted (2026-05-16)

## Context

Issue [#145](https://github.com/cgbarlow/iris/issues/145) — Phase 1 UAT
of the deployed v6.6.4 stack reported that the primary MCP path for
`render_diagram` failed with `HTTP 500 Internal Server Error`. The
documented Phase-1 fallback (`render_markdown` with a re-pasted body)
worked, so users still got their artefacts, but the headline path was
broken on every render call from a live MCP session.

`POST /api/export/diagram/{diagram_id}` and the other
`GET /api/export/*` bundle endpoints all flow through
`backend/app/export/service.py`, which fetches diagram / element /
package / set / collection rows and converts them to Pydantic
responses via helpers like `_row_to_diagram(row)`.

Every helper read columns by string key (`row["id"]`, `row["data"]`,
`row["notation"]`, …). That works on the SQLite adapter — the
`get_connection` helper sets `db.row_factory = aiosqlite.Row`, and
`aiosqlite.Row` supports both `row["col"]` and `row[0]`. It does **not**
work on the Supabase / asyncpg adapter: `SupabaseAdapter._execute_on`
returns an `_AsyncpgCursor` whose `_normalize_row(record)` packs each
asyncpg `Record` into a plain `tuple[Any, ...]` (so it can normalise
`datetime`, `date`, and `UUID` to SQLite-compatible strings). Tuples
only support integer indexing. Every `row["id"]` on Supabase raised
`TypeError: tuple indices must be integers or slices, not str`, which
FastAPI surfaced as a 500.

Every other service module (`app/diagrams/`, `app/sets/`,
`app/elements/`, `app/packages/`, …) already uses positional indexing
for exactly this reason — see `app/diagrams/service.py` lines 176–193.
The export service was the only outlier, which is why the bug only
showed up against Supabase production, not the SQLite test suite.

## Decision

**`app/export/service.py` must read every database row by positional
index, never by string key.** This matches the convention already in
use across the rest of the backend service layer.

In practice that means:

- `_row_to_element`, `_row_to_diagram`, `_row_to_package` use `row[0]`,
  `row[1]`, … to match the literal column order of `_ELEMENT_SELECT`,
  `_DIAGRAM_SELECT`, `_PACKAGE_SELECT`.
- Inline reads in `_fetch_set`, `_fetch_collection`,
  `build_collection_export`, `_fetch_elements_for_diagram`, and
  `_descendant_package_ids` also use positional indexing.
- The helper type annotations widen from `aiosqlite.Row` to `object`
  so the cross-adapter intent is visible at the signature.

## Why not give the Supabase adapter a Row-like wrapper

- Touching `_AsyncpgCursor` would change the shape of every existing
  call site in the codebase that already relies on tuple semantics.
  The whole codebase has already converged on positional indexing —
  the export service is the divergent caller, so fix the caller.
- A Row-like wrapper means carrying column-name metadata through the
  adapter for every query. asyncpg already gives us `Record.keys()`
  but threading that through the normalised-tuple path adds overhead
  to the hot read path for one outlier module's benefit.
- Positional indexing is the convention; codify it instead of
  introducing a second convention.

## Why not catch the `TypeError` in the renderer route

- Hiding the symptom doesn't fix the source. Every `GET /api/export/*`
  read endpoint would still throw on Supabase; we'd just relabel the
  500 as a 502 or similar.
- The structural fix is small (~10 lines of edits) and removes a
  whole class of bug.

## Consequences

- `backend/app/export/service.py` row reads converted to positional
  indexing.
- New regression test `backend/tests/test_export/test_service_tuple_rows.py`
  exercises `_row_to_diagram`, `_row_to_element`, `_row_to_package`
  with plain tuples (the Supabase row shape) so a future
  string-keyed regression fails locally without needing a Supabase
  connection.
- CHANGELOG `[6.6.5]`.
- Version bumps: mcp + frontend 6.6.4 → 6.6.5.

## Verification

- Failing test (`test_row_to_diagram_accepts_tuple_row`) reproduces
  the `TypeError` against pre-fix code.
- Post-fix: `uv run pytest tests/test_export/` — all 44 export tests
  pass (3 new tuple-row tests + 41 existing SQLite-backed tests).
- Manual smoke against deployed iris-api after rebuild: call
  `POST /api/export/diagram/{any-markdown-diagram-id}` with
  `{"format":"md"}` and confirm 200 + `web_url` artefact.

## See also

- [SPEC-183-A](specs/SPEC-183-A-Export-Service-Adapter-Parity.md)
- ADR-094 (database adapter)
- ADR-179 (renderer + artefact store) — the consumer surface affected
- Issue [#145](https://github.com/cgbarlow/iris/issues/145)
- Issue [#133](https://github.com/cgbarlow/iris/issues/133) Phase 1 UAT
