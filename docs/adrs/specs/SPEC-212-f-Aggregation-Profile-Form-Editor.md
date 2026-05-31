# SPEC-212-f: Aggregation profile form-editor (JSON-free authoring)

Implements: extension of [ADR-212](../ADR-212-Aggregation-Profiles-And-Engine.md). Builds on [SPEC-212-d](./SPEC-212-d-Aggregation-Profile-Editor.md) (v1 JSON-textarea editor) and [SPEC-212-e](./SPEC-212-e-Aggregation-Profile-Editor-Polish.md) (clone-from-existing). Addresses the "future v6.26+" list in SPEC-212-d §7: form-based fields, attribute-path autocomplete, and inline preview.

## 1. Goal

A non-technical user can create or modify an aggregation profile end-to-end **without seeing JSON**. The JSON textarea remains as an opt-in "Advanced" escape hatch for power users and for fields the form doesn't surface yet.

## 2. Four UX additions

The work is grouped as four orthogonal additions, all landing together:

| # | Addition | Component |
|---|---|---|
| A | Lift flat output fields to form widgets | `AggregationProfileEditor.svelte` (in place) |
| B | `line_format` chip composer with live preview | `LineFormatComposer.svelte` (new child) |
| C | Traversal wizard with attribute-path picker | `TraversalBuilder.svelte` + `AttributePathPicker.svelte` (new children) |
| E | Template gallery on "New profile" | `AggregationTemplateGallery.svelte` (new child) |

The four child components compose. The editor owns the draft state; children are pure presentation bound via Svelte 5 `$bindable` props.

## 3. Backend surface — inline `profile_data` on `/run`

The live-preview pane (Option B) needs to run an unsaved draft. Extend `AggregationRunRequest`:

```python
class AggregationRunRequest(BaseModel):
    profile_id: str | None = Field(default=None, min_length=1)
    profile_data: ProfileData | None = None
    source_diagram_id: str = Field(min_length=1)
```

Exactly-one-of (`profile_id` XOR `profile_data`) is enforced in the route handler, returning a `400` with a clear message. The engine's `run()` gains an optional `profile_data` kwarg; when provided it bypasses both ADR-227 cache layers (no stable key to revalidate against) and feeds the inline `ProfileData` straight into `_run_uncached`.

Mirrored in:

- MCP `aggregate` tool — `profile_id` becomes optional, `profile_data: object` added.
- CLI `iris aggregate` — `--profile-data <path|-> ` accepts a file path or stdin.

Surface parity (Protocol §14) stays clean — `scripts/check_surface_parity.py` passes unchanged.

## 4. Helpers — single source of truth for form ↔ JSON

`frontend/src/lib/components/aggregationProfileHelpers.ts` exposes pure functions that all four child components share (DRY §13):

- `readOutputFields(profileData) → OutputFields` / `patchOutputFields(profileData, fields)` — Option A round-trip.
- `readTraversalFields(profileData) → TraversalFields` / `patchTraversalFields(profileData, fields)` — Option C round-trip.
- `assembleProfileData(output, traversal)` — assembles a full `profile_data` for save / preview.
- `buildDraftFromTemplate(seed)` / `buildBlankDraft()` — Option E seed → form-fields hydration.
- `insertAtCursor(text, cursor, insertion)` — Option B chip insertion.
- Enum constants (`TOKEN_TYPES`, `SORT_MODES`, `AGGREGATION_FNS`) and `LINE_FORMAT_PLACEHOLDERS` — mirror backend Pydantic literals. Tests guard drift.

The Pydantic backend remains the validation source of truth; the frontend constants only populate dropdowns. A new value added backend-side requires a one-line addition here (and the round-trip test will fail loudly if patterns diverge).

## 5. Option A — lifted output fields

`AggregationProfileEditor.svelte` renders an "Output" section above the JSON textarea with:

- `aggregation_fn` — select (Sum / Count)
- `group_by` — text input + helper showing common path shapes
- `sort_groups`, `sort_items_within_group` — selects
- `show_per_source_breakdown` — checkbox; reveals `breakdown_format` input
- `include_provenance` — checkbox (existing, kept in place)

Empty `group_by` normalises to `null` so the engine treats it as ungrouped. The form patches its values into a draft `profile_data` object that mirrors what would be POSTed.

## 6. Option B — `line_format` chip composer + live preview

`LineFormatComposer.svelte`:

- Single-line text input + a row of clickable placeholder chips: `{element.name}`, `{element.id}`, `{sum_value}`, `{bucket}`, `{bucket_spaced}`. Clicking a chip inserts it at the input's cursor (`insertAtCursor` helper).
- Live-preview pane: when `sourceDiagramId` is supplied, debounce-call (400 ms) `POST /api/aggregation/run` with the inline `profile_data` and show the first 5 rendered lines. Validation failures and source-not-found are rendered as inline error chips, not blocking.
- When no source is supplied (globals authoring), the preview pane is replaced by a one-line "Live preview requires a source diagram" notice.

The placeholder catalogue lives in `aggregationProfileHelpers.LINE_FORMAT_PLACEHOLDERS` so docs and composer never drift.

## 7. Option C — traversal wizard + path picker

`TraversalBuilder.svelte` renders two `<details open>` sections:

- **Source container (optional)**: "These items live inside a parent container" checkbox; when on, shows the outer token-type select and (optional) multiplier sub-form (numerator override path + divisor path + default multiplier).
- **Inner items**: token-type select + value path picker + bucket path picker + `skip_blank_values` checkbox.

