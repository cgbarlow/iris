# SPEC-176-A: Generic creation-cascade shared base prompts

ADR: [ADR-176](../ADR-176-Cascade-Shared-Base-Prompts.md)

## Summary

INSERT three new rows into `ai_creation_prompts` at `layer='base'`, `purpose='creation_format'`, `notation=NULL`, `diagram_type=NULL` with `display_order` 1 / 2 / 3. UPDATE `creation-doview-notation-v1` to defer to the shared cascade. UPDATE `creation-outcomes-map-v1` to reference the shared citations prompt instead of restating the URL rule. Update `backend/app/seed/creation_prompts.py` to re-apply the three new rows + the two updated rows on every startup, matching the existing seed pattern.

## Schema

Existing table from m028 / m051 — no schema changes:

```sql
CREATE TABLE ai_creation_prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    purpose TEXT NOT NULL DEFAULT 'creation_format',
    layer TEXT NOT NULL,
    notation TEXT,
    diagram_type TEXT,
    prompt_text TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## Three new rows

| id | display_order | source-of-truth doc |
|---|---|---|
| `creation-cascade-shared-v1` | 1 | `docs/prompts/creation-cascade-shared.md` |
| `creation-cascade-citations-v1` | 2 | `docs/prompts/creation-cascade-citations.md` |
| `creation-cascade-destination-v1` | 3 | `docs/prompts/creation-cascade-destination.md` |

All three: `purpose='creation_format'`, `layer='base'`, `notation=NULL`, `diagram_type=NULL`, `is_active=1`, `created_by='system'`.

## Two updated rows

| id | Change |
|---|---|
| `creation-doview-notation-v1` | Remove the Stage 0 paste/upload guidance, default-name suggestion, skip-detail branching, destination guidance — defer to the shared cascade. Retain only DoView-specific methodology (This-Then, outcome phrasing, 13 drafting steps, slide ordering, entity types, edge types, color palette, layout rules). |
| `creation-outcomes-map-v1` | Remove the inline Sources rule. Add one line: "Source-reference elements (Sources subpage) follow the format in `creation-cascade-citations-v1`." |

## Composition order

The composer `backend/app/ai/creation.py:_build_layered_prompt` selects base-layer rows for the requested `purpose` ordered by `display_order` ASC, then notation rows, then diagram-type rows. Composed output for `(notation='doview', diagram_type='outcomes_map', purpose='creation_format')` is:

```
[base, display_order=0]   creation-base-v1               (existing — JSON output format)
[base, display_order=1]   creation-cascade-shared-v1     (new — conversation conventions)
[base, display_order=2]   creation-cascade-citations-v1  (new — citation discipline)
[base, display_order=3]   creation-cascade-destination-v1 (new — destination chooser)
[notation]                creation-doview-notation-v1    (updated — DoView methodology only)
[diagram_type]            creation-outcomes-map-v1       (updated — references citations)
```

For `(notation='bpmn', diagram_type=NULL, purpose='creation_format')`:

```
[base, display_order=0]   creation-base-v1
[base, display_order=1]   creation-cascade-shared-v1
[base, display_order=2]   creation-cascade-citations-v1
[base, display_order=3]   creation-cascade-destination-v1
[notation]                creation-bpmn-notation-v1      (existing — BPMN methodology)
```

This is the cross-notation generality proof — BPMN inherits the new shared rules without any BPMN-specific change.

## Migration (SQLite)

`backend/app/migrations/m058_cascade_ux_polish.py` (id verified next free at drafting time):

- INSERT OR IGNORE the three new rows with the bodies from the source-of-truth docs.
- UPDATE `creation-doview-notation-v1` setting `prompt_text` to the canonical refactored body (DoView methodology only).
- UPDATE `creation-outcomes-map-v1` setting `prompt_text` to the canonical body with the citation reference instead of the inline rule.
- All wrapped in defensive table-exists check (matching m053, m057 patterns).
- Idempotent — INSERT OR IGNORE on PK; UPDATE is a fixed body replace.

Register in `backend/app/startup.py:_initialize_sqlite` right after `m057_up(main)`.

## Migration (Supabase)

`backend/app/migrations/supabase/m062_cascade_ux_polish.sql` mirrors the SQLite migration. Same inserts and updates using PostgreSQL's `INSERT ... ON CONFLICT DO NOTHING` for the inserts.

## Seed update

`backend/app/seed/creation_prompts.py`:

- Add three module-level constants `CASCADE_SHARED_PROMPT`, `CASCADE_CITATIONS_PROMPT`, `CASCADE_DESTINATION_PROMPT` lifted verbatim from the three source-of-truth docs.
- Add three entries to `_EXPANSION_ROWS` for the new base-layer rows. `layer='base'`, `notation=None`, `diagram_type=None`, `display_order=1/2/3`.
- Update `DOVIEW_NOTATION_PROMPT` constant to the refactored body (DoView methodology only — no shared content).
- Add an `OUTCOMES_MAP_PROMPT` constant (the canonical body with the citation reference) and an UPDATE statement in `seed_creation_prompts` that applies it to `creation-outcomes-map-v1`.

The seed pattern (INSERT OR IGNORE then UPDATE) handles both fresh installs (migration inserts, seed overwrites with canonical) and existing deploys (seed UPDATE picks up changes without a new migration for future copy edits).

## Tests

### `backend/tests/migrations/test_m058_cascade_ux_polish.py` (new)

Five test functions:

1. `test_base_rows_present_after_migration` — apply migration to fresh SQLite, query `ai_creation_prompts WHERE layer='base' AND purpose='creation_format'`, assert all three new ids present with correct display_order.

2. `test_doview_notation_defers_to_shared` — query `creation-doview-notation-v1.prompt_text`, assert it does NOT contain the strings `"paste your own content"`, `"general knowledge"`, `"Skip detail review"`, `"save to Iris"` (these now live in the shared layer). Assert it DOES contain DoView-specific markers (`"This-Then"`, `"13 Drafting Steps"`, `"causal_link"`).

3. `test_outcomes_map_defers_to_citations` — query `creation-outcomes-map-v1.prompt_text`, assert it references `creation-cascade-citations-v1` and does NOT contain the strings `"raw https URL"` or `"Author/Org · Title"` (which now live in the citations layer).

4. `test_composed_doview_outcomes_map_contains_shared_sections` — call `build_creation_system_prompt(db, notation='doview', diagram_type='outcomes_map')`. Assert the returned body contains:
   - `"AskUserQuestion"` (from shared)
   - `"paste your own content"` (from shared)
   - `"Skip detail review"` (from shared)
   - `"Author/Org · Title · YYYY"` (from citations)
   - `"Save where?"` (from destination)
   - `"This-Then"` (from DoView notation)
   - `"Final column boxes: use final_outcome"` (from outcomes_map diagram_type)

5. `test_composed_bpmn_contains_shared_sections` — call `build_creation_system_prompt(db, notation='bpmn')`. Assert the body contains the same shared and destination strings as above (cross-notation generality proof). Assert it does NOT contain DoView-specific markers.

### Existing test compatibility

`test_outcomes_map_layout` (if present in `backend/tests/`) — verify the test still passes. The Outcomes Map prompt is shorter but should still cover layout expectations.

`backend/tests/test_seed_creation_prompts.py` (if present) — extend to assert the three new base-layer rows are present after `seed_creation_prompts(db)`.

## Source-of-truth docs

- [`docs/prompts/creation-cascade-shared.md`](../../prompts/creation-cascade-shared.md)
- [`docs/prompts/creation-cascade-citations.md`](../../prompts/creation-cascade-citations.md)
- [`docs/prompts/creation-cascade-destination.md`](../../prompts/creation-cascade-destination.md)

Each contains a "Content (paste this into the row's prompt_text field)" fenced block that is the canonical body. The migration and seed constants must match these blocks byte-for-byte (modulo unavoidable Python-string escaping). A drift between docs and code is a defect.

## Versioning

`backend/pyproject.toml`: 6.0.15 → 6.1.0. Minor bump — new conversational behaviour visible to every MCP user, no API surface removal.
`mcp/pyproject.toml`: matched 6.1.0.
`frontend/package.json`: matched 6.1.0.

## CHANGELOG

Add a `[6.1.0]` entry under Added (the three new shared base prompts) and Changed (DoView notation defers to shared, outcomes_map references citations).

## Acceptance criteria

- [ ] Migration applies cleanly to a fresh SQLite database.
- [ ] Migration applies cleanly to a database already at m057 (UPDATEs succeed).
- [ ] All three new base-layer rows present with the canonical bodies.
- [ ] `creation-doview-notation-v1` no longer contains shared-layer content.
- [ ] `creation-outcomes-map-v1` references `creation-cascade-citations-v1`.
- [ ] Composed `(doview, outcomes_map)` body contains the shared + citations + destination + DoView + outcomes_map sections.
- [ ] Composed `(bpmn, *)` body contains the shared + citations + destination + BPMN sections.
- [ ] `seed_creation_prompts` re-apply on a fresh start is idempotent and produces the same composed body.
- [ ] `pytest backend/tests/` green; `pytest mcp/tests/` green.
- [ ] Manual UAT 1: replay banana-monoculture, every cascade question uses AskUserQuestion, Q-Default-Name fires, Q-Skip-Detail fires, Q-Destination fires.
- [ ] Manual UAT 2: start a fresh BPMN cascade, same questions fire (cross-notation proof).