`AttributePathPicker.svelte` is a new lightweight picker that:

- Hits `/api/elements/{id}/data-tree` (the same endpoint `SmartMarkdownSlashPicker` uses; that endpoint is the **single source of truth** for the data-tree shape — both consumers depend on it, no logic duplication).
- Drills via the `dict.keys` / `list_of_named.names` / `list.length` descriptor returned by the endpoint.
- Emits a path string only (e.g. `attributes/Quantity/type`) — not the full `{{element:UUID:attr:…}}` smart-markdown token the slash picker produces.
- Falls back to a plain text input when no `exampleElementId` is supplied (globals authoring path).

**Out of scope here**: refactoring `SmartMarkdownSlashPicker` itself to consume `AttributePathPicker` internally. The slash picker is deeply intertwined with browse-mode and stamps; that refactor is a separate, higher-risk change. The two pickers share the backend endpoint, which is what DRY actually requires — the *logic* (walking the data tree) lives in one place (the server), with two UI consumers tuned for different jobs.

## 8. Option E — template gallery

`AggregationTemplateGallery.svelte` replaces the blank-form default when a user clicks "New profile":

- Card grid (`auto-fill` / `minmax(220px, 1fr)`, mirroring `EntityImagesEditor`'s grid pattern — DRY §13).
- "Blank" card first; then one card per seeded global profile (Shopping list, Sprint points rollup, Time tracker rollup, Expense report, Reading log rollup — from `m077_seed_global_aggregation_profiles.py`).
- Each card shows: name, description, and a truncated `line_format` preview.
- Selecting a card pre-populates Option A's form fields and Option C's wizard via `buildDraftFromTemplate`. The user only sees JSON if they open Advanced.

The legacy "+ Clone from existing" button remains alongside the gallery as a secondary action — it still surfaces in-scope user profiles + globals in a flat list for users who want to clone something they've previously customised.

## 9. Save semantics

- Default path (Advanced closed): form fields are authoritative. Save serialises `assembleProfileData(draftOutput, draftTraversal)` and posts it.
- Advanced open: JSON textarea is authoritative. Save runs `JSON.parse(draftJson)` and posts that. JSON syntax errors keep the editor open with an inline message.
- The Advanced disclosure opening also syncs the JSON from the current form state (so the user sees the JSON the form would have produced, with their edits as the starting point).

## 10. Genericness invariant (ADR-214)

All new copy + placeholder text passes `scripts/check_aggregation_genericness.py`. The aggregation feature stays domain-neutral end-to-end — placeholders show structural examples (`attributes/<Name>/type`, `data.<field>`), never food/sprint/expense terminology.

## 11. Tests

- `frontend/tests/unit/aggregationProfileHelpers.test.ts` — 29 tests covering read/patch round-trips, default fallbacks, empty-string normalisation, blank-draft validity, template-clone draft construction, chip-insert cursor math, and inline-run body shape. Pure-function tests per repo convention (no component renders).
- `frontend/tests/unit/aggregationProfileEditor.test.ts` — existing 13 tests intact (request body shapes, list filter logic, clone draft construction).
- `backend/tests/test_aggregation/test_inline_profile_run.py` — 7 tests covering happy path, ephemerality (no row created), 400 on both/neither, 422 on malformed inline `profile_data`, 404 on missing source, and backwards-compat for the saved-`profile_id` path.

## 12. Files touched

| Path | Change |
|---|---|
| `backend/app/aggregation/models.py` | `AggregationRunRequest` accepts optional `profile_data` |
| `backend/app/aggregation/routes.py` | Route handler enforces exactly-one-of + forwards `profile_data` |
| `backend/app/aggregation/engine.py` | `run()` accepts optional `profile_data`; inline path bypasses cache |
| `mcp/src/iris_mcp/tools.py` | `aggregate` tool gets optional `profile_data` arg |
| `cli/src/iris_cli/main.py` | `iris aggregate --profile-data <path|->` flag |
| `frontend/src/lib/components/aggregationProfileHelpers.ts` (new) | Shared pure helpers |
| `frontend/src/lib/components/AggregationProfileEditor.svelte` | Orchestrator — composes the four children |
| `frontend/src/lib/components/LineFormatComposer.svelte` (new) | Option B |
| `frontend/src/lib/components/TraversalBuilder.svelte` (new) | Option C |
| `frontend/src/lib/components/AttributePathPicker.svelte` (new) | Option C — path picker |
| `frontend/src/lib/components/AggregationTemplateGallery.svelte` (new) | Option E |
| `frontend/tests/unit/aggregationProfileHelpers.test.ts` (new) | Helpers tests |
| `backend/tests/test_aggregation/test_inline_profile_run.py` (new) | Inline-run tests |
| `docs/adrs/specs/SPEC-212-b-*.md` | Note inline engine path |
| `docs/adrs/specs/SPEC-212-c-*.md` | Note new run-endpoint field + parity mirrors |

## 13. Follow-ups (not in this spec)

- Refactor `SmartMarkdownSlashPicker` to consume `AttributePathPicker` internally (would eliminate two slightly-different drill UIs, but is high-risk without a dedicated test pass).
- Schema-driven form rendering (Option D from the planning conversation): derive the form from `ProfileData.model_json_schema()` exported via a new `/api/aggregation/profile-schema` endpoint. Becomes attractive once the custom widgets here are stable.
- Joint "create profile + paired element template" wizard tying ADR-211 into the gallery cards.
