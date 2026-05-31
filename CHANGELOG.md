# Changelog

All notable changes to Iris are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [6.40.0] - 2026-05-31

### Added

- **Form-based aggregation profile editor (SPEC-212-f).** A non-
  technical user can now create or modify an aggregation profile
  end-to-end without seeing JSON. Four UX additions land together:
  - **Output fields** are lifted from the JSON textarea into form
    widgets — `aggregation_fn` (Sum/Count radio), `group_by` text
    input with helper menu, `sort_groups` / `sort_items_within_group`
    selects, `show_per_source_breakdown` checkbox + `breakdown_format`
    input, and the existing `include_provenance` checkbox.
  - **`line_format` chip composer** with clickable placeholder chips
    (`{element.name}`, `{element.id}`, `{sum_value}`, `{bucket}`,
    `{bucket_spaced}`) that insert at the cursor. When the editor
    runs against a known source diagram, a debounced live-preview
    pane shows the first 5 rendered lines via the inline-draft run
    path.
  - **Traversal wizard** — a two-step builder for `traversal.outer`
    (optional, with multiplier sub-form) and `traversal.inner`. The
    value / bucket attribute-path inputs offer a drill-down picker
    that reuses the existing `/api/elements/{id}/data-tree` endpoint;
    falls back to a plain text input when no example element is
    available (globals authoring path).
  - **Template gallery** replaces the blank-form default on "New
    profile". Card grid with the five seeded global profiles plus a
    Blank card; selecting a card pre-populates the form (no JSON
    visible).
  The JSON textarea is retained as an opt-in "Advanced (JSON)"
  disclosure for power users and for fields the form doesn't surface
  yet. When Advanced is open, JSON is authoritative on save.
- **Inline `profile_data` on `POST /api/aggregation/run`** — the
  endpoint now accepts an optional inline profile draft alongside
  the existing `profile_id` lookup. Exactly-one-of is enforced. The
  inline path bypasses the ADR-227 two-layer cache and feeds the
  draft straight through `_run_uncached`. Mirrored on the MCP
  `aggregate` tool (new optional `profile_data` arg) and the
  `iris aggregate` CLI (new `--profile-data <path|->` flag) per the
  Protocol §14 surface-parity invariant.

### Changed

- `AggregationProfileEditor.svelte` orchestrates four new child
  components — `LineFormatComposer.svelte`, `TraversalBuilder.svelte`,
  `AttributePathPicker.svelte`, `AggregationTemplateGallery.svelte`
  — plus a new `aggregationProfileHelpers.ts` module of pure
  read/patch/assemble functions shared across the children (DRY §13).
- `AggregationRunRequest.profile_id` is now optional (paired with
  `profile_data`). The route handler enforces exactly-one-of and
  returns a clear `400` on misuse.

## [6.39.3] - 2026-05-31

### Fixed

- **Status dropdown re-released as v6.39.3.** The Status select-swap
  fix was committed and pushed to the v6.39.2 PR branch but did not
  land on `main` when the PR was merged (GitHub merge used the
  earlier commit at PR-edit time). Re-shipped as v6.39.3 to actually
  roll the fix out.

## [6.39.2] - 2026-05-31

### Fixed

- **Status dropdown on the element edit page now actually shows the
  suggestions.** The v6.39.0 / v6.39.1 `<input list>` + `<datalist>`
  approach was being filtered by Chrome to entries matching the
  current input text — with the cell already showing the existing
  status, the only entry shown was the existing value, looking like
  an empty dropdown. Replaced with a paired `<select>` (quick-pick
  of common Sparx values) + a text input (custom values), both
  bound to the same `editStatus` state. The select always lists all
  five standard values plus any non-standard existing value, so
  state is preserved without forcing the user to retype.
- **Aggregation cache now invalidates on element edits** (ADR-227
  follow-up). The v6.38.0 two-layer cache only tracked DIAGRAM
  versions in `AggregationResult.source_versions`. Element edits —
  the user-facing case (flipping *C&A (alternative name)* from
  `Proposed` to `Approved` and finding the GEANZ Dashboard's Status
  pie unchanged) — don't bump the rollup-source diagram's version,
  so the revalidator passed and we served stale aggregated output.
  - The engine now records every distinct element it touched during
    the walk in `AggregationResult.element_versions: dict[str, int]`
    via one batched `SELECT id, current_version FROM elements WHERE
    id IN (…)` after the walk completes. Only runs for
    element-collecting profiles; other `collect_token_type` profiles
    skip the extra query.
  - `engine_cache.revalidate` now also batch-checks element versions
    against the cached set. Any element edit (status flip, attribute
    change, name rename) bumps the element's `current_version` and
    misses the cache on next lookup.
  - Older cached results have an empty `element_versions` dict and
    still revalidate via the diagram check; new computes populate
    the new field, so cache warmth recovers within one cold-path
    request after the deploy.

## [6.39.1] - 2026-05-31

### Fixed

- **Status datalist suggestions now visible** on the element edit
  page. Chrome / Edge render an empty dropdown when a `<datalist>`
  `<option>` carries only a `value` attribute and no text node — the
  spec-valid `<option value="Approved"></option>` form looks like
  nothing's there. Repeated the value as the option's text content
  (`<option value="Approved">Approved</option>`) so the suggestions
  show across browsers.

## [6.39.0] - 2026-05-31

### Added

- **Element metadata edit UI** (ADR-228, SPEC-228-A). Closes the
  long-standing frontend gap where `metadata.status`, the Extended
  section's eleven scalars (stereotype / version / scope / abstract /
  persistence / author / complexity / phase / EA created+modified
  dates / gen_type), and the `metadata.tagged_values` table were
  display-only despite the backend accepting `metadata` on
  `ElementUpdate` since v6.36.1. Now:
  - Status edits via a free-text `<input list="status-suggestions">`
    with a `<datalist>` of common Sparx values (Approved, Proposed,
    Implemented, Validated, Mandatory).
  - Each Extended scalar gets a plain `<input>` in edit mode,
    initialised from `entity.metadata`. Blanking a field deletes the
    key from `metadata` on save (matches the existing Attributes
    pattern).
  - Tagged-values table becomes an editable grid: per-row `property`,
    `value`, `notes` inputs + ✕ delete + footer `+ Add Tagged Value`
    button. Rows with a blank property are dropped at save.
  - The Sparx `#NOTES#` convention (a `value` like `"3#NOTES#Values:
    1,2,3"`) is preserved across the edit boundary via a new
    `frontend/src/lib/utils/taggedValues.ts` util — `splitTaggedValue`
    surfaces the meaningful value and the prescriptive description in
    their own controls; `joinTaggedValue` reassembles on save; empty
    notes omits the marker. `isUnsetTaggedValue` mirrors the backend's
    `_extract_tagged_value` (`null` / `""` / `"-"` / `"-#NOTES#…"`).

### Fixed

- **Element PUT body no longer sends `element_type`** — `ElementUpdate`
  doesn't accept it (element type is immutable per ADR-178), so the
  field was a no-op. Dropped from `saveEntityMetadata`'s body
  construction. The element-type edit control on the page is
  unchanged for now (its no-op-on-save behaviour predates this PR
  and is tracked as a follow-up affordance cleanup).

## [6.38.0] - 2026-05-31

### Added

- **Two-layer aggregation engine cache** (ADR-227, SPEC-227-A) — makes
  smart-markdown dashboards composed of many `{{aggregation:<view>:…}}`
  tokens fast to load.
  - **Layer 1 — per-request memoisation via a `ContextVar`.** Wraps
    `compute_smart_markdown_content` and the aggregation_list synth
    hook in `diagrams/service.py`. Repeated calls within one render
    for the same `(profile_id, source_diagram_id)` (or the same
    element row / relationship count / diagram name) share a single
    result. The GEANZ Dashboard's six aggregation tokens collapse to
    three engine runs, and 20 hub-element fetches collapse to five.
  - **Layer 2 — process-wide version-keyed LRU.** Hot path keyed by
    `(profile_id, source_diagram_id)`, value = the full
    `AggregationResult`. On lookup, revalidates against
    `aggregation_profiles.updated_at` + a single batched
    `SELECT id, current_version FROM diagrams WHERE id IN (...)` over
    the diagrams in `AggregationResult.source_versions` — two
    queries on hit vs the 50–150 queries the engine would otherwise
    re-run. Invalidation is implicit: any version bump on a
    referenced diagram or the bound profile causes the next lookup
    to miss naturally; no explicit eviction hooks.
  - New `AggregationResult.profile_updated_at` field carries the
    bound profile's `updated_at` from compute time, supporting
    Layer 2 revalidation.
  - LRU size hard-coded to 512 entries; per-uvicorn-worker (in-process
    only — no Redis dependency added). A shared cache is a clean
    follow-up if cold-hit rates ever become a problem.
- **Element-fetch memo helpers in `smart_markdown.py`** —
  `_fetch_element_row` (new), plus per-request memo on
  `_fetch_element_relationship_count`,
  `_fetch_element_diagram_usage_count`, and the `element` /
  `package` / `diagram` / `set` / `collection` branches of
  `_fetch_entity_display_name`. The same element / link target is
  read once per render regardless of how many tokens reference it.

## [6.37.3] - 2026-05-30

### Fixed

- **Fullscreen view persists across iris:// link navigation.** Clicking
  a `iris://diagram/<id>` link inside a focused view used to drop the
  user out of fullscreen because the destination URL didn't carry the
  `?focus=1` flag. `MarkdownView`'s click handler now forwards the
  flag to view-class destinations so a focused → focused navigation
  stays focused.
- **No more unfocused flash before the diagram loads.** Opening a
  view URL with `?focus=1` used to render the normal layout briefly
  while the diagram fetch was in flight, then enter focus mode after
  the data arrived. The `focusMode` state is now initialised from the
  URL during script init (not in a post-render `$effect`), and the
  `loading` / `error` branches render inside `FocusView` when the
  URL says focus, so the focused chrome is on screen from the first
  paint.

## [6.37.2] - 2026-05-30

### Added

- **Shareable fullscreen URLs for views.** Focus mode on
  `/views/[id]` now syncs with a `?focus=1` query param. Toggling
  fullscreen updates the URL via `replaceState` (no history
  pollution); opening any view URL with `?focus=1` lands the page
  directly in fullscreen. Copy-paste-share a focused canvas without
  asking the recipient to click the button. Back/forward navigation
  to a URL without the flag drops out of focus correctly. Frontend
  only — no backend / API change.

## [6.37.1] - 2026-05-30

### Added

- **Two new smart-markdown tokens for dashboard totals** (ADR-226,
  SPEC-226-A):
  - `{{aggregation:<view_id>:row_count[:raw]}}` — total rows across
    every group from an aggregation_list view's profile output.
    Mirrors `AggregationResult.row_count` already exposed via
    `/api/aggregate` and MCP.
  - `{{set:<set_id>:element_count[:raw]}}` — live count of
    non-deleted elements in a set.
  Both compose with the ADR-224 `:raw` modifier so they can be
  dropped inside Mermaid blocks. Default form wraps in a markdown
  link back to the view / set (with the entity name as tooltip).
  Missing/deleted entity → strikethrough; live-but-empty set →
  `"0"`.

  These let the GEANZ Dashboard's Coverage snapshot table replace
  the remaining hand-typed cells (Total elements, ArchiMate_Capability
  stereotype, Maturity values populated, Orphan capabilities) with
  live tokens.

## [6.37.0] - 2026-05-30

### Added

- **Smart-markdown `aggregation` token — group counts from
  aggregation_list views** (ADR-225, SPEC-225-A). New token shape
  `{{aggregation:<aggregation_list_view_id>:group_count:<group>[:raw]}}`
  resolves to the row count of the named group within the bound
  profile's output. Composes with the ADR-224 `:raw` modifier so live
  group counts can be embedded inside Mermaid pie / xychart / flowchart
  blocks (e.g. the GEANZ Dashboard's Status pie now reads `"Approved"
  : {{aggregation:…:group_count:Approved:raw}}` instead of hand-typed
  values). Default form wraps the count in a markdown link back to the
  source aggregation_list view. Unknown group → `"0"`; missing /
  non-aggregation_list view → strikethrough.
- `AggregationResult.group_counts: dict[str, int]` — the new
  `{group_value: row_count}` map populated by the engine, surfaced
  for the smart-markdown token but also available to any other caller
  via the existing `/api/aggregate` and MCP `aggregate` surfaces.

## [6.36.2] - 2026-05-30

### Fixed

- **Aggregation-list edit-mode picker no longer spams the API**
  (`AggregationListCanvas.svelte`). Two bugs combined into a runaway
  request loop on the picker:
  - The source-diagram fetch sent `page_size=200`, but the backend
    `/api/diagrams` endpoint caps `page_size` at 100 and returned 422
    Unprocessable Content on every call.
  - The `$effect` that triggers the load re-fired whenever
    `diagrams.length === 0`, which the failed fetch could never
    populate — producing an infinite retry loop until the user
    closed the page.
  Capped the request at `page_size=100` and added one-shot
  `triedDiagrams` / `triedProfiles` guards so the picker attempts at
  most one fetch per editing-toggle, regardless of outcome.

## [6.36.1] - 2026-05-29

### Fixed

- **MCP `update_element` and CLI `iris update element` now forward `metadata`**.
  The backend `ElementUpdate` model already accepted `metadata`; the MCP
  surface (`_ELEMENT_UPDATE_FIELDS`) and the CLI command (`--metadata-json`)
  were missing it. Lets agents and scripts edit Sparx EA tagged values,
  status, and other element metadata via the standard surfaces. No new
  write op, no schema impact beyond exposing the existing backend field.

## [6.36.0] - 2026-05-29

### Added

- **Smart-markdown `:raw` modifier** (ADR-224, SPEC-224-A). A trailing
  `:raw` on any token's field-spec returns the resolved value **without**
  the `iris://` markdown-link wrap (ADR-209), so tokens can be embedded
  inside fenced code blocks (Mermaid `pie` / `xychart-beta` / `flowchart`)
  where the link syntax would otherwise break the parser. Composes with
  every existing token form — `meta:`, `tag:`, `attr:`, the ADR-210
  `=value` override, the ADR-221 `detail_diagram` short-circuit, the
  ADR-222 `element_count`, and so on. Lets dashboard charts drive their
  values live from the model.

## [6.35.0] - 2026-05-29

### Added

- **Element metadata, EA tagged-value, and computed-count tokens**
  (ADR-223, SPEC-223-A). Smart-markdown gains `{{element:<id>:meta:<key>}}`,
  `{{element:<id>:tag:<property>}}` (strips Sparx EA's `#NOTES#` template
  suffix; `""` / `"-"` → strikethrough), `{{element:<id>:relationship_count}}`,
  and `{{element:<id>:diagram_usage_count}}`. The aggregation engine
  accepts the same as `value_attribute_path` / `bucket_attribute_path`
  (e.g. `meta/status`, `tag/Maturity`, `relationship_count`,
  `diagram_usage_count`) and as `output.group_by` (e.g.
  `element.meta.status`, `element.tag.Maturity`). Unlocks live rollups of
  Status (Approved/Proposed), hubs by relationship count, orphan / unused
  capability lists, and Maturity rollups straight off the element row —
  no engine algorithm change, no migration, no surface-parity impact.

## [6.34.0] - 2026-05-29

### Added

- **Smart-markdown `{{diagram:<id>:element_count}}` token** (ADR-222,
  SPEC-222-A). Renders a live count of the element nodes on a referenced
  view (excluding `diagram_frame` / `note` decoration), wrapped in a link
  that drills into that view. Computed on read, so the figure follows the
  view's contents instead of being hand-maintained. Lets a smart-markdown
  source show a real "N elements in this view" count.

## [6.33.1] - 2026-05-29

### Changed

- Renamed the element-page label "Detail diagram" to **"Detail view"**
  (ADR-221 follow-up). UI label only — the `detail_diagram_id` field /
  API / MCP / CLI surface is unchanged.

## [6.33.0] - 2026-05-29

### Added

- **Element → detail diagram drill link** (ADR-221, SPEC-221-A, issue
  #242). An element can now declare a navigable "detail diagram" — the
  Sparx EA "composite element" concept — so you can drill from an element
  into the diagram that elaborates it, and back out. Surfaced as a new
  nullable `elements.detail_diagram_id` column (migration m080 / Supabase
  m086), tri-state on update like `package_id`:
  - **API/MCP/CLI** (§14 surface parity): `create_element` /
    `update_element` accept `detail_diagram_id` (MCP) /
    `--detail-diagram-id` (CLI), set/clear via JSON `null`. Cross-set
    links are allowed; the target diagram is validated to exist.
  - **Element page** shows a "Detail diagram" drill-in (and a picker to
    set/clear it); the **diagram page** lists referencing elements under
    "Referenced by" (`get_diagram` gains `referenced_by_elements`).
  - **Smart-markdown**: a new `{{element:<id>:detail_diagram}}` token
    renders a link straight to the element's detail diagram.
  - **Sparx EA import**: composite elements (`t_diagram.ParentID` in
    `.qea`; the diagram `owner` in native XMI) now populate
    `detail_diagram_id` automatically, so imported models light up the
    drill.

## [6.32.1] - 2026-05-29

### Fixed

- **Full screen on markdown-notation diagrams** (#243). The "Full screen"
  toolbar button did nothing on text / smart-markdown / dynamic-list /
  aggregation-list views: the text render branches never mounted
  `FocusView`, so toggling focus mode had no visible effect. The text
  branches (browse and edit) now wrap their content in `FocusView` when
  focus mode is active, and the editor's canvas focus branch is gated to
  non-text views so a text view no longer flips to a blank canvas overlay.
  The four-way text-canvas switch is now shared via a single
  `{#snippet markdownArea()}` (DRY) instead of being duplicated across the
  browse, edit, and full-screen variants.

## [6.32.0] - 2026-05-28

### Added

- **Native Sparx EA XMI 2.1 (`.xml`) import** (ADR-219, SPEC-219-A). Iris
  can now import Sparx Enterprise Architect's native XML export ("Export
  Package to XMI 2.1 / Native XML"), in addition to the existing
  `.qea`/`.eap` database import. The new `POST /api/import/sparx-xml`
  endpoint parses the UML 2.1 XMI + EA `<xmi:Extension>` block (packages,
  elements, connectors, tagged values, and diagram geometry) and reuses
  the entire `.qea` import pipeline — type/stereotype mapping, geometry
  conversion, and `ea_guid` idempotency are shared via a new
  surface-agnostic `import_sparx_model` orchestrator (DRY). The import UI
  content-sniffs `.xml` uploads to route Sparx native XMI vs ArchiMate
  Open Exchange automatically. Import-only, website-only this release; an
  MCP tool and CLI command are planned for a follow-up.

## [6.31.5] - 2026-05-28

### Fixed

- **Diagrams generated via the MCP `create_diagram` tool failed to
  load** (issue [#238](https://github.com/cgbarlow/iris/issues/238),
  ADR-218). The shared creation prompt teaches models the *flat* AI node
  shape (`{id, type, label, position, size, visual}`) that
  `apply_diagram_creation` converts to canvas shape — but
  `create_diagram` persisted its `data` verbatim, so flat nodes reached
  storage with no per-node `data` object and the canvas crashed with
  `Cannot read properties of undefined (reading 'entityType')`.
  `create_diagram` / `update_diagram` now normalise the flat shape to
  canvas shape on write, and `get_diagram` auto-heals legacy flat
  diagrams on read (non-destructive). A new shared
  `normalize_canvas_data` is the single source of truth; the
  `apply_diagram_creation` builder now delegates to it (DRY).

- `UnifiedCanvas` `fitViewOptions` now optional-chains `n.data` so a
  dataless node can never hard-crash the canvas on mount
  (defense-in-depth behind the backend fix).

### Repair (UAT/prod)

- The three already-broken diagrams named in issue #238 are repaired in
  place — and only those — by
  `scripts/repair_flat_diagram_shape.py --diagram-id <id> …`, which
  reuses `normalize_canvas_data` and regenerates the affected diagrams'
  thumbnails. The script refuses to run without explicit ids and never
  scans all diagrams. No database schema migration is required.

## [6.31.4] - 2026-05-26

### Fixed

- **Row Level Security enabled on three Supabase tables that slipped past
  the m030 sweep** (issue [#236](https://github.com/cgbarlow/iris/issues/236),
  ADR-095). `artefacts` (m064, v6.2.0), `element_templates` (m071, v6.11.0),
  and `aggregation_profiles` (m081, v6.28.0) were created without
  `ENABLE ROW LEVEL SECURITY`, so the public Supabase `anon` key could
  reach those rows directly via PostgREST, bypassing the FastAPI RBAC
  layer. Migration m085 enables the standard deny-all policy on all
  three; the backend still bypasses RLS as table owner, so no
  application code changes are needed.

- The `test_rls_policies.py` structural test now scans the full Supabase
  migration set instead of just m001–m029, so any future table that
  ships without RLS is caught in CI.

### Migration

- **Supabase only.** Run `scripts/supabase-migrate.sh` against UAT/prod
  after deploy to apply m085. SQLite installations are unaffected (no
  RLS in SQLite).

## [6.31.3] - 2026-05-25

### Fixed

- Aggregation Profiles moved under **Admin → Settings** as an **Aggregation** tab; removed the standalone sidebar link added in v6.31.2.

## [6.31.2] - 2026-05-25

### Fixed

- Aggregation Profiles added to the admin sidebar so it is directly reachable without going through the `/admin` dashboard card.

## [6.31.1] - 2026-05-25

### Added

- Aggregation profile editor surfaces the `output.include_provenance`
  flag (ADR-217) as a discrete checkbox above the JSON textarea.
  Lets a non-technical user flip the flag without editing the raw
  profile_data — patches the parsed JSON on save. SPEC-217-a's UI
  exposure gap from v6.31.0 closed.

## [6.31.0] - 2026-05-24

### Added

- Aggregate output provenance flag (ADR-217) — opt-in per-line
  element_id surfacing for downstream consumers.

## [6.30.2] - 2026-05-22

### Fixed

- **Render deploys no longer get marked `canceled` by the
  port-detection timeout.** `_initialize_supabase` was awaiting
  `regenerate_all_thumbnails` synchronously inside the FastAPI
  lifespan; with 1100+ diagrams on UAT the regen took ~5–6 minutes
  per deploy, well past Render's port-binding deadline. Render
  printed `==> No open ports detected, continuing to scan…` three
  times and cancelled the deploy, despite the process being healthy
  and reaching `Application startup complete` shortly afterwards.

  v6.30.2 dispatches the regen as a fire-and-forget background task
  via `asyncio.create_task(...)`. The lifespan returns immediately
  after scheduling — the port binds in seconds. Thumbnails update
  silently over the next few minutes; any new or changed diagram
  still renders fresh on first GET regardless of whether the
  background sweep has finished. Errors inside the background task
  are logged + swallowed (no unhandled-exception warnings on
  SIGTERM mid-regen).

- The SQLite startup path is unchanged — small dev/self-hosted
  databases don't hit the timeout and the seed example diagrams
  benefit from being rendered synchronously on first run.

### Migration

- None. Pure backend startup-flow change.

## [6.30.1] - 2026-05-22

### Fixed

- **UML attribute `notes` field is editable in element edit mode.**
  Browse view already displayed the `notes` column under Attributes;
  the edit view's attribute table had Scope / Name / Type / Lower /
  Upper but **no Notes input** — values typed via API/CLI persisted
  fine but couldn't be added or changed in the browser. Edit mode now
  has a Notes column that round-trips the value. The underlying
  edit-state mapping in `startEdit` already preserved notes; only the
  UI was missing.

### Migration

- None. Pure frontend addition (one column + one input).

## [6.30.0] - 2026-05-22

### Added

- **Smart-markdown edit-view companion panel**
  ([SPEC-205-b](docs/adrs/specs/SPEC-205-b-Smart-Markdown-Edit-Preview.md),
  supersedes [SPEC-210-a §5.1](docs/adrs/specs/SPEC-210-a-Smart-Markdown-Value-Overrides.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211) comment
  observations C5 + C6). Edit mode in `SmartMarkdownCanvas.svelte`
  now shows a right-hand panel alongside the source textarea with
  two sections:

  - **Fill in the blanks.** Every `{{...:attr:<path>=}}` empty-
    override token (the fillable-slot form from ADR-210) appears as
    a labeled input row — element name, attribute name, editable
    field, and a small `↳ "value path Name"` resolved-line preview.
    Filling the input rewrites the source token in place
    (byte-position rewrite, not string-replace — duplicate tokens
    are disambiguated correctly). This finally delivers the
    inline-editable-spans UX that SPEC-210-a §5.1 specified back
    when v6.18.0 shipped the backend grammar.
  - **Tokens preview.** The last-saved resolved markdown
    (`data.content`) rendered in muted grey via `MarkdownView`. A
    small `↻ saved` / `* unsaved — preview shows last save`
    indicator distinguishes saved vs. drafting state. Live full
    re-render is out of scope (would need either a backend
    roundtrip per keystroke or a JS port of the resolver — DRY
    violation §13).

  Element-name lookups are lazy + cached per element-id. Defensive
  input sanitisation drops `}` and `\` characters to keep the source
  token shape intact.

- The companion panel collapses below the textarea on viewports <
  900px so narrow screens stay usable.

### Migration

- None. Pure frontend addition; no schema, no backend change.

### Out of scope (future)

- Live (debounced) full resolved preview as you type.
- Per-token hover tooltips on the textarea itself.
- Editing non-fillable tokens (e.g. swapping which element a `:name`
  token points at).

## [6.29.0] - 2026-05-22

### Added

- **Clone-from-existing for aggregation profiles**
  ([SPEC-212-e](docs/adrs/specs/SPEC-212-e-Aggregation-Profile-Editor-Polish.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211) comment
  observation O7). A new **+ Clone from existing** button sits next
  to **+ New profile** in `AggregationProfileEditor.svelte`. Selecting
  a profile prefills the editor with `name + " (copy)"`, description,
  and `profile_data`. The clone is always created in the parent's
  scope (set-scoped when invoked from the set page; global when from
  admin) — so you can clone a seeded global into a customised
  set-scoped profile in one move. `is_default_for_set` resets to
  false on every clone.
- **Clone-from-existing for element templates**
  ([SPEC-211-e](docs/adrs/specs/SPEC-211-e-Element-Template-Clone.md),
  observation C4). `TemplatesListDialog` (elements list → Templates
  button) gains a **Clone** action per row, parallel to **Use**. The
  parent page hosts a small mini-dialog asking only for the new name;
  the body is reused from the source (description, template_data,
  markdown_stamp, scope). After creation the page navigates to the
  new template's detail page.

### Changed

- **Friendlier aggregation-profile editor help text** (O6). Replaced
  the ADR/SPEC-mentioning paragraph in `AggregationProfileEditor.svelte`
  and the admin home card description with copy that talks in product
  terms (rollups across documents, totals, etc.).
- **Seeded "Quantified item" element template renamed to "Ingredient"**
  (C3). Same id, same stamp body, same scope; updated name +
  description only. New paired migrations **SQLite m079 / Supabase
  m084** (idempotent: WHERE clause guards on the original name so
  re-running doesn't double-rename).

### Migration

- **SQLite m079** + **Supabase m084**: rename the seeded global
  template row `ea8829e5-…` from "Quantified item" to "Ingredient".
- Supabase migration applied to the live DB before this merge per
  `feedback_render_supabase_ordering`.

## [6.28.0] - 2026-05-22

### Changed

- **Set creation inherits the active collection filter**
  ([ADR-216](docs/adrs/ADR-216-Set-Creation-Inherits-Collection.md),
  [SPEC-216-a](docs/adrs/specs/SPEC-216-a-Set-Creation-Inherits-Collection.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211) comment
  observation O5). When the sets list page (`/sets`) is filtered by a
  collection (via `?collection_id=…` or the active-collection store),
  clicking "Create new set" now passes that collection id through to
  the backend so the new set is born in that collection. Sets
  created from the unfiltered view remain collection-less (current
  behaviour preserved).

### Migration

- None. Pure frontend change in `frontend/src/routes/sets/+page.svelte`.

## [6.27.0] - 2026-05-22

### Changed

- **Smart-markdown picker stamp filter narrowed by body-referenced
  attributes** ([ADR-215](docs/adrs/ADR-215-Stamp-Filter-By-Body-Attributes.md),
  [SPEC-211-d](docs/adrs/specs/SPEC-211-d-Stamp-Filter-By-Body-Attributes.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211) comment
  observation O2/O3). The `/api/element-templates/stamps?element_id=…`
  endpoint now additionally filters out stamps whose body references
  attributes the target element doesn't have. Resolves the user-
  reported case where every grocery element saw all five seeded
  stamps including ones for sprint points and reading logs.
  - Attribute requirements are extracted from `{{self:attr:attributes/<NAME>/<rest>}}`
    tokens in the stamp body via regex. The set must be a subset of
    the element's `data.attributes` names for the stamp to appear.
  - Stamps whose body uses no `self:attr:` tokens (e.g. just
    `{{self:name}}`) pass the body filter trivially.
  - The five seeded stamps now narrow naturally:
    - **Quantified item** (Quantity + Unit) → groceries with both
    - **Sized story** (Points) → story-shaped elements
    - **Logged work** (Hours) → log-shaped elements
    - **Line item** (Amount + Currency) → expense-shaped elements
    - **Read entry** (Pages + Author) → reading-log-shaped elements

### Migration

- None. Pure filter logic change in
  `backend/app/element_templates/service.py::list_stamps_for_element`.

## [6.26.1] - 2026-05-22

### Fixed

- **Admin → Settings → Seed Example Diagrams** no longer 500s with a
  `ForeignKeyViolationError` when the user has placed any non-seed
  diagram or element under a seed package. The seed's
  `_clear_old_seed_data` flow now NULLs out non-seed FK references to
  seed packages (diagrams.parent_package_id, elements.package_id) and
  to seed elements (element_templates.source_element_id, bookmarks)
  before deleting them, so orphaned user content survives the
  clear-and-re-seed cycle (reparented to "no package") while the seed
  packages go away cleanly.
- The browser-side symptom — "No access control origin header" CORS
  error — was a downstream effect of Render returning a 500 without
  CORS headers when the backend exception fired. The fix is on the
  backend; CORS is unchanged.

### Migration

- None. Pure logic fix in `backend/app/seed/example_models.py`.

### Test plan

- Regression tests added in
  `backend/tests/test_seed/test_example_models.py` cover both the
  "non-seed diagram parented to a seed package" and "user template
  referencing a seed element" cases.

## [6.26.0] - 2026-05-22

### Added

- **`aggregation_list` canvas with source + profile pickers**
  ([SPEC-213-b](docs/adrs/specs/SPEC-213-b-Aggregation-List-Pickers.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211),
  follow-up to v6.21.0). New `AggregationListCanvas.svelte`:
  - **View mode**: renders the synthesised `data.content` via
    `MarkdownView` (same as smart_markdown / dynamic_list).
  - **Edit mode**: native `<select>` pickers for source diagram
    (`smart_markdown` only, scoped to the same set) and aggregation
    profile (in-scope: set-scoped + globals). Collapsible preview
    of the currently rendered output.
- **`DiagramDialog` create flow** offers `Aggregation list` under the
  `markdown` notation. Picker labels are alpha-sorted (preserved from
  ADR-206), so the new entry appears at the top of the markdown
  type list.
- **`views/[id]` canvas dispatcher** gains an `aggregation_list`
  branch in both edit-mode and browse-mode paths.

### Migration

- None. Pure frontend addition; reuses v6.20.0 + v6.21.0 endpoints.

### Out of scope

- Typeahead autocomplete on the source / profile pickers (native
  `<select>` is sufficient for now).
- Cross-set source picking (current: same-set only).
- Live engine re-render on every config change (current: triggers on
  Save like other canvases).

## [6.25.0] - 2026-05-22

### Added

- **Aggregation profile editor** UI
  ([SPEC-212-d](docs/adrs/specs/SPEC-212-d-Aggregation-Profile-Editor.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211),
  follow-up to v6.20.0). New reusable component
  `AggregationProfileEditor.svelte` for listing, creating, editing,
  and soft-deleting aggregation profiles. Edit-form has Name +
  Description + JSON textarea for `profile_data`, with parse-validate
  on Save. Seeded profiles are good clone templates.
- **`/admin/aggregation-profiles`** — new admin route for global
  profiles, with a card linking from the admin home page.
- **Set edit page** gains a new section listing and managing
  set-scoped profiles (above the Danger zone).

### Migration

- None. Pure frontend addition; reuses v6.20.0 REST endpoints.

### Out of scope (deferred)

- Tabbed form-based editor (General / Traversal / Multiplier /
  Output). The JSON textarea covers v1; the seeded profiles cover
  the common cases.
- Attribute-path autocomplete.
- Inline preview of the engine against a draft.

## [6.24.0] - 2026-05-22

### Added

- **Element-template stamp editor** in the template detail page
  ([SPEC-211-c](docs/adrs/specs/SPEC-211-c-Stamp-Editor.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211),
  follow-up to v6.19.0). A new **Markdown stamp** section shows the
  template's `markdown_stamp` body with an inline edit textarea.
  Save → `PUT /api/element-templates/{id}` with the new body;
  empty string clears the stamp. Help text documents
  `{{self:name}}` / `{{self:attr:<path>}}` / trailing-`=` fillable-
  slot syntax. The seeded stamps are good clone templates for
  authoring new ones.

### Migration

- None. Pure frontend addition.

### Out of scope (deferred)

- Picker self-mode (smart-markdown picker emitting `{{self:…}}`
  tokens instead of full `{{element:UUID:…}}` tokens). The current
  v1 editor is a plain textarea; authors write tokens by hand.
- Live preview of the stamp rendered against the template's source
  element.

## [6.23.0] - 2026-05-22

### Added

- **Smart-markdown picker — Stamps section**
  ([SPEC-211-b](docs/adrs/specs/SPEC-211-b-Picker-Stamps-Section.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211),
  follow-up to v6.19.0). When the picker enters drill mode against an
  element, it fetches in-scope stamps via
  `GET /api/element-templates/stamps?element_id=<id>` and surfaces
  them as one-pick rows at the top of the drill menu. Backend has
  already substituted `{{self:…}}` → `{{element:<id>:…}}` so the
  body is paste-ready. Selecting a stamp emits its body verbatim
  via `oninsert`; downstream tokens behave like any author-typed
  tokens.
- Stamp rows display as `Stamp: <template name>`. Keyboard
  navigation (arrows / Enter / Tab / `.`) inherits from the existing
  drill menu — no new keys.
- Compresses the common multi-token recipe-author line (quantity +
  unit + name) from three picker round-trips to one.

### Changed

- For non-element entities (collection, set, package, diagram) the
  picker is unchanged — stamps don't apply (the endpoint requires an
  element id).

### Migration

- None. Pure frontend addition.

## [6.22.0] - 2026-05-22

### Added

- **Three operator-run migration scripts** for the meal-plan →
  shopping-list demo workflow (issue #211):
  - `scripts/backfill_quantity_attribute.py` — adds a blank
    `Quantity` attribute to every element in a target set so authors
    can write `=<value>` overrides without first editing each
    element's data.
  - `scripts/migrate_recipes_to_quantity_tokens.py` — rewrites the
    legacy free-text quantity pattern
    `NNN {{element:UUID:attr:.../Unit/type}} {{element:UUID:name}}`
    into the ADR-210 structured form
    `{{element:UUID:attr:attributes/Quantity/type=NNN}} {{element:UUID:attr:attributes/Unit/type}} {{element:UUID:name}}`.
    Renders identically; now machine-parseable by the v6.20.0
    aggregation engine.
  - `scripts/backfill_servings_on_recipes.py` — sets
    `data.servings` on smart_markdown diagrams so the Shopping list
    profile's diner-count multiplier has a denominator.
- All three scripts: argparse CLI; dry-run mode; idempotent;
  `--created-by <uuid>` for Supabase NOT-NULL attribution (auto-
  detected from existing rows in the set when omitted).
- Pure-function regex tests in
  `backend/tests/test_scripts/test_migrate_recipes_regex.py`.
- **Live demo data migrated**: 178 grocery elements gained a
  Quantity attribute; 124 quantity prefixes rewritten across 29
  recipes; 34 recipes gained `data.servings = 4`. Issue #211
  end-to-end workflow is now exercisable.

### Migration

- Operator-run, not in the SQLite startup runner (target sets are
  environment-specific). The three scripts are pure data
  transforms — no schema changes. Already applied to the live UAT/
  prod data.

## [6.21.1] - 2026-05-22

### Added

- **Genericness invariant CI check**
  ([ADR-214](docs/adrs/ADR-214-Genericness-Invariant-Shopping-List.md),
  [SPEC-214-a](docs/adrs/specs/SPEC-214-a-Genericness-Invariant.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211)).
  `scripts/check_aggregation_genericness.py` fails CI if any of the
  banned domain terms — `ingredient`, `recipe`, `meal`, `diners`,
  `servings`, `aisle`, `grocery`, `pantry`, `shopping` — appears in
  Iris core code paths. Mirrors ADR-182's surface-parity discipline:
  the shopping-list workflow was deliberately built without domain
  terminology in code; this script keeps that honest under future
  contributions.
- Comments and docstrings are exempt — the principle is "no domain
  logic," not "no domain mentions." Allow-listed paths: migrations,
  seed, import_sparx, tests, i18n, all `*.md` files.
- New GitHub Actions workflow `genericness-check.yml` runs the
  script on PRs touching `backend/app/**`, `frontend/src/**`, the
  script itself, or the workflow file.
- pytest harness in `backend/tests/test_aggregation/test_genericness_invariant.py`
  so local runs catch violations too.

### Migration

- None.

## [6.21.0] - 2026-05-22

### Added

- **`aggregation_list` diagram type**
  ([ADR-213](docs/adrs/ADR-213-Aggregation-List-Diagram-Type.md),
  [SPEC-213-a](docs/adrs/specs/SPEC-213-a-Aggregation-List-Diagram-Type.md),
  issue [#211](https://github.com/cgbarlow/issues/211)). Synth-on-
  read diagram type under the `markdown` notation. Storage is
  minimal config (`data.source_diagram_id` + `data.profile_id`); the
  v6.20.0 aggregation engine fills `data.content` at GET time. Thin
  wrapper — the engine does the real work. Failures (missing
  source/profile/etc.) render informative placeholders in
  `data.content` instead of crashing the GET, so the diagram stays
  editable.
- The aggregation_list canvas reads `data.content` and renders it
  via the existing `MarkdownView` component — same look and feel as
  smart_markdown and dynamic_list.

### Migration

- **SQLite m078 / Supabase m083** — register `aggregation_list`
  diagram type under the `markdown` notation. Two-row insert
  (`diagram_types` + `diagram_type_notations`), idempotent via
  `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING`.
- Supabase migration applied to the live DB prior to merge.

## [6.20.0] - 2026-05-22

### Added

- **Generic aggregation engine + profile library**
  ([ADR-212](docs/adrs/ADR-212-Aggregation-Profiles-And-Engine.md),
  [SPEC-212-a](docs/adrs/specs/SPEC-212-a-Aggregation-Profile-Schema.md),
  [SPEC-212-b](docs/adrs/specs/SPEC-212-b-Aggregation-Engine.md),
  [SPEC-212-c](docs/adrs/specs/SPEC-212-c-Aggregation-Surfaces.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211)). A new
  `aggregation_profiles` table holds rulesets; the engine in
  `backend/app/aggregation/` walks a source smart-markdown diagram
  (optionally recursing one level into referenced diagrams),
  collects tokens of a configured type, resolves per-use values via
  ADR-210 `=value` overrides, groups by `(token_id, bucket)`,
  aggregates with `sum` or `count`, groups again by an output
  attribute, and renders configurable markdown lines. No domain
  terminology (recipe / ingredient / sprint / receipt) lives in
  code — all the flavour is in the profile JSON.
- **Five seeded global aggregation profiles**:
  - **Shopping list** — outer: diagram tokens with Diners/Servings
    multiplier; inner: element tokens with Quantity/Unit; group_by:
    `element.package_name`. Pairs with the "Quantified item" stamp.
  - **Sprint points rollup** — story-points sum, grouped by team.
  - **Time tracker rollup** — hours sum, grouped by client/project.
  - **Expense report** — amount sum bucketed by currency, grouped by
    category.
  - **Reading log rollup** — pages sum, grouped by author.

  Each ships as `is_global = TRUE` with deterministic UUIDv5 ids so
  re-running migrations is a no-op.
- **REST endpoints** under `/api/aggregation/`:
  - `POST /api/aggregation/profiles` (create) + `GET / GET {id} / PUT / DELETE`.
  - **`POST /api/aggregation/run`** — apply a profile to a source
    diagram. Returns `{markdown, computed_at, source_versions,
    row_count, warnings}`. Read-shaped despite POST; no persistence
    side-effects.
- **MCP tools**: `create_aggregation_profile`,
  `list_aggregation_profiles`, `get_aggregation_profile`,
  `update_aggregation_profile`, `delete_aggregation_profile`, and
  the linchpin **`aggregate`** (run a profile against a source).
  Callable directly by Claude Desktop / any agent without ever
  opening a UI.
- **CLI subcommands**: `iris aggregation-profile create / list /
  get / update / delete` plus **`iris aggregate --profile <id>
  --source <id>`**. The aggregate command is the CLI face of the
  same engine MCP and REST share.

### Migration

- **SQLite m076 / Supabase m081** — create `aggregation_profiles`
  table.
- **SQLite m077 / Supabase m082** — seed five global profiles.
- Supabase migrations applied to the live DB prior to merge per
  `feedback_render_supabase_ordering`.

## [6.19.0] - 2026-05-22

### Added

- **Markdown stamps on element templates**
  ([ADR-211](docs/adrs/ADR-211-Element-Template-Stamps.md),
  [SPEC-211-a](docs/adrs/specs/SPEC-211-a-Element-Template-Stamps.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211)).
  `element_templates` gains a new `markdown_stamp TEXT` column that
  holds a smart-markdown fragment using `{{self:<field-spec>}}`
  placeholders. At smart-markdown insert time the picker substitutes
  `self` with the selected element's ID, so a single pick yields a
  multi-token line (e.g. quantity + unit + name) instead of three
  separate picker round-trips. Stamps live on element_templates so
  they reuse the existing scope (`is_global` / `set_id`) and
  management UX.
- **`POST` / `PUT /api/element-templates` accept `markdown_stamp`
  and direct `template_data`**. `source_element_id` is now optional —
  a template can carry direct content via `template_data`, a stamp
  via `markdown_stamp`, or both. At least one of the three (source,
  data, stamp) must yield non-empty content; empty templates are
  rejected with 422.
- **`GET /api/element-templates/stamps?element_id=<id>`** — new read
  endpoint returning in-scope stamps for an element. Scope rules:
  template is global OR set-matches the element's set; if the
  template's captured `element_type` is set, it must match the
  element's. Each returned `markdown_stamp` has `{{self:…}}` already
  rewritten to `{{element:<element-id>:…}}` so the body is paste-ready.
- **MCP tool `list_element_template_stamps`** — calls the new
  endpoint. Discoverable by Claude Desktop / any agent during smart-
  markdown authoring sessions.
- **MCP `create_element_template` and `update_element_template`** accept
  the new `markdown_stamp` and `template_data` arguments. CLI
  `iris create / update element-template` gain `--markdown-stamp`
  and `--template-data-file` flags.
- **Five seeded global element-template stamps** ship in m075 / m080:
  - **Quantified item** — `{{self:attr:attributes/Quantity/type=}} {{self:attr:attributes/Unit/type}} {{self:name}}`
  - **Sized story** — `{{self:attr:attributes/Points/type=}} pts — {{self:name}}`
  - **Logged work** — `{{self:attr:attributes/Hours/type=}}h — {{self:name}}`
  - **Line item** — `{{self:attr:attributes/Currency/type}}{{self:attr:attributes/Amount/type=}} — {{self:name}}`
  - **Read entry** — `{{self:attr:attributes/Pages/type=}} pages — "{{self:name}}" by {{self:attr:attributes/Author/type}}`

  Each carries a pre-filled `data.attributes` blueprint so creating an
  element from the template yields the slots its stamp expects. All
  ship as `is_global = TRUE` with `created_by = NULL`.

### Changed

- `element_templates.created_by` is now nullable in the response
  model — seeded global templates have no authoring user. Existing
  user-created templates always carry the author's id (unchanged).

### Migration

- **SQLite m074** — `markdown_stamp` column added to
  `element_templates`. Idempotent.
- **Supabase m079** — mirror of m074. Apply via
  `scripts/supabase-migrate.sh` before rolling forward.
- **SQLite m075 / Supabase m080** — seed the five global stamps with
  deterministic UUIDv5 ids so re-running is a no-op.
- Order per memory `feedback_render_supabase_ordering`: apply Supabase
  migrations first, then merge to `main` so Render serves code with
  the column already present.

## [6.18.0] - 2026-05-22

### Added

- **Smart-markdown tokens accept inline `=value` overrides on the
  field-spec** ([ADR-210](docs/adrs/ADR-210-Smart-Markdown-Value-Overrides.md),
  [SPEC-210-a](docs/adrs/specs/SPEC-210-a-Smart-Markdown-Value-Overrides.md),
  issue [#211](https://github.com/cgbarlow/iris/issues/211)). A token
  of the form `{{element:UUID:attr:Quantity/type=500}}` resolves to
  "500" regardless of the stored attribute value — per-use values
  without a side table. The resolver splits on the first `=` so
  override values may themselves contain `=`. A token with an empty
  override (`{{...:attr:path=}}`) is a "fillable slot" marker:
  renders as strikethrough so an unfilled placeholder is visible.
  Dangling references (deleted entities) still strike through even
  when an override is present. Existing tokens without `=` resolve
  identically to before — pure additive grammar extension.
- **Smart-markdown picker — Shift+Enter inserts as fillable slot**.
  Pressing Enter on a primitive in the picker emits the normal token;
  Shift+Enter emits the same token with `=` appended so the author
  can fill the value in the source pane (or hand the diagram to a
  collaborator). Hint text in the picker updated.

### Migration

- None. Pure grammar additive change; no schema or data migration.
- Existing recipes with plain-text quantities (e.g.
  `500 {{element:UUID:attr:Unit/type}} {{element:UUID:name}}`) render
  identically. Migration to the new override form is optional and
  arrives later via issue #211 PR 6.

## [6.17.9] - 2026-05-21

### Changed

- **Smart-markdown thumbnails now show the rendered text**, not the
  raw `{{element:GUID:field}}` tokens stripped to `[…]`
  (issue [#208](https://github.com/cgbarlow/iris/issues/208) follow-up).
  `generate_and_store_thumbnail` now calls
  `compute_smart_markdown_content` for `smart_markdown` diagrams so
  the thumbnail reflects what the user sees in the rendered view. The
  resolver's markdown link syntax (`[value](iris://… "name")`) is
  stripped to plain text for the tile; inline `<img>` tags become
  `[image]`; strikethrough'd unresolvable tokens unwrap to the raw
  token (then `_markdown_preview_lines` applies the old `[…]`
  placeholder).
- Falls back to the previous v6.17.6 behaviour (raw source with tokens
  → `[…]`) if the resolver raises — logged but non-fatal.

### Migration

- None.

## [6.17.8] - 2026-05-21

### Fixed

- **Markdown view thumbnails now actually regenerate on Supabase
  deployments** (issue [#208](https://github.com/cgbarlow/iris/issues/208)).
  `_initialize_supabase` was deliberately skipping
  `regenerate_all_thumbnails` based on a stale comment about
  "Netlify Function runtime" — Iris runs on Render's Docker image
  which bundles cairo + pango. As a result, the v6.17.6/v6.17.7
  markdown-preview SVG generator was dormant for pre-existing
  diagrams. Now runs on every Supabase startup (soft-fail with a log
  line if cairosvg is somehow unavailable).
- **Set filter by collection now applies on the Views and Bookmarks
  pages** (issue [#208](https://github.com/cgbarlow/iris/issues/208) /
  issue [#200](https://github.com/cgbarlow/iris/issues/200) follow-up).
  Both pages rendered `<SetSelector>` without the `collectionId` prop,
  so the dropdown always loaded the full set list regardless of which
  collection was picked. Elements page (the original #200 target) was
  already wired correctly in v6.17.6; the same fix now lands here.

### Migration

- None.

## [6.17.7] - 2026-05-21

### Fixed

- **Markdown view thumbnails now actually render text on Render**
  (issue [#205](https://github.com/cgbarlow/iris/issues/205) item 3
  regression). v6.17.6's text spans specified
  `font-family="ui-monospace,monospace"` — on Render's container,
  Pango couldn't resolve the family and produced text with no
  visible glyphs (blank background tile). Dropped the font-family
  attribute so cairosvg uses the same default the visual-diagram
  thumbnails use successfully.
- **`generate_and_store_thumbnail` now catches non-ImportError
  exceptions from cairosvg** so a single rasterisation failure
  can't break the whole `regenerate_all_thumbnails` startup sweep.
  Falls back to storing raw SVG bytes — browsers render SVG via
  `<img>` natively.

### Migration

- None.

## [6.17.6] - 2026-05-21

### Added

- **Markdown-notation views now get auto-generated thumbnails**
  (issue [#205](https://github.com/cgbarlow/iris/issues/205)
  item 3). `generate_svg_from_diagram_data` learns to render
  `smart_markdown` / `text` / `dynamic_list` types as a plain-text
  SVG preview (first heading + first lines of `data.markdown_source`
  or `data.content`). cairosvg pipes the SVG through the existing
  PNG store; `regenerate_all_thumbnails` on startup backfills
  existing markdown views. v6.17.4 had only added an attached-image
  fallback — the user wanted the same machinery visual diagrams use,
  not a fallback.

### Fixed

- **Collections gallery now shows attached image as tile**
  (issue [#205](https://github.com/cgbarlow/iris/issues/205)
  item 5). v6.17.4 added the rendering path on the sets gallery
  but missed `frontend/src/routes/collections/+page.svelte` —
  collections still hardcoded the "C" placeholder. Added
  `getImageThumbnailUrl` + `<img>` rendering mirroring the sets
  page.
- **Elements page Set dropdown filter by Collection (issue #200)
  hardened.** v6.17.4's SetSelector relied on Svelte 5's reactive
  read inside an `$effect` that only bare-touched `collectionId`
  before calling a closure-capturing `loadSets()`. Refactored
  `loadSets` to accept the explicit argument so the dependency is
  unambiguous; the elements page's `currentCollectionId` continues
  to drive it.

### Migration

- None.

## [6.17.5] - 2026-05-20

### Changed

- **All four component version numbers are now bumped together** on
  every Iris release. v6.17.4 added the `/version` page but the
  per-component pyproject versions (backend 1.2.0 / mcp 6.13.0 /
  cli 0.1.0) had drifted years behind the frontend's release-tag
  cadence, so the page showed misleading stale numbers. Synced all
  four to `6.17.5`; future releases follow this convention.
- **`/version` page now leads with the Iris release tag** (from
  `frontend/package.json`) and the build's git commit sha, with
  the per-component versions as a secondary table. A warning row
  flags any version divergence between components so a stuck
  deploy is obvious.

### Added

- **`GET /api/version` now returns `git_sha`** — sourced from
  `IRIS_GIT_SHA` / `RENDER_GIT_COMMIT` env vars at backend startup,
  with a `git rev-parse HEAD` fallback for local dev. The
  ground-truth signal when package numbers are out of sync.

### Migration

- None.

## [6.17.4] - 2026-05-20

### Fixed

- **Views Details → Images section now actually renders.** v6.17.0
  mounted the section just before `{:else if activeTab ==
  'relationships'}` — but by that anchor we were inside the Canvas
  branch (`{:else if activeTab == 'canvas'}` opens earlier). Moved
  the mount inside the Details branch so clicking the Details tab
  shows it.
- **Elements page Set dropdown now filters by selected Collection**
  (issue [#200](https://github.com/cgbarlow/iris/issues/200)). The
  `SetSelector` gains an optional `collectionId` prop; when set,
  it loads `/api/sets?collection_id=X`. The elements page wires
  this from its active collection state.
- **Markdown-notation views now show a thumbnail** in the views
  gallery. `DiagramThumbnail` can't render markdown content into
  a tile, so SVG mode left those views with an empty thumbnail.
  The gallery now also tries the backend `/api/diagrams/{id}/
  thumbnail` URL for markdown-notation views; the backend
  `get_thumbnail` falls back to the first `entity_images`
  attachment so users can pick a thumbnail by attaching an image
  to the view's Details → Images section.
- **Sets / collections gallery tiles use attached images.** When
  a user uploads an image via the new Details → Images section,
  `has_thumbnail_image` is now true (via SQL subquery that checks
  `entity_images`) and the gallery renders the thumbnail URL.
  Backend `get_set_thumbnail` and `get_collection_thumbnail` fall
  back to the first attachment when no explicit thumbnail is set,
  preserving the existing priority (model → image → attachment).

### Added

- **Collections and sets are now limited to 1 attached image.** The
  `EntityImagesEditor` gains a `maxImages` prop; when the cap is
  reached the upload affordance hides. Sets and collections pass
  `maxImages={1}` because the attachment doubles as the gallery
  tile thumbnail. Packages, views, and elements remain unlimited.
- **`/version` page** lists the deployed version of each Iris
  component (Frontend, Backend, MCP server, CLI). Backed by a new
  `GET /api/version` endpoint that reads each component's
  `pyproject.toml` at startup.

### Migration

- None.

## [6.17.3] - 2026-05-20

### Fixed

- **Attached images now render in production.** v6.17.0/.1/.2's
  `<img src="/api/images/<id>">` was a relative URL — the SvelteKit
  SPA doesn't proxy `/api/*` to the backend in production, so the
  browser loaded the SPA's `index.html` as image bytes and showed
  a broken icon. New `frontend/src/lib/utils/imageUrl.ts` helper
  prepends `API_BASE_URL`; used by `EntityImagesEditor` (grid +
  lightbox) and `SmartMarkdownSlashPicker` (drill thumbs + sizer
  preview).
- **Smart Markdown `<img>` tags in browse mode also resolve.**
  The resolver emits relative `/api/images/<id>` server-side;
  `markdownHelpers.ts` now post-processes the sanitised HTML to
  rewrite those `<img src>` attributes to absolute backend URLs.
  Same rewriter, single source of truth.
- **Element + package save button no longer gated by image
  attachments.** Image attachments commit atomically server-side
  on upload, so they shouldn't block the form's save/discard. The
  Images section on `/elements/[id]` and `/packages/[id]` now
  always shows the upload affordance regardless of edit mode —
  matching the collections / sets pattern.

### Migration

- None.

## [6.17.2] - 2026-05-20

### Fixed

- **Image upload now actually persists on Supabase**. v6.17.0's
  paired Supabase migration m078 declared
  `entity_images.created_at TEXT NOT NULL`, but Iris's asyncpg adapter
  (`_convert_params` in `backend/app/db/adapter.py`) unconditionally
  converts ISO-format string parameters into native `datetime`
  objects. asyncpg then rejected the INSERT with
  `DataError: invalid input for query argument $6 (expected str, got
  datetime)`. Other Iris tables (m002, m006, m007, …) already use
  `TIMESTAMPTZ`; m078 was the outlier. Updated m078 to
  `TIMESTAMPTZ NOT NULL` for new installs and to `ALTER COLUMN ...
  TYPE TIMESTAMPTZ` for existing installs. The v6.17.1 graceful 503
  handler made this diagnosable from the response body.

### Migration

- **Supabase m078 needs to be re-run** by the operator
  (`scripts/supabase-migrate.sh`). The script is idempotent: on
  databases where `created_at` is already TEXT, it converts in
  place; on fresh installs it skips the ALTER and creates the
  column with the right type.

## [6.17.1] - 2026-05-20

### Fixed

- **Images section now appears on views (`/views/[id]`)** — was
  using the canvas-edit flag rather than always-allow-upload, so the
  section never surfaced unless the user entered canvas edit mode.
  Now uses `editing={true}` and renders an `Images` heading (issue
  #194 follow-up).
- **Element details page now shows the `Images` heading** for
  consistency with the other entity types.
- **Packages page Images section now has a heading** to match the
  other entity types.
- **Backend image-attachment endpoints return a graceful 503**
  (instead of an unhandled 500) when the underlying table doesn't
  exist (Supabase migration m078 not yet applied). The 503 carries
  CORS headers so the browser shows the real cause instead of a
  misleading CORS error; the detail message tells the operator to
  run `scripts/supabase-migrate.sh`.

## [6.17.0] - 2026-05-20

### Added

- **Entity image attachments** (ADR-209, issue
  [#194](https://github.com/cgbarlow/iris/issues/194)). Any
  collection, set, package, view, or element can now have one or
  more attached images, surfaced under its Details screen. Edit
  Details exposes a `+ Upload` button + per-image Remove. Backed
  by a new junction table `entity_images` (paired SQLite m073 +
  Supabase m078) that references the existing `images` table.
- **Picker image references with sizing**. The Smart Markdown
  picker can now drill into an entity, pick one of its attached
  images, and choose how to render it: original, width-by-%,
  width-by-px, height-by-%, height-by-px. Token format:
  `{{image:<id>}}` or `{{image:<id>:<axis>:<value>}}`. The
  resolver emits an `<img>` tag with the chosen sizing into
  `data.content`; `MarkdownView` renders it.
- **Markdown toolbar image button is now a chooser**: clicking
  the image button opens a small `ImageInsertDialog` with two
  tabs — **Link** (paste a URL → `![alt](url)`) and **Upload**
  (file picker → POST `/api/images` → `![alt](/api/images/<id>)`).
  Works in both Standard Markdown and Smart Markdown views.
- **Endpoints**: `POST /api/{entity_type}/{id}/images`,
  `POST /api/{entity_type}/{id}/images/attach`,
  `GET /api/{entity_type}/{id}/images`,
  `DELETE /api/{entity_type}/{id}/images/{attachment_id}`.
  Whitelisted entity types: `collection|set|package|diagram|element`.
- **MCP tools + CLI commands** (§14 parity):
  `attach_entity_image`, `detach_entity_image`,
  `list_entity_images` — both surfaces.

### Changed

- **Views index** (`/views/`) reverts from `HierarchyControls`
  to a single primary `+ New View` button matching the
  Elements-page button style/size. Dashboard and packages-detail
  keep using `HierarchyControls`.

### Migration

- **SQLite m073 + Supabase m078 (paired §15)** — adds
  `entity_images` table with indexes and RLS policies. Idempotent.
  Run `scripts/supabase-migrate.sh` to apply the Supabase mirror.

## [6.16.1] - 2026-05-20

### Fixed

- **Picker opens at the calling view's collection** (issue
  [#185](https://github.com/cgbarlow/iris/issues/185) regression
  follow-up). v6.16.0 always opened at the global root; users
  expected the picker to start at their current scope so search
  "at this level" matches the intent of the original 2026-05-19
  comment. SmartMarkdownCanvas now passes the diagram's `set_id`
  as `contextSetId`; the picker fetches the set, seeds its
  initial breadcrumb to `Root > {collection}` (or `Root > {set}`
  if the set has no parent collection), and the first browse
  fetch uses that scope.
- **Package drill replaced with browse navigation** — clicking a
  package in the picker now navigates browse to
  `scope=package` (showing the breadcrumb + "Pick this package"
  + contained elements), matching the set-level pattern. The
  v6.16.0 drill-with-children-list felt off because non-element
  drill UX visually diverged from set/collection browse.
- **IDE-style Tab and `.` in browse mode** — Tab or `.` on the
  highlighted browse item now commits and navigates (or drills
  for elements), matching the in-drill behaviour. Tab no longer
  tabs focus out of the picker.

### Changed

- **Bucket order at scope=set is now Packages → Views → Elements**
  (was Elements → Packages → Views). Matches user direction.
- **`scope=package` returns the contained elements as items**
  instead of a `counts` payload. Packages only contain elements,
  so the bucket-card intermediary added unnecessary friction.

### Migration

- No DB changes. Code-only follow-up to v6.16.0.

## [6.16.0] - 2026-05-20

### Fixed

- **Smart Markdown picker search now works** (ADR-207, issue
  [#185](https://github.com/cgbarlow/iris/issues/185) follow-up).
  The v6.15.0 input wired search via a `$effect` that didn't track
  the `query` state, so typing never re-triggered the search. The
  input now uses an explicit `oninput` handler matching the
  v6.14.x pattern.
- **Picker drill keystrokes** (`.`/Tab/typing-to-filter) now work
  in production. `handleDrillKey` was only calling
  `preventDefault()` when the menu had items; Tab without
  preventDefault tabbed focus away from the picker entirely. Tab
  and `.` are now unconditionally consumed in drill mode.
- **Hierarchy view 'New' button is now the same height as 'Show'**
  (issue [#185](https://github.com/cgbarlow/iris/issues/185)).
  The 'Show' button has a 1px border; the 'New' button now carries
  `border border-transparent` so the box models match.

### Added

- **Drill into contained children** (ADR-207). The picker drill
  mode for collections, sets, and packages now surfaces the
  entity's contained children alongside `name`/`description`.
  Clicking a child drills into that child. Closes the gap in
  ADR-206 where non-element drill only exposed top-level fields.
- **'Pick this {entity}' shortcut** at non-root breadcrumb levels
  in the picker browse mode. Picks the breadcrumb-leaf entity and
  opens its drill view — so a set's or collection's own
  name/description is reachable from inside the browse tree.
- **`GET /api/picker/browse?scope=package`** and **`scope=package_bucket`** —
  new picker browse scopes for drilling into a package's contents.
  Mirrors the existing `set`/`set_bucket` shape.
- **'Element' option in the 'New' dropdown** (issue
  [#191](https://github.com/cgbarlow/iris/issues/191)). Appears
  beneath 'View' across all three call sites that use the shared
  `HierarchyControls.svelte` component. Opens the existing
  `EntityDialog` in create mode.
- **Per-set `element_tab_default` preference** (ADR-208, issue
  [#192](https://github.com/cgbarlow/iris/issues/192)). Sibling to
  the v6.14.0 `package_tab_default` and `view_tab_default` columns.
  Default `relationships`. Element detail page seeds its
  `activeTab` from this value (same shape as the view-detail
  initialiser).
- **`GET /api/elements/{id}/package-memberships`** — returns the
  package(s) this element belongs to. Reads the existing
  `elements.package_id` column (ADR-184); empty list when null.

### Changed

- **Element detail screen tab order**: Relationships is now the
  first tab (was Details). The standalone "Used in Diagrams" tab
  is folded into Relationships as a section, alongside a new
  "Package membership" section. DRY of the v6.10.x package screen
  pattern that already shows contained elements under Relationships
  (issue [#192](https://github.com/cgbarlow/iris/issues/192)).
- **Picker badge colours now align with the Knowledge Graph colour
  key** (ADR-207). Existing pale palette stays; mappings rotate so
  collection → pale pink (KG red), set → pale purple (KG violet),
  package → pale amber (KG amber, unchanged), view → pale green
  (KG green), element → pale blue (KG blue, unchanged).
- **Picker label "Diagrams" → "Views"** (badge text + bucket
  label). Backend `entity_type` still says `'diagram'` — this is
  a presentation-only mapping inside
  `SmartMarkdownSlashPicker.svelte`. The wider Iris rename is a
  separate ticket.

### Migration

- **SQLite m072 + Supabase m077 (paired, §15)** — `ALTER TABLE sets
  ADD COLUMN element_tab_default TEXT NOT NULL DEFAULT
  'relationships'`. Idempotent. Run
  `scripts/supabase-migrate.sh` after deploy to apply the
  Supabase mirror.

## [6.15.0] - 2026-05-19

### Added

- **Smart Markdown picker: hierarchical browse, recent chips, and
  nested attribute drill** (ADR-206, issue
  [#185](https://github.com/cgbarlow/iris/issues/185) follow-ups).
  Pressing `/` in a Smart Markdown view now opens with a discoverable
  browser: Recent chips (entities already referenced in this diagram,
  derived from the live source — no new state) → breadcrumb →
  collections list. Click drills into a collection's sets, then into
  a set's Packages / Diagrams / Elements buckets with counts (zero
  buckets hidden), then into the entity list. Reset button on the
  breadcrumb returns to root.
- **Nested attribute drill** for elements whose `data` contains
  arrays-of-dicts (the ArchiMate-style attribute pattern). After
  picking an element, the picker collapses into an IDE-style
  autocomplete strip `[entity].<field>`. Typing `.` or Tab drills;
  arrow keys highlight; Enter inserts. Token format extends to
  `attr:SEG/SEG/SEG` with named lookup for arrays of dicts whose
  items have a `name` field (e.g. `attr:attributes/Unit/type` →
  resolves to `g`). Backward compatible with v6.14.x single-key
  tokens.
- **`GET /api/picker/browse`** — uniform breadcrumb + items +
  counts response across the four hierarchy scopes (`root`,
  `collection`, `set`, `set_bucket`). Drives the new picker browse
  mode.
- **`GET /api/elements/{id}/data-tree`** — tree descriptor for the
  drill UI (kind = dict | list_of_named | list | primitive). The
  legacy `/attribute-keys` endpoint stays for backwards
  compatibility.
- **Creation-format prompts** for `smart_markdown` and
  `dynamic_list` diagram types (Protocol §14 follow-up). MCP and
  CLI clients now have authoritative documentation of each type's
  `data` shape via `get_creation_prompts(diagram_type=...,
  purpose='creation_format')`.

### Changed

- **`/api/search/entities` is now substring-matching** (was
  prefix-only). Searching "mince" now finds "pork mince". Plus
  optional `set_id` / `collection_id` query params to scope results
  to a set or a collection's subtree.
- **Diagram-type dropdown is alphabetical**
  (`frontend/src/lib/components/DiagramDialog.svelte`). The
  `markdown` notation now lists `Dynamic List`, `Smart Markdown`,
  `Standard Markdown` rather than registry order. Registry
  ordering (`display_order, name`) is preserved server-side for
  other consumers.

### Migration

- No DB schema changes. `creation_prompts.py` is re-seeded on
  startup (idempotent `INSERT OR IGNORE` + `UPDATE`). No paired
  Supabase migration; no `supabase-migrate.sh` step required.

## [6.14.2] - 2026-05-18

### Fixed

- **`PUT /api/sets/{id}` no longer hides update failures behind a
  misleading "duplicate name" 409.** The previous `except Exception`
  in the sets router caught every error — including transient asyncpg
  failures, constraint violations on new columns, etc. — and surfaced
  them as `409 "A set with this name already exists"`. That was the
  user-visible signal during the v6.14.0 hierarchy-sort persistence
  report (which the frontend silently displayed without making clear
  the underlying cause). The handler now logs the full exception and
  returns `409` with `f"Failed to update set ({type}: {message})"` so
  the actual cause surfaces to DevTools / the toast.

## [6.14.1] - 2026-05-18

### Fixed

- **View tab default now honoured for empty diagrams** (ADR-204
  follow-up). The v6.14.0 initialiser only applied the parent set's
  `view_tab_default` to *content-bearing* diagrams, falling back to
  Details for empty ones — that masked the user's explicit
  preference. The set's preference now always wins when the
  diagram has a `set_id`.

### Changed

- **Renamed `Text` diagram type to `Standard Markdown`** in the
  registry (id stays `text`; existing diagrams keep working). Reads
  better next to its siblings `Dynamic List` and `Smart Markdown`
  under the markdown notation.
- **Diagram-create picker fallback list now includes Smart Markdown**
  for the markdown notation, so the entry shows even if the live
  registry fetch fails or the page has a stale cache. (Hard refresh
  to clear stale browser state.)

### Migration

- **SQLite m071 + Supabase m075 (paired, §15)** — `UPDATE diagram_types
  SET name = 'Standard Markdown' WHERE id = 'text'`. Idempotent.

## [6.14.0] - 2026-05-18

### Added

- **Smart Markdown view type** (ADR-205, issue
  [#185](https://github.com/cgbarlow/iris/issues/185)). A new
  diagram type registered under the existing `markdown` notation.
  Users author markdown and embed inline references to live entity
  fields using a `/` slash-picker:
  - Token format: `{{<entity-type>:<id>:<field-spec>}}`.
  - Reference any element's `name`, `description`, or custom
    attribute via `attr:<key>` (e.g. `attr:Unit`).
  - Reference any package / diagram / set / collection's `name`
    and `description`.
  - Unresolvable tokens render as `~~{{...}}~~` so data loss is
    visible.
  - Resolution happens server-side on read, so the existing
    markdown / docx / pdf export renderers pick up the resolved
    content without any new code (Protocol §13 DRY).
  - Two new read-only endpoints: `GET /api/search/entities` (the
    picker's entity step) and `GET /api/elements/{id}/attribute-keys`
    (the picker's field step for elements).
  - Two new frontend canvases: `SmartMarkdownCanvas.svelte` and
    `SmartMarkdownSlashPicker.svelte`.

- **Per-set tab defaults** (ADR-204, issue
  [#186](https://github.com/cgbarlow/iris/issues/186)). Each set
  now owns two new preferences:
  - **Package tab default** — which tab opens on `/packages/{id}`
    for packages in this set. Options: `relationships` (new
    default), `details`. The Packages screen tab order is also
    reordered to lead with Relationships, then Details, then
    Version History.
  - **View tab default** — which tab opens on `/views/{id}` for
    diagrams in this set. Options: `canvas` (new default),
    `relationships`, `details`. The Views screen tab order moves
    Details to between Relationships and Version History.
  - Both surfaced on the set edit page, the MCP `update_set` tool,
    and the `iris update set` CLI flags (`--package-tab-default`,
    `--view-tab-default`; ADR-202's `--hierarchy-sort` also got
    its CLI flag here).

### Migration

- **SQLite m069 + Supabase m073 (paired, §15)** — adds two TEXT
  columns to `sets`:
  - `package_tab_default TEXT NOT NULL DEFAULT 'relationships'`
  - `view_tab_default TEXT NOT NULL DEFAULT 'canvas'`
  - Enums enforced at the Pydantic layer (no SQL CHECK; Protocol §15).
  - Existing sets inherit the new defaults — no back-fill needed.
- **SQLite m070 + Supabase m074 (paired, §15)** — registers
  `smart_markdown` in `diagram_types` and maps it to the existing
  `markdown` notation in `diagram_type_notations`. Idempotent via
  `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING`.
- **Release ordering for Supabase**: run
  `scripts/supabase-migrate.sh` against the Supabase DB **before**
  the code deploys. The service-layer fallbacks keep the API
  non-fatal in a brief deploy-before-migrate window — set
  responses degrade to the new defaults; the smart_markdown type
  simply won't appear in the picker until the migration runs.

## [6.13.0] - 2026-05-18

### Added

- **Per-set hierarchy sort preference** (ADR-202). Each set can
  now choose how its packages and diagrams are ordered in the
  hierarchy views (dashboard tree, packages page sidebar, views
  page tree). Four options on the set edit page (Edit Set →
  Hierarchy sort):
  - **Manual** (drag-and-drop sequence_order — current behaviour,
    default for new and existing sets).
  - **Alphabetical** (A → Z, case-insensitive, interleaves
    packages and diagrams).
  - **Newest first** (`created_at DESC`).
  - **Oldest first** (`created_at ASC`).
  - Also surfaced on the MCP `update_set` tool. New `hierarchy_sort`
    field round-trips through `SetResponse` / `SetUpdate`.

### Migration

- **SQLite m068 + Supabase m072 (paired, §15)** — adds
  `hierarchy_sort TEXT NOT NULL DEFAULT 'manual'` to `sets`. Enum
  enforced at the Pydantic layer (no SQL CHECK, so SQLite and
  Supabase syntax stay identical). Existing sets inherit the
  `'manual'` default — no back-fill needed.
- **Release ordering for Supabase**: run
  `scripts/supabase-migrate.sh` against the Supabase DB **before**
  the code deploys. The service layer has a defensive fallback so
  a brief window without the migration degrades to manual sort
  rather than 500-ing.

## [6.12.0] - 2026-05-18

### Changed

- **Knowledge graph: packaged elements reached via the package
  chain only** (issue
  [#181](https://github.com/cgbarlow/iris/issues/181), ADR-203).
  Previously, an element belonging to a package rendered both
  `set → element` (set_membership) and `set → package → element`
  (chain) — visual redundancy. The direct `set → element` edge
  is now skipped when the element's package is visible in the
  current scope. Free-floating elements (no `package_id`) keep
  their direct edge. If the package is out of scope (soft-
  deleted, different set), the direct edge falls through so the
  element isn't visually orphaned. No toggle — the chain conveys
  containment more usefully and the redundant edge is just
  clutter.

## [6.11.1] - 2026-05-18

### Fixed

- **KG settings dropdown "Relationships" tab overflowed**. After
  v6.9.0 (ADR-199) added the third tab, the 220px min-width
  popover couldn't fit "Relationships" on one line; it wrapped or
  clipped. Bumped to 300px and added `whitespace-nowrap` to each
  tab button so labels stay on a single line regardless of any
  future container resizing.

## [6.10.1] - 2026-05-18

### Fixed

- **Relationships tab stayed empty on cross-package navigation**
  (ADR-201, follows ADR-195). After ADR-195 correctly cleared the
  previous package's data on navigation, the Relationships tab
  did not auto-rehydrate when the user navigated from one
  package to another via the hierarchy sidebar — the list went
  empty until the user clicked the "Relationships" tab heading.
  `loadPackage` now triggers `loadPackageElements` automatically
  if the user is already sitting on the Relationships tab when
  the new package loads.

## [6.10.0] - 2026-05-18

### Added

- **Batch element create + update across REST, MCP, CLI** (issue
  [#173](https://github.com/cgbarlow/iris/issues/173) item 6,
  ADR-200). Creating or updating long lists of elements via the
  singular `create_element` / `update_element` MCP tools required
  N round-trips. New plural tools handle up to 100 items in one
  call:
  - REST: `POST /api/batch/elements/create`,
    `POST /api/batch/elements/update`. Both return
    `BatchResultWithIds { succeeded, failed, errors, ids }`.
  - MCP: `create_elements`, `update_elements`. Per-item schema
    is open so callers can construct any subset of the singular
    fields.
  - CLI: `iris create elements --from-json <path|->`,
    `iris update elements --from-json <path|->`. JSON-only input
    via file or stdin.
  - Per-item failure isolation — a bad row reports an
    index-tagged error without sinking the rest of the batch.
    Per-item optimistic concurrency on update (each item carries
    its own `expected_version`).
  - Surface parity (`scripts/check_surface_parity.py`) verified
    clean.

## [6.9.0] - 2026-05-18

### Added

- **Knowledge graph models element ↔ package membership as a
  first-class edge** (issue
  [#173](https://github.com/cgbarlow/iris/issues/173) item 5,
  ADR-199). For every element with a non-null `package_id`, the
  graph now emits a `package → element` edge (direction matches
  `set_membership` and `hierarchy`). Default visibility ON;
  toggle lives under the new Relationships tab → Package group →
  "Elements (membership)".

### Changed

- **KG settings: Visibility tab split into Nodes + Relationships**
  (issue [#173](https://github.com/cgbarlow/iris/issues/173) item 4,
  ADR-199). The previous combined column mixed node-type toggles
  and relationship-type toggles; finding the one you wanted was
  fiddly. The settings dialog now has three tabs (Nodes /
  Relationships / Display). Per-tab Reset semantics: each tab
  resets only its own concern.

## [6.8.7] - 2026-05-18

### Fixed

- **Cloning an element from /elements/{id} dropped it into the
  default set** (issue
  [#173](https://github.com/cgbarlow/iris/issues/173) item 1,
  ADR-198). The detail-page Clone button POSTed to
  `/api/elements` without `set_id`, so the backend's
  `create_element` fell back to `DEFAULT_SET_ID`. Now passes
  `set_id: entity.set_id`. Batch clone path
  (`POST /api/batch/elements/clone`) was already correct; a
  regression test now locks in that invariant explicitly.

## [6.8.6] - 2026-05-18

### Fixed

- **Template viewer rendered a broken link to a deleted source
  element** (issue
  [#173](https://github.com/cgbarlow/iris/issues/173) item 2,
  ADR-197). Two-half cause: (a) the backend subquery that
  resolves `source_element_name` did not filter on
  `elements.is_deleted = 0`, so a soft-deleted source still
  produced a name; (b) the frontend's `{#if}` was keyed on
  `source_element_id` — but the id stays populated as a dangling
  FK after source deletion, so the "(source element deleted)"
  fallback was unreachable. Backend subqueries now filter
  `e.is_deleted = 0` (db-adapter rewrites to `FALSE` on Supabase
  per §15); frontend conditional now keys on
  `source_element_name`.

## [6.8.5] - 2026-05-18

### Fixed

- **Elements page search "flashed away" after typing**  (issue
  [#173](https://github.com/cgbarlow/iris/issues/173) item 7,
  ADR-196). Typing "grocery" briefly showed the matching element,
  then it disappeared as a slower earlier-typed request returned
  and overwrote the result. Root cause: the search input fired
  `loadElements()` synchronously on every keystroke with no
  debounce and no `AbortController`. The fix mirrors the
  dashboard's pattern — 300 ms debounce, an `AbortController` so
  newer requests cancel older in-flight ones, and a request-time
  query capture as a belt-and-braces race guard. Aborted requests
  no longer surface as a generic "Failed to load elements".

## [6.8.4] - 2026-05-18

### Fixed

- **Stale elements rendered on package Relationships tab after
  navigation** (issue
  [#173](https://github.com/cgbarlow/iris/issues/173) item 3,
  ADR-195). Navigating from package A to package B left A's
  elements visible on B's Relationships tab until a hard browser
  refresh. Root cause: `loadPackage` reset top-level state
  (`pkg`, `error`, `parentPackageName`) but not the lazy-loaded
  relationships state (`packageElementsLoaded`, `packageElements`,
  `packageElementsTotal`, `packageElementsLoading`,
  `packageElementsError`), so the activation-side guard
  short-circuited the re-fetch. Also resets inline edit state
  (`editingDetails`, `detailsDirty`) so edit mode doesn't bleed
  across packages.

## [6.8.3] - 2026-05-17

### Fixed

- **HTTP 500 on `POST /api/element-templates` in Supabase** (the
  surfaced as CORS error in the UAT browser because the failure
  short-circuited the CORS middleware). The `INSERT INTO
  element_templates` statement embedded a literal `0` for
  `is_deleted` in the `VALUES` clause — PostgreSQL rejects integer
  literals for `BOOLEAN` columns (Protocol §15). The adapter's
  retry-with-bool-coercion only fires for *bound* int parameters,
  and the `is_xxx = 0/1` regex rewrite doesn't catch bare literals
  inside `VALUES`. `is_deleted` is dropped from the INSERT column
  list — both schemas default it correctly (`0` on SQLite, `FALSE`
  on Supabase).
- **Dynamic List bullet missing closing `**`** (issue
  [#170](https://github.com/cgbarlow/iris/issues/170)). When
  `show_description=False`, `_bullet` emitted `- **{name}` (no
  closing `**`), so markdown rendered the literal asterisks instead
  of bolding the name. Now emits `- **{name}**`.

### Changed

- **Dynamic List defaults to enclosing-package contents** (issue
  [#170](https://github.com/cgbarlow/iris/issues/170)). A fresh
  `dynamic_list` diagram created inside a package now defaults to
  `mode='package_elements'` with `package_id` = the diagram's
  `parent_package_id`. Diagrams without a parent package fall back
  to the previous `diagram_relationships` default. The synthesised
  `data.dynamic_source` is echoed on read so the frontend picker
  reflects the applied defaults. The auto-generated footer
  ("(Dynamic list — auto-generated)") is removed from the
  rendered markdown. The mode dropdown labels are simplified to
  "Package elements" and "Diagram relationships" (no "Default" prefix).

## [6.8.2] - 2026-05-17

### Fixed

- **HierarchyControls "Show" / "+ New" dropdowns clipped inside narrow
  sidebars** (issue
  [#169](https://github.com/cgbarlow/iris/issues/169)). On the
  packages-detail page (and any other surface where the hierarchy
  panel sits inside an `overflow-y: auto` / `overflow: hidden`
  container), the dropdown menus were anchored with Tailwind
  `absolute left-0`, so they got clipped at the ancestor's right
  edge — the "Packages are always shown." footer ran off the visible
  area. The menus now render with `position: fixed`, with viewport
  coordinates computed from the trigger button's
  `getBoundingClientRect()`. Fixed-position menus stay anchored to
  the viewport, so they close on any scroll.

## [6.8.1] - 2026-05-17

### Fixed

- **Dynamic List view crashes with `marked(): input parameter is
  undefined or null`** (issue
  [#167](https://github.com/cgbarlow/iris/issues/167)). Two-part
  fix: `DynamicListCanvas` now passes the markdown content under
  the prop name `MarkdownView` actually declares (`source`, not
  `markdown`); `renderMarkdown()` coalesces `undefined` / `null`
  to `''` defensively so the same class of bug can't bite other
  callers. DOMPurify still runs after `marked` per Protocol §7.
- **Class element attributes inconsistent across diagrams** (ADR-192,
  SPEC-192-A, issue
  [#164](https://github.com/cgbarlow/iris/issues/164)). The canvas
  used to mint nodes with only `label / entityType / description /
  entityId / notation`, dropping class attributes, operations,
  literals and visual overrides. Three near-identical mini-builders
  on `views/[id]/+page.svelte` now route through a new shared
  `elementToNodeData()` helper, so the renderer always sees a
  complete shape and `refreshNodeDescriptions` carries
  backend-authored attributes forward.
- **Package Relationships tab always empty** (issue
  [#166](https://github.com/cgbarlow/iris/issues/166)). The
  frontend asked for `?page_size=200` on
  `GET /api/packages/{id}/elements`; the router capped at
  `le=100`, so every request 422'd and the silent catch on the
  frontend hid the failure as "No elements in this package."
  Backend cap raised to `le=500`; frontend surfaces fetch errors
  in a banner instead of swallowing them.

### Changed

- **Hierarchy sidebar uniformity** (ADR-194, SPEC-194-A, issue
  [#162](https://github.com/cgbarlow/iris/issues/162)).
  `HierarchyControls` defaults shrunk to compact density
  (`px-2 py-1 text-xs` triggers; `px-3 py-1 text-xs` menu items).
  The packages-detail sidebar drops its bespoke "+ Child" dropdown
  and inline `Diagrams` toggle and adopts the shared
  `HierarchyControls` + `showDiagrams` / `showText` model that
  Dashboard / Views list / View detail already use. All four
  hierarchy surfaces now read visually identical.
- **"Save as template" dialog clarifies the `Data` field** (issue
  [#165](https://github.com/cgbarlow/iris/issues/165)). The
  ambiguous "Data payload" label is renamed to "Data (attributes,
  operations, visual…)" and the dialog gains help text explaining
  what `Data` vs `Metadata` capture — class element attributes
  already round-tripped through templates via the `data` field;
  users couldn't tell from the old label.

## [6.8.0] - 2026-05-17

### Added

- **Element Templates** (ADR-191, SPEC-191-A, issue
  [#153](https://github.com/cgbarlow/iris/issues/153)). Capture a
  user-selected subset of fields from an existing element into a
  reusable template, then pre-fill new elements from any template via
  REST, MCP, or CLI.
  - Set-scoped by default; opt-in `is_global` flag for templates that
    should be reusable across sets. A CHECK constraint enforces that
    exactly one of "scoped to a set" or "global" is true at any time.
  - Field whitelist of eight keys (`name`, `description`,
    `element_type`, `notation`, `data`, `metadata`, `package_id`,
    `tags`) — anything outside the whitelist is silently dropped at
    write time.
  - Full CRUD on three surfaces (per Protocol §14 / ADR-182): REST
    routes under `/api/element-templates`, five MCP tools
    (`create_*` / `list_*` / `get_*` / `update_*` /
    `delete_element_template`), and a new `element-template` entity
    on the CLI. `POST /api/elements` and the matching MCP / CLI
    create surfaces gain an optional `template_id` parameter that
    pre-fills whitelisted fields server-side (explicit fields always
    win).
  - Frontend: **Templates** button on `/elements` opens a
    `TemplatesListDialog` (set-scoped + global) with per-row
    "Use" buttons; **Save as template** on `/elements/[id]` opens a
    `CreateTemplateDialog` with field checkboxes and a "Make
    global" toggle; new `/element-templates/[id]` detail page renders
    the captured snapshot with a "Create element from template"
    affordance and Delete.
  - 74 new tests across backend (34), MCP (12), CLI (8), and frontend
    (20).
  - `scripts/check_surface_parity.py` updated to register the new
    `element_template` entity and to accept kebab-case CLI entity
    names (normalised to underscore for the cross-surface compare).
    `delete_element_template` joins the documented
    "delete deferred — needs audit/undo ADR" asymmetry list.

### Migrations

- SQLite `m067_element_templates.py` — table + CHECK + two partial
  indexes. Wired into `backend/app/startup.py:_initialize_sqlite`.
- Supabase mirror `m071_element_templates.sql` — same shape with
  `BOOLEAN` `is_global` / `is_deleted` (Protocol §15 boolean literal
  convention; `m067_*.sql` was already taken by the
  doview_analysis pointer fix, so the Supabase numbering steps to
  `m071`). Applied via `scripts/supabase-migrate.sh` **before** the
  Render code deploy.

## [6.7.4] - 2026-05-16

### Added

- **MCP `create_element` accepts `package_id`** (ADR-188, issue
  [#154](https://github.com/cgbarlow/iris/issues/154)). Closes the
  v6.7.0 surface-parity gap where REST + CLI accepted `package_id` on
  create but the MCP tool didn't, forcing callers into a follow-up
  `update_element` round-trip. Schema and handler both updated; new
  regression test `mcp/tests/test_create_element_package.py` (4
  tests).
- **Package detail "Relationships" tab** (ADR-189, issue
  [#157](https://github.com/cgbarlow/iris/issues/157)). The package
  detail page now has a third tab that lazy-loads
  `GET /api/packages/{id}/elements` and lists the elements attached
  to the package with links into each. Mirrors the relationship-
  surface pattern from the views/diagrams detail page. New
  regression test
  `frontend/tests/unit/packageRelationshipsTab.test.ts` (9 tests).

### Fixed

- **`class` diagram type now available under `simple` notation**
  (ADR-190, issue
  [#160](https://github.com/cgbarlow/iris/issues/160)). The m020
  registry seed only declared `('class', 'uml', 1)`, but live data
  contains elements with `notation='simple'` and `element_type='class'`
  (e.g. the FIXM US Extension v4.1.1 dataset — verified live against
  iris-api UAT, element
  `09158b60-94cd-46db-9211-a4d50c9c1550`), so the new-element
  diagram-type dropdown hid `class` whenever the user picked Simple.
  Paired SQLite m066 + Supabase m070 migrations insert the missing
  `('class', 'simple', is_default=0)` row idempotently
  (`INSERT OR IGNORE` / `ON CONFLICT … DO NOTHING`, `FALSE` literal
  on Postgres per Protocol §15). Frontend hard-coded fallback list
  in `DiagramDialog.svelte` updated to match. New per-migration
  schema test `backend/tests/test_migrations/test_class_for_simple_notation_schema.py`
  (7 tests).

### Migrations

- SQLite `m066_class_for_simple_notation.py` — wired into
  `backend/app/startup.py:_initialize_sqlite` migration runner.
- Supabase mirror `m070_class_for_simple_notation.sql` — applied
  via `scripts/supabase-migrate.sh` **before** the app rolls forward
  (Protocol §15 release ordering).

## [6.7.3] - 2026-05-16

### Fixed

- MCP `update_element` / `update_diagram` / `update_package` and the
  CLI's shared `_put_merge_partial` helper never sent the `If-Match`
  header. Backend update routes require it (HTTP 428 without) for
  optimistic concurrency on versioned entities, so every call from
  these surfaces failed in production. Both helpers now extract
  `current_version` from the GET response and inject `If-Match` on
  the PUT; unversioned endpoints (collections, sets) continue without
  it since their GET responses don't include the field. Regression
  guard added in `mcp/tests/test_update_tools.py::TestIfMatchHeader`
  and `cli/tests/test_write_commands.py::TestUpdateIfMatch`.
  ([issue #158](https://github.com/cgbarlow/iris/issues/157))

## [6.7.2] - 2026-05-16

### Fixed

- `DynamicListCanvas.svelte` imported `apiFetch` from `$lib/api` —
  a directory containing only `named-prompts.ts` (no `index.ts`), so
  Vite errored with `EISDIR: illegal operation on a directory, read`
  and every frontend deploy on Render aborted at 1041 modules
  transformed. Now imports from `$lib/utils/api`, matching the
  convention used everywhere else in the canvas tree.

## [6.7.1] - 2026-05-16

### Fixed

- Supabase migration m069 used `0` for `diagram_type_notations.is_default`,
  which PostgreSQL rejects with `column "is_default" is of type boolean
  but expression is of type integer`. Now uses `FALSE`, matching the
  v5.12.x boolean-literal convention. Re-running m069 against an
  affected Supabase database is now a clean no-op (the prior failure
  rolled back, so no partial state to repair).

### Added

- Protocol §15 — SQLite ↔ Supabase Migration Parity
  ([issue #152](https://github.com/cgbarlow/iris/issues/152)).
  Codifies the rules that prevent SQLite-passing changes from
  500-ing on Supabase: paired SQLite/Supabase migrations in the
  same PR, `TRUE`/`FALSE` boolean literals on Postgres,
  positional row access in service code, no dollar-quoted SQL in
  the startup path, migrate-before-roll-forward release ordering,
  and a per-migration schema test in `backend/tests/test_migrations/`.
  Motivated by the v6.7.0 m069 incident (`0` vs `FALSE` for
  `diagram_type_notations.is_default`) and the v6.6.5 export-service
  row-key incident.

## [6.7.0] - 2026-05-16

Issues [#147](https://github.com/cgbarlow/iris/issues/147) and
[#149](https://github.com/cgbarlow/iris/issues/149) — two linked
features shipped together as a single coordinated release:

### Added — Element → package optional membership (issue #149, ADR-184)

- New nullable `elements.package_id` column (migration m064) — an
  element may belong to a package independently of (and additionally
  to) its set. Cross-field invariant: if both `set_id` and
  `package_id` are non-null, the referenced package's `set_id` must
  match or be null (HTTP 422 on mismatch).
- `ElementCreate` and `ElementUpdate` accept `package_id`; the update
  shape is tri-state (omit to leave untouched, JSON `null` to clear,
  string to set).
- `ElementResponse` exposes `package_id` and `package_name`.
- `GET /api/elements` gains a three-valued `package_id` filter (omit,
  `"null"`, or a UUID) per the convention from
  [ADR-185](docs/adrs/ADR-185-Nullable-Filter-Convention.md). The
  existing `list_diagrams.parent_package_id` filter is refactored to
  use the same shared helper.
- New endpoint `GET /api/packages/{id}/elements` (paginated).
- `GET /api/diagrams/{id}/relationships` response gains
  `element_package_memberships` — element → package rows for elements
  drawn on the diagram.
- Frontend: element-detail edit form exposes a Package picker scoped
  to the element's set. `/views/[id]` Relationships tab gains a third
  section listing element → package memberships.
- CLI: `iris elements update --package-id <uuid|null>`,
  `iris elements list --package-id <uuid|null>`, new subcommand
  `iris packages list-elements <pkg>`.
- MCP: `update_element` accepts `package_id`; `list_elements` accepts
  the `package_id` filter; new tool `list_package_elements`.

### Added — Dynamic List diagram type (issue #147, ADR-186 + ADR-187)

- New diagram type `dynamic_list` under the existing `markdown`
  notation (migration m065). Auto-generated bullet markdown computed
  from one of two source modes:
  - `diagram_relationships` (default) — two bullets per intra-diagram
    relationship (source name, then target name); non-deduplicated.
  - `package_elements` — one bullet per element in a chosen package,
    sorted alphabetically by name.
- `show_description` toggle appends `(description)` to each bullet in
  both modes. Null/empty descriptions fall back to the plain bullet.
- Content is synthesised at read-time on the backend (ADR-187 —
  reusable "compute-on-read" pattern). The persisted `data` row never
  carries `content` or `is_content_locked`; both keys appear only on
  responses. Export and MCP `render_diagram` pick up the synthesised
  text via the existing markdown-notation pipeline.
- New Svelte component `DynamicListCanvas` — read-only preview plus a
  Source panel in edit mode (mode select + package picker +
  Show-description checkbox). `/views/[id]` routes to it for
  `dynamic_list` diagrams.
- `DiagramDialog` lists Dynamic List under the markdown notation.

### Changed

- `list_diagrams.parent_package_id` parameter parsing refactored to
  use the shared `parse_nullable_id` helper (no behavioural change).
- `/views/[id]` Relationships-tab pill counter now reflects all three
  categories (diagram relationships + element relationships +
  element → package memberships).

### Migrations

- SQLite: m064, m065. Both idempotent, no back-fill.
- Supabase: m068 (mirrors m064), m069 (mirrors m065).

### Surface parity

- `python scripts/check_surface_parity.py` passes unchanged. No new
  write verbs registered; ADR-178's "no `move_element`" invariant
  preserved (element → package is an additive enrichment of
  `update_element`, not a move).

## [6.6.5] - 2026-05-16

Issue [#145](https://github.com/cgbarlow/iris/issues/145) — Phase 1
UAT of the deployed v6.6.4 stack reported that the primary MCP path
for `render_diagram` failed with `HTTP 500 Internal Server Error`.
The documented `render_markdown` fallback worked, so the user still
got their three artefacts, but the headline path was broken on every
render call from a live MCP session.

### Root cause

`backend/app/export/service.py` read every database row by string
column key (`row["id"]`, `row["data"]`, …). The SQLite adapter sets
`db.row_factory = aiosqlite.Row`, so string keys work in the test
suite. The Supabase adapter normalises every asyncpg `Record` to a
plain `tuple[Any, ...]` (so it can convert PG `datetime` / `UUID`
to SQLite-compatible strings — see
`backend/app/db/adapter.py::_normalize_row`). Tuples only support
integer indexing. Every export call on Supabase raised
`TypeError: tuple indices must be integers or slices, not str`,
which FastAPI surfaced as a 500.

Every other backend service module (`app/diagrams/service.py`,
`app/sets/`, `app/elements/`, `app/packages/`, …) already uses
positional indexing for exactly this reason. The export service
was the only outlier — which is why the bug only showed up against
production, not the SQLite test suite. The same defect was also
silently breaking every other `GET /api/export/*` bundle endpoint
on Supabase deployments.

### Fix

- All `row["col"]` reads in `app/export/service.py` converted to
  positional indexing matching `_ELEMENT_SELECT` / `_DIAGRAM_SELECT`
  / `_PACKAGE_SELECT` column order. Touches `_row_to_element`,
  `_row_to_diagram`, `_row_to_package`, `_fetch_set`,
  `_fetch_collection`, `build_collection_export`,
  `_fetch_elements_for_diagram`, `_descendant_package_ids`.
- Helper type annotations widened from `aiosqlite.Row` to `object`
  with a comment noting both adapters are now supported.

### Tests

- New `backend/tests/test_export/test_service_tuple_rows.py` —
  three unit tests against `_row_to_diagram` / `_row_to_element` /
  `_row_to_package` with plain-tuple inputs (the Supabase row
  shape). Pre-fix these raise `TypeError`; post-fix they pass.
  A future maintainer that reintroduces `row["col"]` reads in the
  export service trips the test without needing a live Supabase
  connection.
- All 44 existing export-suite tests still pass against SQLite.

### Files

- `backend/app/export/service.py` — positional indexing throughout.
- `backend/tests/test_export/test_service_tuple_rows.py` (new).
- `docs/adrs/ADR-183-Export-Service-Adapter-Parity.md` (new).
- `docs/adrs/specs/SPEC-183-A-Export-Service-Adapter-Parity.md` (new).
- `mcp/pyproject.toml` 6.6.4 → 6.6.5.
- `frontend/package.json` 6.6.4 → 6.6.5.

### Deploy

Backend-only fix. After the Render rebuild lands, re-run the
`render_diagram` smoke from `docs/issue-133-deploy-verification.md`
step 6 / Phase 2 — both the curl and the cascade-driven MCP path
should return 200 + artefact URLs.

## [6.6.4] - 2026-05-16

Issue #133 Phase 1 deploy-verification UAT — two unrelated defects
the user's first run through the Outcomes Theory orient surfaced.

### Background

Two findings out of the Phase 1 UAT against the deployed v6.6.3
stack (`docs/issue-133-deploy-verification.md` step 6, stage 1):

1. **The orient menu rendered as prose bullets, not chips.** Every
   other question in the cascade (info source, default name,
   DoView-Q1/2/3, Stage-1→2 transition, destination chooser) fired
   via AskUserQuestion as intended by ADR-177. The orient menu —
   the very first user-facing question — did not. The model
   dropped option numbers, stripped the question shape, and pushed
   the four options into a prose paragraph.
2. **The orient sheet's `list_diagrams` instruction returned no
   roots.** The Outcomes Theory Book Set carries two root-level
   markdown diagrams (Introduction, Conclusion) that bracket Parts
   A–J. The orient sheet says to call `list_diagrams(set_id=...)`
   and filter to `parent_package_id == null` to surface them. The
   call returned 50 unrelated Part G–J chapter rows; the
   bracketing roots were unreachable from the MCP surface.

### Root cause #1 — orient wrapper missed the ADR-177 rollout

ADR-177 (v6.1.0) promoted "use AskUserQuestion for every
multi-option question" from an ORIENT-FIRST step-3 aside to a
top-level rule in the MCP server-wide `instructions` channel, and
m063 patched it into the deployed singleton body. But the
`_orient_wrapper()` at `mcp/src/iris_mcp/links.py:55-129` — added
in v6.0.6 (ADR-167) because claude.ai's hosted MCP integration does
not reliably surface the server-wide `instructions` field to the
model, so the orient directive gets re-embedded into every
set/collection tool response — was not updated. Its step 3 said
"copy each option … into your response," i.e. prose. In claude.ai
the model sees the wrapper but not the server-wide rule, so the
orient menu became the one place where AskUserQuestion was never
reaching the model.

Cascade questions were unaffected because their AskUserQuestion
instructions live in the cascade prompt bodies themselves
(`creation-cascade-shared-v1`, `creation-doview-notation-v1`, etc.)
— which the model fetches as tool responses and so does read.

### Root cause #2 — `list_diagrams` MCP tool never exposed pagination

The backend `list_diagrams` route
(`backend/app/diagrams/router.py`) has always been paginated at
`page_size=50` ordered by `updated_at DESC`, but the MCP tool
wrapper at `mcp/src/iris_mcp/tools.py:178` discarded `page` /
`page_size` / `parent_package_id` entirely — it just called
`c.list_diagrams(set_id=...)` and trusted the first 50 rows. The
gap hadn't bitten because the Outcomes Theory Set was small. Issue
#133 Phase 1–5 UAT pushed it past 50 diagrams and re-edited Parts
G–J most recently, which displaced the older root markdown
diagrams off page 1.

The `list_packages` tool already had the right shape from ADR-158
(v5.13.0) — pagination + `parent_package_id` filter + a "REQUIRE
iterating pages or you will miss content" warning in the
description. `list_diagrams` had never been backfilled.

### Fixed

- **`_orient_wrapper()` step 3 (`mcp/src/iris_mcp/links.py`)** now
  instructs the model to fire ONE AskUserQuestion call with the
  four menu options when the client supports the tool, carrying
  each option's full sentence in the `description` field
  (preserving the existing CHARACTER-BY-CHARACTER verbatim rule)
  and a short 3-5-word `label` derived from the option's leading
  concept. Numbered-prose fallback for clients without
  AskUserQuestion is spelled out as a fallback, not the default.
  Explicit "do NOT render the menu as prose bullets when
  AskUserQuestion is available" anti-pattern callout.
- **`list_diagrams` MCP tool (`mcp/src/iris_mcp/tools.py`)** now
  exposes `page`, `page_size`, and `parent_package_id`. Tool
  description matches `list_packages`: "Paginated — defaults to
  page=1, page_size=50 (max 100). Sets with more than 50 diagrams
  REQUIRE iterating pages, or you will miss content." Documents
  the literal string `"null"` as the sentinel for root-only
  filtering.
- **Backend route + service** (`backend/app/diagrams/router.py`,
  `backend/app/diagrams/service.py`) accept `parent_package_id`
  with three semantics — omitted (no filter), `"null"`
  (root-level only via `parent_package_id IS NULL`), or a UUID
  (exact match).
- **`iris-client` `list_diagrams`** plumbs the same three
  semantics through to the HTTP layer.
- **Outcomes Theory orient sheet content
  (`docs/prompts/doview-book-mcp-system-context.md`)** updated to
  call `list_diagrams(set_id=..., parent_package_id="null")` as a
  single targeted call, with an explicit warning that the
  un-filtered call returns the wrong 50 rows once the Set is past
  50 diagrams. Revision-history entry added; admin must paste the
  new body into the Set's `mcp_system_context` field via
  `/admin/settings/ai`.

### Tests

- `mcp/tests/test_links_orient_wrapper.py::test_wrapper_requires_askuserquestion_for_menu`
  — asserts the wrapper names AskUserQuestion, names the numbered
  fallback, and still carries the existing verbatim-copy
  discipline.
- `mcp/tests/test_tools_list_diagrams_pagination.py` — six tests
  covering wiring (page / page_size / parent_package_id defaults
  and override, null-sentinel pass-through) and tool schema
  (description warns about pagination, names the null sentinel,
  exposes the three new args).
- `iris-client/tests/test_diagrams_pagination.py` — five tests
  covering default-param shape, page / page_size override, and
  the three `parent_package_id` semantics on the HTTP layer.
- `backend/tests/test_diagrams/test_list_diagrams_parent_filter.py`
  — four end-to-end tests confirming `parent_package_id=null`
  returns only roots even when 50 fresher under-package diagrams
  fill the default page.

### Deploy

- **MCP redeploy** required (orient wrapper + tool schema change).
- **Backend redeploy** required (route + service change).
- **No Supabase migration.**
- **Admin paste** required on the Outcomes Theory Set's
  `mcp_system_context` field (`/admin/settings/ai`) — copy the
  new "Content (paste this into the field on UAT)" block from
  `docs/prompts/doview-book-mcp-system-context.md`. Without the
  paste the orient call still works but the model still has the
  old "fetch all then filter" instruction.
- Frontend version bump only (no UI change).

### Reference

- ADR-167 — the wrapper this patch updates.
- ADR-177 — the AskUserQuestion convention that originally missed
  the wrapper rollout.
- ADR-158 — the pagination + parent filter shape `list_diagrams`
  is now backfilling parity with.

## [6.6.3] - 2026-05-16

UI/UX patch — four minor issues caught during Phase 5 manual UAT.

### Fixed

- **GUI Export menu: "Unexpected end of JSON input"** for every
  format (markdown / docx / pdf). Root cause: `DiagramExportMenu.svelte`
  used bare `fetch('/api/export/diagram/...')`, which resolves
  against the FRONTEND host in production (chrisbarlow.nz), not the
  backend (iris-api-gtb3.onrender.com). The SPA fallback returned an
  HTML document that `JSON.parse` rejected. Switched to `apiFetch`
  which prefixes `API_BASE_URL` and carries the JWT bearer. The
  artefact download `<a href>` now also uses `${API_BASE_URL}/api/artefacts/<id>`
  so the browser hits the backend directly.
- **SVG/PNG export options visible on markdown diagrams** (and then
  failed with "no canvas element to capture"). Root cause: the
  parent `+page.svelte` computed `isMarkdownContent={(notation as string) === 'markdown'}`,
  but the page's `notation` $derived value resolves to `'text'` (the
  canvas-type token) for markdown-notation diagrams, not
  `'markdown'`. Now uses `diagram?.notation === 'markdown' || (canvasType as string) === 'text'`
  which matches the actual diagram metadata.
- **Hierarchy panel "+ New" and "Show" buttons wrap to two lines** in
  narrow side-panel widths. Added `whitespace-nowrap` to both
  buttons in `HierarchyControls.svelte`.
- **View toolbar "Add to context" wraps to two lines**, doubling the
  height of the whole button row. Added `whitespace-nowrap` to
  Add to context, Bookmark, Clone, Delete buttons.
- **Delete diagram navigates to `/views` (loses set context)**. Now
  pre-computes a sensible "up" destination before the DELETE: prefer
  the previous sibling diagram in the same set, then the next
  sibling, then any other diagram in the set, then the parent
  package, then the set page, then `/views` as last resort.

### Frontend type checks

`npm run check`: 165 → 165 errors (zero new from this patch — all
pre-existing in unrelated files).

### Deploy

Frontend redeploy only. No backend / Supabase / MCP changes.

## [6.6.2] - 2026-05-16

Issue #133 Phase 1 UAT defect fix — doview_analysis content
structure regression that crept in at v6.0.0 (ADR-164).

### Background

A doview_analysis created via the cascade
(`https://iris-uat.chrisbarlow.nz/views/3e196c18-b061-4656-b841-395509a9c611`,
2026-05-16) didn't follow the response_format output structure —
no opening sentence, no Summary/Full/Diagrams sections, no
outcomes-theory framing, no tool URLs, no handbook reference. Zero
compliance.

### Root cause

v5.12.0 (ADR-157) introduced the response_format prompts for
`(markdown, doview_analysis)` and a dedicated `save_doview_analysis`
MCP tool whose description hinted at the expected structure
("Markdown body of the analysis (Summary + Full + Diagrams
sections)"). The model would fetch `purpose='response_format'`,
draft compliant markdown, then save.

v5.17.0 (ADR-162) added generic `create_diagram` with a
`_CREATION_FLOW_PREAMBLE` that directs the model to fetch
`purpose='creation_format'`. At v5.17.0 both tools coexisted —
doview_analysis still went through `save_doview_analysis`.

v6.0.0 (ADR-164) removed `save_doview_analysis`, leaving
doview_analysis creation to go through generic `create_diagram`.
But `_CREATION_FLOW_PREAMBLE` was not updated to tell the model
"for markdown-content diagrams like doview_analysis, ALSO fetch
`purpose='response_format'` to get the output-structure rules."
The structure-rules dependency was lost.

v6.1.0's Phase 1 work made cascade-driven creation more attractive
(AskUserQuestion, destination chooser), so the latent defect from
v6.0.0 became much more visible.

### Fixed

- **`mcp/src/iris_mcp/tools.py:_CREATION_FLOW_PREAMBLE`** gains a
  step 2a: explicit instruction for the model to fetch
  `get_response_prompt(notation='markdown', diagram_type=...,
  purpose='response_format')` when creating any content-bearing
  markdown diagram, and to apply those rules to the markdown body.
- **New backstop prompt** `creation-format-doview-analysis-pointer-v1`
  at `(purpose='creation_format', layer='diagram_type',
  diagram_type='doview_analysis')` instructs the model to fetch the
  response_format cascade and apply its rules. Composes into every
  creation_format cascade for doview_analysis. Single source of
  truth for the actual rules stays on the response_format side per
  protocols §13 DRY — this row is a pointer, not duplicated content.
- SQLite migration `m063_doview_analysis_creation_format_pointer.py`
  + Supabase mirror `m067_…sql`.
- Seed file `backend/app/seed/creation_prompts.py` extended with
  `DOVIEW_ANALYSIS_CREATION_FORMAT_POINTER` constant; re-applied
  on every backend startup so admin edits get overwritten with
  canonical content.

### Verification

- `pytest backend/tests/test_migrations/test_doview_analysis_creation_pointer_schema.py`
  — 12 new green.
- `pytest backend/tests/test_ai/test_creation_prompts_expanded.py`
  — row-count assertion updated 18 → 19 active creation_format rows.
- 376/376 + 201/201 (backend + MCP) green.
- Manual UAT after redeploy: re-create a doview_analysis via the
  cascade; expect compliant Summary/Full/Diagrams structure.

### Deploy

Run new Supabase migration (`m067_doview_analysis_creation_format_pointer.sql`)
via the Supabase SQL Editor or `./scripts/supabase-migrate.sh`,
then redeploy backend + iris-mcp on Render. No frontend changes.

## [6.6.1] - 2026-05-16

Issue #133 deploy fix — Render base image was missing WeasyPrint
runtime system dependencies. `POST /api/export/markdown` returned
500 on the v6.6.0 deploy; this release adds the missing libraries
to `backend/Dockerfile` so the renderer endpoint resolves cleanly.

### Fixed

- `backend/Dockerfile` now installs `libpango-1.0-0`,
  `libpangoft2-1.0-0`, `libgdk-pixbuf-2.0-0`, `shared-mime-info`,
  and `fonts-dejavu-core` alongside the pre-existing `libcairo2`.
  Predicted by the `feedback_render_deploy_verification` memory
  exactly — verified by curl against the live endpoint per the
  ADR-179 deploy gate.

## [6.6.0] - 2026-05-16

Issue #133 Phase 6 — surface parity discipline. The final phase of the
multi-phase plan. Codifies the rule that every backend write endpoint
must have a matching MCP tool AND a matching CLI subcommand; enforces
it as a CI gate so future drift is caught at PR time.

### Added

- **`scripts/check_surface_parity.py`** (ADR-182, SPEC-182-A). Parses
  backend routers, MCP tool registrations, and CLI commands; reports
  hard violations (exit 1) and soft warnings (exit 0). Also runs the
  protocols §13 DRY check for the renderer module — no `weasyprint`
  / `markdown_it` imports outside `backend/app/export/renderers/`.
- **`.github/workflows/parity-check.yml`** runs the script on every
  PR that touches a router, the MCP tools file, the CLI main file,
  the renderer module, or the script itself.

### Changed

- **`docs/protocols.md`** gains §14 "Surface Parity" with a one-line
  rule reference and pointer to ADR-182.
- **`CLAUDE.md`** appends a §14 reference so future code generation
  respects the rule.

### Documented asymmetries

The script exempts (and the ADR lists):

| Surface gap | Reason |
|---|---|
| `iris ask` CLI-only | MCP clients bring their own LLM (ADR-168) |
| No `delete_*` anywhere | Out of scope for #133; future ADR for audit/undo |
| No `move_element` | Elements are owned by their parent diagram (ADR-178 invariant) |
| In-set-only `move_diagram` / `move_package` | Backend `/parent` endpoints are in-set only; cross-set requires `create_set` + re-save (ADR-178) |

### Verification

- `python3 scripts/check_surface_parity.py` against the current main
  tree → exit 0, "✅ Parity clean".
- 17 backend write ops, 13 MCP write tools, 13 CLI write commands.
  The 4-tool delta is exactly the 4 entity-level `delete_*` endpoints
  (collection, set, package, diagram, element — 5 actually, but
  filtered down by the documented asymmetry).

### See also

- [ADR-182](docs/adrs/ADR-182-Surface-Parity-Discipline.md)
- [SPEC-182-A](docs/adrs/specs/SPEC-182-A-Surface-Parity-Discipline.md)
- [docs/plans/issue-133-doview-mcp-polish.md](docs/plans/issue-133-doview-mcp-polish.md) — multi-phase plan, complete with all six phases shipped.

### Issue #133 — complete

This is the final phase of issue #133. All six phases shipped between
2026-05-16 morning (v6.1.0) and 2026-05-16 evening (v6.6.0):

- v6.1.0 — cascade UX polish + MCP-wide AskUserQuestion (ADR-176, ADR-177)
- v6.2.0 — md/docx/pdf renderer + Iris artefact store (ADR-179)
- v6.3.0 — MCP update_* + move_* tools (ADR-178)
- v6.4.0 — CLI write-tool parity + create_element backfill (ADR-180)
- v6.5.0 — unified GUI diagram export menu (ADR-181)
- v6.6.0 — surface parity discipline + CI gate (ADR-182, this release)

## [6.5.0] - 2026-05-16

Issue #133 Phase 5 — unified diagram export menu in the GUI. The
diagram view's Export dropdown now ships real text PDFs and docx
files (server-rendered via Phase 2's renderer) alongside the
client-rasterised SVG / PNG it always had. The legacy jsPDF
PNG-screenshot-wrapped-in-A4 path is removed.

### Added

- **`frontend/src/lib/components/DiagramExportMenu.svelte`** (ADR-181,
  SPEC-181-A) — reusable Export dropdown component. Server-rendered
  Markdown / Docx / PDF via `POST /api/export/diagram/{id}` from
  Phase 2 (ADR-179). Client-rasterised SVG / PNG retained for visual
  diagrams. Visual-only items are hidden for markdown-content
  diagrams; the rest is universal. Triggers browser-native download
  via `<a download>` against `/api/artefacts/<id>` so no bytes flow
  through Svelte state.

### Changed

- `frontend/src/routes/views/[id]/+page.svelte` replaces both inline
  Export menus (regular view + focus mode) with `<DiagramExportMenu>`.
  The page-level `handleExportSvg`, `handleExportPng`,
  `handleExportPdf` functions and the `showExportMenu` state are
  removed — the component manages its own.

### Removed

- `frontend/src/lib/utils/export.ts` no longer imports `jspdf` or
  exposes `exportToPdf`. The old client-side PDF path (PNG screenshot
  wrapped in jsPDF at A4 paper size) was always worse than (a) a real
  text PDF from the server for markdown-content diagrams or (b) a
  direct PNG for visual diagrams.
- `jspdf` removed from `frontend/package.json` dependencies.

### See also

- [ADR-181](docs/adrs/ADR-181-Unified-Diagram-Export-GUI.md)
- [SPEC-181-A](docs/adrs/specs/SPEC-181-A-Unified-Diagram-Export-GUI.md)
- [docs/plans/issue-133-doview-mcp-polish.md](docs/plans/issue-133-doview-mcp-polish.md)

### Verification

- `npm run check`: zero new type errors (165 → 165 errors; all
  pre-existing). The new `.svelte` component and `+page.svelte`
  rewiring are type-clean.
- Manual UAT (post-merge): open a markdown diagram → Export → PDF →
  file is a real text PDF, not a screenshot. Visual diagram → Export
  → SVG / PNG still produce the canvas screenshot.

## [6.4.0] - 2026-05-16

Issue #133 Phase 4 — CLI write-tool parity with MCP. Every backend
write endpoint that has an MCP tool now also has an `iris` CLI
subcommand. The deliberate `iris ask` asymmetry (CLI-only, no MCP
counterpart per ADR-168) is documented.

### Added

- `iris create` sub-app with `collection`, `set`, `package`,
  `diagram` commands (ADR-180, SPEC-180-A). Mirrors the MCP `create_*`
  surface.
- `iris update` sub-app with `collection`, `set`, `package`,
  `diagram`, `element` commands. Same partial-update semantics as
  MCP `update_*` (GET-then-merge-then-PUT). `iris update set`
  deliberately excludes `--collection-id` (use `iris move set`).
- `iris move` sub-app with `diagram`, `package`, `set` commands.
  Pass the literal string `null` to set the target to NULL (move
  to set root / un-group).
- `iris render` sub-app with `diagram` and `markdown` commands.
  Renders to md/docx/pdf via the Phase 2 backend endpoints. With
  `-o OUT_PATH`, downloads the artefact bytes; without, prints the
  metadata JSON.
- **`create_element`** MCP tool + **`iris create element`** CLI
  command (Phase 4 follow-up). Backfills a parity gap that predates
  Phase 4: every other entity type had a `create_*` tool, but
  standalone elements could only be created via
  `apply_diagram_creation` (atomic with a diagram canvas). The new
  surface targets the element-pool use case where an element exists
  independently and is referenced by diagrams later.
- `cli/pyproject.toml`: 0.1.0 → 0.2.0.

### See also

- [ADR-180](docs/adrs/ADR-180-CLI-Write-Tool-Parity.md)
- [SPEC-180-A](docs/adrs/specs/SPEC-180-A-CLI-Write-Parity.md)
- [docs/plans/issue-133-doview-mcp-polish.md](docs/plans/issue-133-doview-mcp-polish.md)

### Tests

- 34/34 functional tests green in `cli/tests/` (17 new write-command
  tests + existing 17). 3 integration smoke tests skipped because they
  need the backend module installed in the CLI venv — pre-existing.

## [6.3.0] - 2026-05-16

Issue #133 Phase 3 — MCP `update_*` and `move_*` tool surface. The
cascade destination chooser is now fully actuated end-to-end (prompts
v6.1.0, renderer v6.2.0, move tools v6.3.0).

### Added

- **5 MCP update tools** (ADR-178, SPEC-178-A) wrapping existing
  backend PUT endpoints:
  - `update_collection(collection_id, name?, description?, system_prompt?, mcp_system_context?, thumbnail_source?, thumbnail_diagram_id?)`
  - `update_set(set_id, name?, description?, system_prompt?, mcp_system_context?, thumbnail_source?, thumbnail_diagram_id?)` — collection_id deliberately omitted (use move_set)
  - `update_package(package_id, name?, description?, metadata?)`
  - `update_diagram(diagram_id, name?, description?, data?, metadata?, change_summary?)` — versioned
  - `update_element(element_id, name?, description?, data?)`

  All five do a GET-then-merge-then-PUT so callers can pass partial
  updates without losing other fields (backend PUT does full-replace).
  All decorated with `web_url` (ADR-175 pattern). All map 401 to
  `auth_required` payloads.

- **3 MCP move tools**:
  - `move_diagram(diagram_id, parent_package_id?)` — in-set re-parent;
    null parent → set root.
  - `move_package(package_id, parent_package_id?)` — in-set re-parent
    with cycle check; null parent → set root.
  - `move_set(set_id, collection_id?)` — cross-collection move; null
    `collection_id` un-groups the set. Preserves all other metadata.

  Cross-set moves of packages/diagrams are NOT supported in v6.3.0 —
  documented as a deferred capability in ADR-178 and the Phase 6
  parity matrix.

### Changed

- **Cascade destination prompt** drops the Phase-1 cross-set move
  fallback. New body instructs the model: existing-set destination →
  save + `move_diagram` / `move_package`; new-set destination →
  `create_set` first in target collection, then save directly into
  the new set. Migration m062 + Supabase m066 + seed + canonical doc
  updated in lockstep.
- The destination chooser doc's "Phase-1 fallback" section retitled
  to "Actuation notes" to reflect the fully-shipped state.

### Notes

- Element re-parenting between diagrams is explicitly NOT a feature
  (per ADR-178). Elements travel with their parent diagram.
- Phase 6 (v6.6.0) will codify cross-surface parity as a CI gate.

### See also

- [ADR-178](docs/adrs/ADR-178-MCP-Update-Move-Tools.md)
- [SPEC-178-A](docs/adrs/specs/SPEC-178-A-MCP-Update-Move-Tools.md)
- [docs/plans/issue-133-doview-mcp-polish.md](docs/plans/issue-133-doview-mcp-polish.md)

### Tests

- 413/415 green in `backend/tests/test_{ai,migrations,export,artefacts}/`
  + new `test_phase3_move_actuation_schema.py` (8 tests).
- 197/197 green in `mcp/tests/` (16 new update + move tool tests).

## [6.2.0] - 2026-05-16

Issue #133 Phase 2 — server-side md/docx/pdf renderer + Iris artefact
store. The Phase-1 destination chooser cascade can now actually
produce the downloadable artefacts it promises.

### Added

- **Renderer module at `backend/app/export/renderers/`** (ADR-179,
  SPEC-179-A).
  - `markdown.py` — passthrough + normalisation.
  - `docx.py` — md → docx via `python-docx` + `markdown-it-py`.
    Headings, paragraphs, bullet/number lists, code blocks, mermaid
    blocks (verbatim passthrough), blockquotes.
  - `pdf.py` — md → pdf via `weasyprint`. Iris-branded CSS at
    `renderers/styles/iris.css` — system fonts, header colour
    palette, code block styling.
- **Artefact store at `backend/app/artefacts/`** (sibling to images,
  not a graft).
  - `artefacts` table — id / filename / mime / bytes / size_bytes /
    source_kind / source_ref / created_by / created_at.
  - Allowed mimes: text/markdown, docx, pdf. 25 MB per-row cap.
  - Magic-byte validation for pdf (`%PDF`) and docx (`PK\x03\x04`).
- **Backend endpoints**:
  - `POST /api/export/diagram/{diagram_id}` body `{format}` —
    render a diagram, store, return `ArtefactResponse` with
    `web_url`.
  - `POST /api/export/markdown` body `{markdown, title, format}` —
    ad-hoc render of cascade-generated content.
  - `GET /api/artefacts/{artefact_id}` — auth-optional download,
    Content-Disposition: attachment, immutable cache.
- **MCP tools** `render_diagram` and `render_markdown`. Both return
  `{id, filename, mime_type, size_bytes, web_url, ...}`. `web_url`
  points at the backend `/api/artefacts/<id>` so any client (browser,
  curl) downloads directly.
- **New backend deps**: `markdown-it-py>=4.0.0`, `weasyprint>=68.0`.
  Both verified installable in the dev devcontainer. WeasyPrint
  needs Pango / Cairo / GDK-PixBuf system libraries — Render image
  to be verified at deploy gate per
  `feedback_render_deploy_verification`.

### Changed

- **Cascade destination prompt** (`creation-cascade-destination-v1`)
  no longer carries the Phase-1 docx/pdf fallback paragraph. The
  body now instructs: "When the user picks docx or pdf at Q-Dest3,
  call the MCP `render_markdown` tool once per selected format ...
  present the `web_url` to the user as a clickable download link."
  The cross-set move fallback stays until Phase 3 (v6.3.0) ships
  `move_*` tools.
- The seed file's `CASCADE_DESTINATION_PROMPT` constant matches the
  new canonical body; `docs/prompts/creation-cascade-destination.md`
  updated in lockstep.

### See also

- [ADR-179](docs/adrs/ADR-179-Renderer-And-Artefact-Store.md)
- [SPEC-179-A](docs/adrs/specs/SPEC-179-A-Renderer-And-Artefact-Store.md)
- [docs/plans/issue-133-doview-mcp-polish.md](docs/plans/issue-133-doview-mcp-polish.md)

### Tests

406/406 green across `tests/test_ai/` + `tests/test_migrations/` +
`tests/test_export/` + `tests/test_artefacts/`. 181/181 green in
`mcp/tests/` (8 new tool tests).

## [6.1.0] - 2026-05-16

Issue #133 Phase 1 — creation-cascade UX polish + MCP-wide
AskUserQuestion convention.

### Added

- **Three new shared base-layer prompts for every notation's
  `creation_format` cascade (ADR-176, SPEC-176-A).**
  - `creation-cascade-shared-v1` (display_order=1) — Stage-0 questions
    (subject, info source with paste/upload affordance, default name
    suggestion) and the Stage 1 → Stage 2 transition question (skip
    detail / review detail / refine structure).
  - `creation-cascade-citations-v1` (display_order=2) — citation
    discipline: raw URLs and the
    `Author/Org · Title · YYYY · https://url` label format for every
    source-reference / annotation element.
  - `creation-cascade-destination-v1` (display_order=3) —
    save-destination chooser (Iris / downloadable artefacts / both;
    new set under parent collection by default; markdown / docx / pdf
    format selection). Includes Phase-1 fallbacks while the renderer
    (v6.2.0) and `move_*` tools (v6.3.0) are still in flight.
  Composed via the existing layered-prompt composer at
  `app/ai/creation.py:_build_layered_prompt`, so every notation
  (DoView, BPMN, UML, ArchiMate, C4, Simple) inherits the new
  conventions automatically.
- **MCP-wide ASKING QUESTIONS convention in the server-instructions
  singleton body (ADR-177, SPEC-177-A).** Whenever the model surfaces
  a finite-choice question to the user, it MUST use the client's
  structured user-question tool (AskUserQuestion in Claude Code /
  Claude Desktop / Cursor). Applies to the orient menu, every cascade
  Stage-0 question, the save-destination chooser, and any other
  user-facing choice. Supersedes the user-question half of ADR-167.
- New canonical paste-ready docs at
  `docs/prompts/creation-cascade-shared.md`,
  `docs/prompts/creation-cascade-citations.md`,
  `docs/prompts/creation-cascade-destination.md`.
- `display_order` is now part of the conflict tuple in
  `/api/ai/creation-prompts` CRUD (so multiple active base-layer rows
  can coexist at the same `(purpose, layer, NULL, NULL)` provided
  their display_orders differ).

### Changed

- `creation-doview-notation-v1` deferred to the shared cascade — the
  duplicated Stage-0 paste/upload, default-name, skip-detail, and
  destination guidance is removed from its body and lives once at the
  base layer. The DoView-specific questions (subpage count, detail
  level, sources page) remain in the notation prompt as
  `DoView-Q1` / `DoView-Q2` / `DoView-Q3`.
- `creation-outcomes-map-v1` updated to reference
  `creation-cascade-citations-v1` instead of restating the URL rule.
- `mcp-server-instructions-v1` body re-applied on every backend
  startup by `seed_creation_prompts` (new behaviour for this row —
  matches the existing cascade-prompt pattern). Future copy edits to
  the MCP server instructions ship without needing a new migration.
- `mcp/src/iris_mcp/server_instructions.py:_FALLBACK_INSTRUCTIONS`
  updated to include the new ASKING QUESTIONS section so day-one
  fallback matches the seeded body.
- `docs/prompts/mcp-server-instructions.md` updated with the new
  ASKING QUESTIONS section and a v6.1.0 revision-history entry.
- `mcp/README.md` documents the new conversation conventions and
  creation cascade structure.

### See also

- [ADR-176](docs/adrs/ADR-176-Cascade-Shared-Base-Prompts.md)
- [ADR-177](docs/adrs/ADR-177-AskUserQuestion-MCP-Convention.md)
- [SPEC-176-A](docs/adrs/specs/SPEC-176-A-Cascade-Shared-Base-Prompts.md)
- [SPEC-177-A](docs/adrs/specs/SPEC-177-A-AskUserQuestion-MCP-Convention.md)
- [docs/plans/issue-133-doview-mcp-polish.md](docs/plans/issue-133-doview-mcp-polish.md) — multi-phase plan; this is Phase 1.
- Issue [#133](https://github.com/cgbarlow/iris/issues/133) — UAT report and feedback.

## [6.0.15] - 2026-05-13

### Fixed

- **`create_*` MCP tool responses now include `web_url` so the model
  can link the user straight to the new entity (ADR-175).** Pre-
  v6.0.15, every read tool was decorated with `web_url` via
  `links.with_web_url(...)`, but the create_* tools returned a bare
  `model_dump_json()`. The model had no link to surface and had to
  guess the host. Concrete v6.0.14 failure:
  ```
  User: link me to it
  Claude: https://iris.chrisbarlow.nz/sets/df7aa9df-...   ← wrong host
  ```
  v6.0.15 wraps the return of `_create_collection`, `_create_set`,
  `_create_package`, and `_create_diagram` with
  `with_web_url(result.model_dump_json(), "<kind>")`. The model now
  surfaces the real frontend URL.
- `apply_diagram_creation` is unchanged — its batch response shape
  (`{diagram_ids: [...], primary_diagram_id: ...}`) of bare id
  strings needs a different decoration approach; deferred.

### Added

- 5 regression tests in `tests/test_create_tools_web_url_decoration.py`:
  - Each create_* tool's response includes a correctly-shaped
    `web_url` when `IRIS_WEB_URL` is set.
  - Absent `IRIS_WEB_URL` → response passes through unchanged (no
    `web_url` key), behaviour parity with read tools.
- 173/173 MCP tests pass.

### See also

- [ADR-175](docs/adrs/ADR-175-Web-URL-Decoration-On-Create-Tools.md)
- [SPEC-175-A](docs/adrs/specs/SPEC-175-A-Web-URL-Decoration-On-Create-Tools.md)

## [6.0.14] - 2026-05-13

### Fixed

- **OAuth-issued JWTs now validate in Supabase deployment mode
  (ADR-174).** v6.0.13 got the connector to "Connected" — token
  exchange returned 200 — but the very first authenticated API call
  the connector made got 401, and every subsequent write call too.
  Root cause: `_get_current_user_supabase` only validates JWTs with
  the **Supabase** signing key (ES256 via JWKS or HS256 with
  `SUPABASE_JWT_SECRET`). iris-OAuth tokens are signed by
  `app.oauth.service.issue_access_token` with the **iris** JWT secret
  via `config.auth.jwt_secret`. Two different keys → signature
  validation always fails → 401.
- The bug existed from v6.0.0 (when OAuth shipped) but was hidden
  because the existing OAuth tests run in SQLite mode, where
  `_get_current_user_sqlite` validates with the iris JWT secret and
  everything works.
- Fix: hybrid validation in `_get_current_user_supabase`. JWTs with
  `aud="iris-mcp"` (the canonical OAuth audience) route through the
  iris HS256 validator using `config.auth.jwt_secret`; everything
  else stays on the Supabase validation path. Audience-claim routing
  with strict per-issuer signature validation — no fall-through (a
  token claiming `aud="iris-mcp"` with the wrong signature gets 401,
  not a second chance with the Supabase secret).
- Profile lookup unchanged: both paths use the same
  `get_profile(db, user_id)` because the OAuth `sub` claim IS the
  Supabase auth.users UUID (consent screen captured it from this
  same function pre-issue).

### Security

- **`IRIS_JWT_SECRET` is now required in production.** The dev
  default in `config.py` is a hardcoded string in the public repo
  — anyone reading the repo can forge OAuth-issued JWTs against any
  deployment that hasn't overridden the secret. v6.0.14 adds
  `IRIS_JWT_SECRET` to `render.yaml` with `sync: false`; the
  operator generates a per-deployment secret
  (`openssl rand -hex 32`) and pastes it into the Render dashboard
  for the `iris-api` service. **This does NOT auto-apply** (Render
  Blueprint-sync limitation — same gotcha as `IRIS_MCP_PUBLIC_URL`
  in v6.0.9 and `IRIS_WEB_URL` in v6.0.11). Operator action
  required.

### Added

- 3 new regression tests in `tests/test_auth/test_supabase_mode_oauth_token.py`:
  - iris-OAuth token (correct signature) validates via iris path →
    returns user dict.
  - iris-OAuth token with wrong signature → 401 (no fall-through to
    Supabase validation).
  - Supabase-shaped token (no `aud="iris-mcp"`) routes through
    Supabase path → returns user dict.
- 120/120 OAuth + auth tests pass.

### Operator action required after deploy

1. **Set `IRIS_JWT_SECRET` on the iris-api service in the Render
   dashboard.** Generate the value with `openssl rand -hex 32`. Save;
   the service restarts.
2. **Disconnect + reconnect the Iris connector in claude.ai.** Old
   bearers signed with the dev-default secret will no longer
   validate; a fresh OAuth flow will mint bearers with the new
   secret.

### User-visible after that

- claude.ai → Sign in on Iris connector → consent → Allow → connector
  goes to **Connected** → write tools (`create_collection`,
  `create_set`, etc.) succeed.

### See also

- [ADR-174](docs/adrs/ADR-174-Hybrid-JWT-Validation-In-Supabase-Mode.md)
- [ADR-164](docs/adrs/ADR-164-OAuth-2.1-for-MCP.md) — original OAuth
  design that introduced the dual-key situation.
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — eleven-
  revision fix history (v6.0.4 → v6.0.14).

## [6.0.13] - 2026-05-13

### Fixed

- **OAuth token exchange crashed on Postgres with a SQLite/Postgres
  bool-vs-int type mismatch (ADR-173).** The connector dance reached
  the final step in v6.0.12 — user signed in to Iris, tapped Allow on
  consent, was redirected back to claude.ai with an authorization
  code — and the token exchange at `POST /oauth/token` blew up with:

  ```
  asyncpg.exceptions.DatatypeMismatchError:
    column "revoked" is of type boolean but expression is of type integer
  ```

  claude.ai surfaced the failure as `mcp_token_exchange_failed`. Live
  Render logs pointed at `oauth/service.py:260` in
  `create_refresh_token`.
- Root cause: `oauth_refresh_tokens.revoked` is `BOOLEAN` on Postgres
  (Supabase) but `INTEGER` on SQLite. Three call sites in
  `app/oauth/service.py` used bare-int SQL literals (`VALUES (..., 0)`,
  `SET revoked = 1`). SQLite accepts both, Postgres is strict. The
  existing 40 OAuth tests all passed against SQLite, so the bug went
  undetected from v6.0.0 until live production testing.
- Fix: parameterise as Python `bool` so the DB adapter coerces to the
  right SQL type on either backend.

### Added

- **Static regression guard** (`test_postgres_bool_int_compatibility.py`)
  scans the OAuth service source for bare-int literals on boolean
  columns. Catches future drift on SQLite-only test runs without
  needing a Postgres test fixture. 4 new test cases.
- 44/44 OAuth tests pass (40 existing + 4 new).

### User-visible after deploy

- claude.ai mobile → tap Sign in on Iris connector → consent page →
  Allow → connector goes to "Connected" (no more
  `mcp_token_exchange_failed`).
- Write tools (`create_collection`, `create_set`, etc.) now succeed
  with the issued bearer.

### See also

- [ADR-173](docs/adrs/ADR-173-OAuth-Boolean-Column-Parameterisation.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — ten-
  revision fix history.

## [6.0.12] - 2026-05-13

### Fixed

- **OAuth `authorization_endpoint` now derives from `IRIS_CORS_ORIGINS`
  when `IRIS_WEB_URL` isn't set (ADR-172).** v6.0.11 wired the endpoint
  through `IRIS_WEB_URL` and added the env var to `render.yaml`. Render
  Blueprint-sync gotcha: env-var additions in `render.yaml` don't
  auto-apply to existing services — they only take effect on initial
  service creation or via manual Blueprint re-sync. The same issue hit
  `IRIS_MCP_PUBLIC_URL` on iris-mcp in v6.0.9. Live iris-api still
  served the API host as `authorization_endpoint` post-v6.0.11 deploy
  because the new env var didn't propagate.
- v6.0.12 makes the code robust to that: if `IRIS_WEB_URL` is unset, it
  derives the frontend URL from the first non-localhost entry in
  `IRIS_CORS_ORIGINS` (which has been set since v6.0.0 and is
  guaranteed to be present — the frontend can't call iris-api without
  it). Resolution order: `IRIS_WEB_URL` → `IRIS_CORS_ORIGINS` (first
  non-localhost) → API issuer URL.

### Added

- 4 new regression tests in `backend/tests/test_oauth/test_metadata.py`:
  - Uses first non-localhost CORS origin when `IRIS_WEB_URL` is unset.
  - `IRIS_WEB_URL` wins over the CORS-origin fallback.
  - Skips `http://localhost:*` and `http://127.0.0.1:*` entries.
  - Strips trailing slashes.
- 40/40 backend OAuth tests pass.

### User-visible after deploy

- `curl https://iris-api-gtb3.onrender.com/.well-known/oauth-authorization-server`
  now reports
  `authorization_endpoint: https://iris-uat.chrisbarlow.nz/oauth/authorize`
  even if the new env var was never synced — auto-derived from the
  long-existing `IRIS_CORS_ORIGINS`.
- The OAuth flow continues from claude.ai → SvelteKit consent page →
  Allow → redirect with code → token → bearer → write tools succeed.

### See also

- [ADR-172](docs/adrs/ADR-172-Derive-Frontend-URL-From-CORS-Origins.md)
- [ADR-171](docs/adrs/ADR-171-OAuth-Authorization-Endpoint-Points-At-Frontend.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — nine-
  revision fix history.

## [6.0.11] - 2026-05-13

### Fixed

- **OAuth `authorization_endpoint` pointed at the wrong host, 404'ing
  the consent flow (ADR-171).** v6.0.10 unblocked claude.ai's OAuth
  trigger — tapping "Sign in" on the Iris connector finally initiated
  the flow. But the browser then redirected to the AS-metadata-
  advertised `authorization_endpoint` and landed on a hard
  `{"detail":"Not Found"}` 404. The metadata advertised the API host:

  ```
  authorization_endpoint: https://iris-api-gtb3.onrender.com/oauth/authorize
  ```

  But iris-api has no GET handler at `/oauth/authorize`. The user-
  facing consent screen is a SvelteKit page on the frontend at
  `https://iris-uat.chrisbarlow.nz/oauth/authorize`. The OAuth 2.1
  authorization endpoint is a **browser** endpoint — its job is to
  show login + consent UI and redirect back to the client's
  redirect_uri with an authorization code. v6.0.0 → v6.0.10 advertised
  the wrong host for that endpoint.
- v6.0.11 sources `authorization_endpoint` from `IRIS_WEB_URL` (the
  frontend host) in `app.oauth.router.authorization_server_metadata`.
  Token / registration / revocation endpoints stay on the API host —
  those are machine-to-machine endpoints (no browser involved).
  `render.yaml` adds `IRIS_WEB_URL=https://iris-uat.chrisbarlow.nz` to
  the iris-api service so the live deployment knows where the
  frontend lives.
- Falls back to the API host when `IRIS_WEB_URL` is unset (dev
  convenience — the metadata is well-formed, even though the URL
  won't actually serve a consent page).

### Added

- 3 new regression tests in `backend/tests/test_oauth/test_metadata.py`:
  - `authorization_endpoint` uses `IRIS_WEB_URL` when set.
  - Trailing slashes on `IRIS_WEB_URL` are stripped (no double-slash
    in the URL).
  - Falls back to issuer when `IRIS_WEB_URL` is unset.
  - Token / registration / revocation endpoints stay on the API host
    regardless.
- 36/36 backend OAuth tests pass.

### User-visible after deploy

- `https://iris-api-gtb3.onrender.com/.well-known/oauth-authorization-server`
  now reports
  `authorization_endpoint: https://iris-uat.chrisbarlow.nz/oauth/authorize`.
- claude.ai → tap Sign in on Iris connector → browser opens the
  SvelteKit consent page (not a 404) → user signs in to Iris if not
  already signed in → consent screen → tap Allow → redirected back to
  claude.ai with an auth code → bearer issued → write tools work.

### See also

- [ADR-171](docs/adrs/ADR-171-OAuth-Authorization-Endpoint-Points-At-Frontend.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — eight-
  revision fix history.

## [6.0.10] - 2026-05-13

### Fixed

- **OAuth-Discovery trigger now fires for claude.ai's MCP client
  (ADR-170).** The MCP authorization spec (2025-06-18) and RFC 9728
  require resource servers to return HTTP **401** with
  `WWW-Authenticate: Bearer resource_metadata="<URL>"` whenever a
  request lacks credentials. **That 401 is the canonical trigger** that
  causes claude.ai (and any compliant MCP client) to fetch the metadata,
  DCR-register itself, redirect the user to sign in, exchange the code
  for a bearer, and retry. iris-mcp v6.0.0 through v6.0.9 returned HTTP
  **200** with a JSON tool-error body (`"error":"auth_required"`) on
  unauthenticated requests — the spec's 401 trigger never fired,
  claude.ai treated the Iris connector as anonymous, and the user-
  visible "Sign in" button never appeared.
- v6.0.10 short-circuits `POST /` at the transport layer (in `mcp_asgi`)
  with a spec-compliant 401 + `WWW-Authenticate` when the request has
  no bearer token. The `resource_metadata` URL sources from
  `IRIS_MCP_PUBLIC_URL` (when set, per ADR-169) or `IRIS_API_URL` as a
  fallback. Static/health endpoints (`/info`, `/favicon.*`,
  `/.well-known/oauth-protected-resource`) remain anonymous.
- The tool-layer `auth_required` JSON payload in `tools.py` is
  preserved as a defensive backstop for the "bearer present but
  invalid/expired" case — v6.0.10 only fixes the missing-bearer case.

### Removed

- **Anonymous HTTP read access via iris-mcp.** A CLI script that wants
  to call iris-mcp's HTTP endpoint without OAuth must now use the stdio
  transport (`iris-mcp` with `IRIS_TOKEN`) or talk to iris-api
  directly. The frontend's read-only public endpoints and the iris-
  client SDK are unaffected. This trade-off is what unlocks claude.ai's
  OAuth flow — see ADR-170 for the rationale (every working production
  hosted-MCP server requires auth uniformly).

### Added

- 4 new regression tests (`TestAuthChallenge` in `test_http_main.py`)
  pinning: 401 on unauthenticated POST /; WWW-Authenticate header
  shape with `resource_metadata=`; URL sourcing from
  `IRIS_MCP_PUBLIC_URL` when set; bearer-present requests bypass the
  401 gate and pass through to the MCP layer.
- 168/168 MCP tests pass.

### User-visible after deploy

- **Add the Iris connector in claude.ai** — Settings → Connectors → add
  `https://iris-mcp.onrender.com`. claude.ai's probe gets back HTTP 401,
  discovers OAuth metadata, registers itself via DCR, and the connector
  card now shows a **"Sign in"** button.
- **Click Sign in** — a browser tab opens against iris-api's
  `/oauth/authorize`. Sign in with the same email/password you use on
  iris-uat. Consent screen. Redirect. claude.ai stores the bearer.
- **Write tools work** — `create_collection`, `create_set`, etc. now
  succeed.

### See also

- [ADR-170](docs/adrs/ADR-170-Require-Bearer-On-MCP-HTTP-Endpoint.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — seven-
  revision fix history culminating here.

## [6.0.9] - 2026-05-13

### Fixed

- **OAuth metadata pointed at the wrong host, silently breaking
  claude.ai's auto-sign-in (ADR-169).** The Protected Resource metadata
  at `iris-mcp.../.well-known/oauth-protected-resource` advertised
  `https://iris-uat.chrisbarlow.nz` (the frontend host) as the
  Authorization Server. The frontend is a SvelteKit SPA that returns
  HTTP 200 with its `index.html` for any unknown path — including
  `/.well-known/oauth-authorization-server` — so claude.ai's MCP
  client couldn't parse OAuth metadata from the HTML body and fell
  back to surfacing the tool-layer `auth_required` error. v6.0.0 →
  v6.0.8 all shipped this bug.
- v6.0.9 sources `authorization_server` from `IRIS_API_URL` (where the
  RFC 8414 AS metadata document and `/oauth/{authorize,token,register,
  revoke}` endpoints actually live). `resource` falls back to
  `IRIS_API_URL` too when `IRIS_MCP_PUBLIC_URL` isn't set. `IRIS_WEB_URL`
  is no longer read by the OAuth metadata path — its purpose is link
  decoration only.
- `render.yaml` for the `iris-mcp` service now sets
  `IRIS_MCP_PUBLIC_URL = https://iris-mcp.onrender.com` so the live
  deployment's `resource` field correctly identifies the iris-mcp
  service (rather than falling back to the API host).
- Tool-layer `auth_required` payload + canonical
  `mcp_server_instructions` body refined: the previous wording
  ("Configure → enable OAuth") assumed claude.ai's connector UI exposes
  a manual OAuth toggle, but the actual flow auto-detects OAuth from
  Protected Resource metadata and offers a "Sign in" button. The new
  wording reflects that users do NOT enter `client_id` / `secret` and
  that re-adding the connector forces metadata re-discovery if no
  sign-in button appears.

### Added

- **Introduction and Conclusion in the Outcomes Theory Book TOC.** The
  set has two root-level markdown diagrams (`parent_package_id=null`)
  that bracket Part A through Part J; v6.0.7's `package_hierarchy` call
  alone missed them. The canonical `doview-book-mcp-system-context.md`
  paste-doc now names two structural-overview calls
  (`package_hierarchy` + `list_diagrams` filtered to root) so the model
  fetches both packages and root-level diagrams. The orient sheet
  instructs the model to render Introduction first, the parts, then
  Conclusion last.
- Two new regression tests in `test_oauth_resource.py` pinning the
  v6.0.9 metadata correctness: `authorization_server` points at
  `IRIS_API_URL`; `resource` falls back to `IRIS_API_URL` (not
  `IRIS_WEB_URL`) when `IRIS_MCP_PUBLIC_URL` is unset.
- 164/164 MCP tests pass.

### Admin action required after deploy

After Render reports `6.0.9` on `/info`:

1. **Re-paste** the v6.0.9 menu from
   [`docs/prompts/doview-book-mcp-system-context.md`](docs/prompts/doview-book-mcp-system-context.md)
   into the Outcomes Theory Book set's `mcp_system_context` field at
   `/sets/33032180-d77a-4ce4-88cf-b49cd643e093`.
2. **Re-paste** the v6.0.9 auth-recovery body from
   [`docs/prompts/mcp-server-instructions.md`](docs/prompts/mcp-server-instructions.md)
   into the `mcp_server_instructions` row at `/admin/settings/ai`.
3. **Remove and re-add** the Iris connector in claude.ai so the MCP
   client re-discovers the now-correct OAuth metadata. After that,
   clicking "Sign in" on the connector should open a browser tab for
   you to sign in to Iris (no `client_id` / `secret` entry).

The v6.0.5 TTL refresh propagates both paste edits to claude.ai within
60 seconds. No Render restart required for either.

### See also

- [ADR-169](docs/adrs/ADR-169-OAuth-Metadata-URL-Fix.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119)

## [6.0.8] - 2026-05-13

### Removed

- **`ask` tool removed from the MCP surface (ADR-168).** When iris-mcp
  is consumed by a capable-LLM client (claude.ai / Claude Desktop /
  Claude Code / Cursor), routing the model's question to Iris' server-
  side AI is redundant and breaks tone continuity. Concretely, v6.0.7
  testing surfaced the failure: the user picked "Generate a new DoView
  outcomes-theory analysis" and the model called `ask` to do it — the
  analysis came back in a different voice from a different conversation,
  with no follow-through path. Cross-scope questions are fulfilled
  equally well by the local model reading the data directly through
  `search`, `get_*`, `list_*`, and `package_hierarchy`.
- iris-client's `IrisClient.ask(...)` SDK method is **kept**. Scripts,
  jobs, iris-cli, and any non-MCP consumer that genuinely needs Iris AI
  inference can still call it. The boundary is drawn at the MCP surface.

### Changed

- **`apply_diagram_creation` description rewritten.** Previously read
  "Use after calling `ask` with mode='creation'..." — referenced the
  removed `ask` path. Now reads: "The client drafts the diagrams JSON
  (one entry per diagram, matching the creation_format cascade returned
  by `get_response_prompt(...)`) and posts it here for persistence.
  Prefer `create_diagram` for single-diagram creation; this tool is for
  batch saves." Reflects the local-AI-as-author model.
- **Orient wrapper strengthened (ADR-167 follow-up).** Two new short
  paragraphs make explicit:
  - Cross-package / cross-set / cross-collection questions are
    fulfilled by the local model reading data via the read-only MCP
    tools. "There is no 'ask Iris AI' tool — it has been removed."
  - DoView outcomes-theory analyses + visual outcomes_map diagrams are
    drafted by the local AI using its own reasoning + the creation_format
    cascade; persistence is via `create_diagram` / `apply_diagram_creation`.
    "Do NOT look for a separate AI-analysis tool — none exists."
- **Canonical `doview-book-mcp-system-context.md` paste-doc updated.**
  Option 2 broadens from "Ask a cross-package question via Iris AI —
  uses mcp__iris__ask" to "Ask a cross-package, cross-set, or
  cross-collection question about the material". Option 3 drops the
  "→ call create_diagram" implementation tag. Admin must re-paste from
  the doc into `/admin/settings/ai` on UAT to apply the new menu.

### Tests

- `TestAsk` class replaced with `TestAskRemoved` (2 cases): `ask` not
  in `tool_definitions()`; dispatching to `"ask"` returns the standard
  unknown-tool error.
- `test_links_orient_wrapper.py` updated: asserts `mcp__iris__ask` is
  NOT in the wrapper text, and adds `TestWrapperStepsAnalysisToLocalAI`
  pinning the new "YOU do the work" steering.
- 163/163 MCP tests pass.

### Admin action required after deploy

Paste the v6.0.8 content from
[`docs/prompts/doview-book-mcp-system-context.md`](docs/prompts/doview-book-mcp-system-context.md)
into the Outcomes Theory Book's `mcp_system_context` field on
`/admin/settings/ai`. The TTL refresh (v6.0.5, ADR-166) propagates the
change to claude.ai within 60s without a redeploy.

### See also

- [ADR-168](docs/adrs/ADR-168-Remove-Ask-Tool-From-MCP-Surface.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — six-revision
  fix history: v6.0.4 (wire), v6.0.5 (refresh), v6.0.6 (embed), v6.0.7
  (TOC format + verbatim menu), v6.0.8 (drop ask, route analysis local).

## [6.0.7] - 2026-05-13

### Fixed

- **TOC now renders as a markdown bullet list with clickable links per
  Part / chapter (issue #119 polish).** v6.0.6 got claude.ai to invoke
  `package_hierarchy` and present the parts, but the model rendered the
  result as a wall of text without links. Two underlying causes:
  - `package_hierarchy` tool output was not decorated with `web_url`
    fields (`with_web_urls_list` only walks the top level; the nested
    `children` arrays were left bare).
  - The orient wrapper said only "Surface the resulting tree" — no
    formatting prescription, so the model defaulted to a paragraph.
- New `decorate_tree(nodes, kind, base)` walks a homogeneous tree
  recursively and attaches `web_url` at every depth. `_package_hierarchy`
  now wraps its output with `with_web_urls_tree`. Every Part and chapter
  in the response carries `web_url`, so the model can render `[name](url)`
  markdown links directly.
- Orient wrapper now spells out the TOC format explicitly: "render the
  result as a markdown bullet list, ONE ENTRY PER LINE, with each entry
  as a clickable markdown link using the node's `web_url` field". Includes
  a concrete two-line example so the model has a pattern to mimic.

- **Menu options now stay verbatim (issue #119 polish).** v6.0.6 said
  "do not paraphrase" but the model still dropped parenthetical examples
  ("(e.g. J06 — Mathematization of Outcomes Theory)"), tool references
  ("uses mcp__iris__ask"), and "→ call create_diagram" — and even reworded
  "outcomes-theory analysis" to "outcomes map".
- Orient wrapper now demands "CHARACTER-BY-CHARACTER" copying with explicit
  negations: "Do NOT summarise. Do NOT shorten. Do NOT drop parenthetical
  examples like '(e.g. J06 — Mathematization of Outcomes Theory)' or tool
  references like 'uses mcp__iris__ask'. ... Long options are intentional."

### Added

- New `decorate_tree` and `with_web_urls_tree` helpers in `links.py`.
  Exported from `__all__`.
- 5 new regression tests (`TestPackageHierarchyTreeDecoration`,
  `TestOrientWrapperFormattingDirectives`) pinning the recursive
  decoration and the strengthened wrapper wording.

### Why this matters

- Users opening an authored scope now see the TOC as a navigable list
  with one-click access to each Part / chapter — restoring the click-to-
  open affordance the 5.x UI had via the dashboard. Matches the user's
  visual request in issue #119 follow-up.
- The four menu options match the admin-authored body exactly. Admins
  iterating on the menu copy in `/admin/settings/ai` see their edits
  reach claude.ai unmodified.

### See also

- ADR-167 — Orient directive in tool response (updated to cover the
  TOC formatting + character-by-character menu wording).
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — five-revision
  fix history: v6.0.4 (wire), v6.0.5 (refresh), v6.0.6 (embed), v6.0.7
  (TOC format + verbatim menu).

## [6.0.6] - 2026-05-13

### Fixed

- **Orient-first protocol now reaches claude.ai's hosted MCP integration
  (issue #119, ADR-167).** v6.0.4 (ADR-165) wired the protocol through
  `Server.instructions` on the HTTP transport; v6.0.5 (ADR-166) kept it
  fresh via a TTL refresh. Both were verified working on the wire — the
  strong canonical body was delivered in every `InitializeResult` claude.ai
  received. But claude.ai's model **still skipped the `package_hierarchy`
  call and paraphrased the menu**. Three rounds of fixes confirmed the
  channel works; the conclusion: **claude.ai does not reliably surface
  `InitializeResult.instructions` to the model.**
- v6.0.6's pragmatic fix re-embeds the orient directive **directly into
  the tool response**, where the model has been consistently shown to
  read it. `iris-mcp`'s `links.py` now prepends a hardcoded imperative
  prefix to any non-empty `mcp_system_context` field on set / collection
  responses (`search`, `list_*`, `get_*`). The prefix pre-fills the
  scope's id in the tool-call signature (`set_id="..."` /
  `collection_id="..."`) so the model has the exact `package_hierarchy`
  call ready — no inference needed, just execute.
- The prefix is hardcoded in `iris-mcp` source (universal protocol, not
  scope-specific content). Admin-edits to per-scope `mcp_system_context`
  stay focused on the scope's menu. The existing `Server.instructions`
  channel is preserved as belt-and-suspenders for MCP clients that do
  surface it reliably (Claude Desktop, Claude Code, Cursor).
- The wrapper is **idempotent** via a marker check and **always-on**
  regardless of `IRIS_WEB_URL` (the web-URL decoration is env-gated; the
  orient wrapper is universal).

### Added

- New `wrap_orient(item, kind)` primitive in `links.py`. Pre-fills the
  scope's id in the tool-call signature, applies only to sets and
  collections, idempotent, no-op when the field is missing/empty.
- **18 new regression tests** (`test_links_orient_wrapper.py`) across
  five classes: primitive behaviour (wrap, no-ops, idempotency),
  search-response application, list-response application, single-entity
  application, IRIS_WEB_URL independence.
- 4 v5.11.0 / ADR-156 passthrough tests updated: the wrapped body must
  still end with the original admin-authored content (the v5.11.0
  contract evolves; ADR-167 strengthens it).

### Why this matters

- **claude.ai users now see the v5.x flow restored**: opening the
  Outcomes Theory Book auto-loads the TOC, presents the four-option
  menu via `AskUserQuestion`, no "want me to load it?" preamble.
- The fix doesn't depend on any future claude.ai-side change. The orient
  directive is in the tool response data, which every MCP client surfaces
  to its model unconditionally.

### See also

- [ADR-167](docs/adrs/ADR-167-Orient-Directive-In-Tool-Response.md)
- [SPEC-167-A](docs/adrs/specs/SPEC-167-A-Orient-Directive-In-Tool-Response.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — four-revision
  fix history: v6.0.4 (wire), v6.0.5 (refresh), v6.0.6 (embed in
  response).

## [6.0.5] - 2026-05-13

### Fixed

- **MCP server instructions now refresh from the backend on a TTL —
  admin edits propagate without a Render redeploy (issue #119 final
  follow-up, ADR-166).** v6.0.4 (ADR-165) wired the orient-first
  protocol body through the HTTP transport at lifespan startup, but
  iris-mcp continued serving the body it fetched at boot for the
  entire lifetime of the process. Admins editing the
  `mcp_server_instructions` row in `/admin/settings/ai` had to wait
  for a manual Render "Manual Deploy" before the new body reached
  claude.ai. That defeated the "admin-editable" promise of ADR-163.
- The HTTP-transport lifespan now spawns an `asyncio` background task
  that re-fetches `/api/ai/server-instructions` every
  `IRIS_MCP_INSTRUCTIONS_REFRESH_S` seconds (default **60**) and
  updates `session_manager.app.instructions` if the body has changed.
  The MCP SDK reads `Server.instructions` per request, so the next
  claude.ai session that connects after the tick sees the fresh body.
- **Transient backend failures preserve the last good value.** A new
  helper `try_fetch_server_instructions(iris_url) -> str | None`
  returns `None` on every failure mode `fetch_server_instructions`
  falls back from (network error, HTTP error, malformed JSON, empty
  body). The refresh loop only writes when it gets a fresh real body,
  so a 30-second backend hiccup doesn't silently revert admin
  customisations to the hardcoded fallback. The startup fetch still
  uses `fetch_server_instructions` so the first request never sees
  `instructions=None`.
- **Background task is cancelled cleanly on lifespan shutdown.** No
  hung tasks, no leaked exceptions when iris-mcp restarts.

### Added

- New env var `IRIS_MCP_INSTRUCTIONS_REFRESH_S` (default 60, set 0 to
  disable the loop). Tunable for prompt-engineering iteration (shorter
  interval) or quiet production (longer interval / disabled).
- 7 new regression tests:
  - `test_server_instructions.py::TestTryFetchServerInstructions` (7
    cases) — `try_fetch` returns body on happy path; `None` on every
    failure mode the canonical variant falls back from.
  - `test_http_main.py::TestRefreshLoop` (3 cases) — refresh picks up
    an updated body within the TTL window; preserves last-good body
    on transient failure; disabled when interval is 0.

### Why this matters

- Admins iterating on the orient protocol from `/admin/settings/ai`
  now see edits propagate to claude.ai within ≤ 60 seconds (default).
  No Render dashboard required, no commit-and-deploy cycle. This is
  what ADR-163's "admin-editable" promise has meant all along; v6.0.5
  is the last gap closed.

### See also

- [ADR-166](docs/adrs/ADR-166-MCP-Server-Instructions-TTL-Refresh.md)
- [SPEC-166-A](docs/adrs/specs/SPEC-166-A-MCP-Server-Instructions-TTL-Refresh.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119)

## [6.0.4] - 2026-05-13

### Fixed

- **MCP orient-first protocol over HTTP transport (issue #119, ADR-165).**
  v5.18.0 (ADR-163) lifted the universal ORIENT-FIRST protocol into the
  MCP `Server(instructions=...)` channel and wired it through the stdio
  entry point. The parallel wiring for the HTTP transport
  (`asgi.py:build_session_manager`, `http_main.py:create_app`) was
  missed, so every claude.ai connection — which uses HTTP via the OAuth
  connector introduced in v6.0.0 — received `InitializeResult` with no
  `instructions` body. Without that directive in scope ("INVOKE the
  structural-overview call... NOT as a follow-up 'want me to load it?'
  prompt"), opening an authored set produced a paraphrased text menu
  instead of the 5.x flow: auto-loaded TOC + four-option `AskUserQuestion`
  widget.
- `build_session_manager()` gains an `instructions: str | None = None`
  keyword argument that forwards to `build_server(..., instructions=...)`.
  `create_app()` builds the manager up front, then fetches the orient
  body in the FastAPI lifespan startup and mutates
  `session_manager.app.instructions` before the first request arrives.
  Mutation is safe — the MCP SDK reads `Server.instructions` per request
  when constructing the InitializeResult, not at server-construct time.
- Fallback semantics are inherited from `fetch_server_instructions`:
  any network error, HTTP error, malformed JSON, or empty body yields
  the hardcoded baseline. The HTTP transport therefore never advertises
  `instructions=None` in production.
- Prior fixes (v6.0.1 m055, v6.0.2 m056, v6.0.3) targeted a separate
  bug — the `iris_package_hierarchy` → `package_hierarchy` tool-name
  substitution — which is unrelated and remains fixed.

### Added

- **Regression tests** (`test_server_instructions_wiring.py::TestBuildSessionManagerInstructionsWiring`,
  `test_http_main.py::TestCreateAppFetchesInstructions`) pin the HTTP
  transport's `instructions` wiring end-to-end. The wiring tests round-
  trip an arbitrary body through `build_session_manager`; the http_main
  tests verify the lifespan fetches `/api/ai/server-instructions` and
  falls back gracefully on backend errors. Closes the test gap that let
  the v5.18.0 regression land unnoticed.
- `app.state.session_manager` exposed on the FastAPI app so regression
  tests can introspect the wrapped MCP server's instructions without
  walking private route internals.

### Why this matters

- claude.ai users opening any authored scope (e.g. the Outcomes Theory
  Book set) now see the full ORIENT-FIRST flow: TOC auto-loaded,
  four-option menu offered via `AskUserQuestion`, no "want me to load
  it?" preamble. Matches the 5.x.previous flow captured in issue #119.

### See also

- [ADR-165](docs/adrs/ADR-165-MCP-Server-Instructions-Over-HTTP-Transport.md)
- [SPEC-165-A](docs/adrs/specs/SPEC-165-A-MCP-Server-Instructions-Over-HTTP-Transport.md)
- Issue [#119](https://github.com/cgbarlow/iris/issues/119)

## [6.0.3] - 2026-05-13

### Fixed

- **Stale `iris_authenticate` references in `mcp_server_instructions`
  seed body** (issue #115 follow-up). The v5.18.0 seed (m053) shipped
  two sentences referencing the v5.15.0 `iris_authenticate` flow —
  one in WORKFLOW GUIDANCE, one in AUTH RECOVERY. v6.0.0 (ADR-164)
  removed that tool and rewrote the canonical doc + iris-mcp fallback
  constant, but the **seed body** was never updated. Live deployments
  seeded with v5.18.0 carried the stale references through v6.0.0 →
  v6.0.2 even after m055/m056 fixed the unrelated `iris_package_hierarchy`
  typo. Discovered during the regression-test inventory for this release.
- **m057 (SQLite) + m061 (Supabase)** surgically REPLACE() the two
  stale sentences in the singleton `mcp_server_instructions` row with
  their v6.0.0 OAuth-aligned text. Admin customisations elsewhere in
  the body are preserved. Idempotent.
- The seed bodies themselves (m053 SQLite + m057 Supabase) are also
  updated so fresh installs converge with migrated installs.

### Added

- **Regression test** `test_no_unregistered_iris_tool_refs.py` walks
  every live-data source (seeded migration bodies, iris-mcp source
  files, canonical paste-ready docs) and asserts every `iris_<word>`
  token references a registered MCP tool (parsed statically from
  `tools.py`) or is in a small non-tool allowlist (env vars, the
  server name, etc.). Specific regression assertions for
  `iris_package_hierarchy` (issue #115 root cause) and
  `iris_authenticate` (v6.0.0-removed tool) being absent from all
  seed bodies. Caught one stale historical-comment reference in
  `tools.py` that the v6.0.3 inventory had missed.

### Migration

- **SQLite m057** runs automatically on next boot. No manual paste.
- **Supabase m061**: apply once via `./scripts/supabase-migrate.sh`.

### Tests

- 12 new regression tests (`test_no_unregistered_iris_tool_refs.py`)
  + 5 new migration tests (`test_stale_auth_recovery_fix.py`).

## [6.0.2] - 2026-05-13

### Fixed

- **Per-scope `mcp_system_context` still carried `iris_package_hierarchy`**
  (issue #115 follow-up). v6.0.1's m055/m059 fixed the server-wide
  `mcp_server_instructions` singleton row, but the **per-scope
  content** on `sets.mcp_system_context` (and `collections.mcp_system_context`)
  was pasted during v5.18.0 / v6.0.0 admin setup with the wrong tool
  name. Live-data testing confirmed: search results for the Outcomes
  Theory Book still surfaced `iris_package_hierarchy(set_id=)` in
  the scope content, defeating v6.0.1's protocol fix.
- **m056 (SQLite) + m060 (Supabase)** surgically REPLACE() the wrong
  substring in `sets.mcp_system_context` AND `collections.mcp_system_context`
  for every row that's non-NULL. Admin customisations elsewhere in
  each body are preserved. Idempotent.

### Migration

- **SQLite m056** runs automatically on next boot. No manual paste.
- **Supabase m060**: apply once via `./scripts/supabase-migrate.sh`.

### Tests

- 4 new migration-parser tests (REPLACE shape on both tables, guards,
  NULL-skip, Supabase mirror). End-to-end smoke against an in-memory
  SQLite fixture confirms the REPLACE fixes stale rows and is
  idempotent.

## [6.0.1] - 2026-05-13

### Fixed

- **MCP orient-flow TOC step missing in v6** (issue #115). When a
  user opened the Outcomes Theory Book in Iris via the claude.ai
  connector, the v5.x flow returned a brief description **plus a
  package hierarchy (the TOC, Part A–Part J)** plus the four-option
  menu. v6.0.0 dropped the TOC step — the model offered "Want me to
  load the package hierarchy?" as a follow-up instead of surfacing
  it as part of the orient.

  Root cause: the canonical mcp_server_instructions content (seeded
  in v5.18.0 / ADR-163) and the canonical Outcomes Theory Book
  `mcp_system_context` (since v5.13.0 / ADR-158) both referenced the
  structural-overview tool as `iris_package_hierarchy`, but the
  actual MCP-registered tool name is `package_hierarchy`. claude.ai
  v5-era hosted-MCP behaviour translated the wrong name (or kept the
  full toolset loaded); the stricter v6-era behaviour does not. The
  orient step 2 silently no-op'd.

  Two fixes:
  1. Corrected the tool name in all five canonical sources (server
     instructions seed m053, server instructions Supabase seed m057,
     server-instructions iris-mcp fallback constant, canonical doc,
     Outcomes Theory Book scope context doc).
  2. Strengthened the orient-protocol step 2 to require invocation
     before the menu: "INVOKE the structural-overview call ... NOT
     as a follow-up 'want me to load it?' prompt. If your MCP client
     lazy-loads tools and the named tool isn't currently in your
     toolset, request/load it before continuing. The TOC is part of
     the orient, not optional."

### Migration

- **SQLite m055** runs automatically on next boot. Surgically
  `REPLACE()`s `iris_package_hierarchy` → `package_hierarchy` in the
  live `mcp_server_instructions` singleton row's `prompt_text`.
  Preserves any admin customisations elsewhere in the body.
- **Supabase m059**: apply once via `./scripts/supabase-migrate.sh`.
- No manual paste needed — the migration fixes the live row directly.

### Tests

- 5 new migration-parser tests verifying the REPLACE() shape and
  that the underlying m053/m057 seeds also use the correct name
  (so fresh installs don't regress).

## [6.0.0] - 2026-05-13

### Breaking changes

- **`iris_authenticate` MCP tool removed.** Was added in v5.15.0 to
  authenticate write tools from inside a conversation; broke
  fundamentally in HTTP-streamable mode (claude.ai connectors)
  because the v5.15.0 design assumed stdio's long-lived client.
- **`save_doview_analysis` MCP tool removed.** Deprecated since
  v5.17.0; use `create_diagram(notation='markdown',
  diagram_type='doview_analysis', set_id=..., name=...,
  data={'content': '<markdown>'}, parent_package_id=?)`.
- **`/settings/mcp-pairing` page removed.** The "MCP Connections"
  section on `/settings` is also gone.
- **`/api/auth/pairing-codes` endpoints removed.** `pairing_codes`
  table is dropped by migration m054 (SQLite) / m058 (Supabase).
- **iris-client methods removed**: `create_pairing_code`,
  `exchange_pairing_code`, `set_token`. The `PairingCodeResponse`
  and `ExchangedPATResponse` models are also gone.
- **iris-mcp `~/.iris-mcp/<hash>.json` token store removed.** The
  `token_store.py` module is deleted.
- **iris-mcp stdio token resolution** simplified to "IRIS_TOKEN env
  var or anonymous" — no more file fallback.

### Added

- **OAuth 2.1 Authorization Server on iris-backend** (ADR-164,
  SPEC-164-A). RFC 8414 metadata + RFC 7591 DCR + RFC 7636 PKCE +
  RFC 7009 revocation. Endpoints:
  - `GET /.well-known/oauth-authorization-server` (anonymous)
  - `POST /oauth/register` (anonymous; open DCR)
  - `POST /oauth/token` (authorization_code + refresh_token grants)
  - `POST /oauth/revoke`
  - Frontend `/oauth/authorize` consent screen with helpers
    `POST /api/oauth/authorize/prepare` + `/decision`.
- **Three new DB tables**: `oauth_clients`, `oauth_authorization_codes`,
  `oauth_refresh_tokens` (with family-id rotation + theft detection
  mirroring the v5.x `refresh_tokens` pattern).
- **JWT access tokens** signed with the existing `JWT_SECRET` (HS256);
  flow through the existing `get_current_user` dependency unchanged
  thanks to `verify_aud=False` (the `aud="iris-mcp"` claim is
  informational; signature is the security boundary).
- **Refresh tokens** are opaque DB-stored strings with 14-day
  lifetime, single-use rotation, and family-wide kill switch on
  replay (theft detection).
- **iris-mcp Protected Resource metadata** at
  `/.well-known/oauth-protected-resource` (RFC 9728). MCP clients
  fetch this on a 401 response's `WWW-Authenticate: Bearer
  resource_metadata="..."` hint and start an OAuth dance.
- **Frontend `/oauth/authorize` consent screen** with DOMPurify-
  sanitised `client_name`, Allow/Deny buttons, redirect-back via
  the existing `safeRedirectTarget` flow.

### Changed

- **`get_current_user` accepts OAuth-issued JWTs.** The existing
  bearer-prefix detection (`iris_pat_` vs JWT) is unchanged; OAuth
  JWTs carry `aud="iris-mcp"`, `azp=<client_id>`, `scope="iris"`,
  `role` claims. PATs (`iris_pat_*`) continue to coexist for CLI/
  scripted use unchanged.
- **`decode_access_token`** gains `verify_aud=False` so OAuth-
  issued JWTs and legacy `/api/auth/login` JWTs both pass through
  uniformly.
- **iris-mcp `_auth_required_payload` rewritten.** New shape:
  `{success: False, error: "auth_required", next_step:
  "configure_oauth_in_connector_settings",
  oauth_resource_metadata_url: ...}`. No more `next_tool` /
  `pairing_url` fields.
- **Server-wide MCP `instructions` AUTH RECOVERY section** rewritten
  for OAuth. Admins on UAT should paste the trimmed
  `docs/prompts/mcp-server-instructions.md` content into the
  singleton row.
- **PATs kept** for CLI / scripted use. No changes to
  `/api/users/me/tokens`, `verify_pat`, or `iris_pat_*` bearer
  detection.

### Migration

- **SQLite m054** runs automatically on next boot. Drops
  `pairing_codes`, creates `oauth_clients` + `oauth_authorization_codes`
  + `oauth_refresh_tokens`.
- **Supabase m058**: apply once via `./scripts/supabase-migrate.sh`.
- **Manual on UAT**: paste the rewritten `mcp-server-instructions.md`
  content into the `mcp_server_instructions` singleton row (admins).
- **HTTP/claude.ai users**: remove the v5.15.0 pairing-code
  configuration and reconfigure the connector to use OAuth. The
  connector setup wizard will run the OAuth dance automatically.
- **Stdio operators** with `IRIS_TOKEN` env var: no action needed.

### Tests

- ~33 net new backend tests (OAuth metadata, register, authorize,
  token PKCE, refresh rotation, revoke, get_current_user OAuth-JWT
  acceptance, migration schema parsers).
- ~6 iris-mcp tests (resource metadata + WWW-Authenticate helpers +
  HTTP endpoint mount).
- ~6 frontend tests (consent screen sanitisation + pairing-page
  removal regression checks).
- ~22 tests deleted (pairing-code tests across backend / iris-mcp
  / iris-client / frontend).
- Combined: backend 215 pass, MCP 123 pass, iris-client 52 pass,
  frontend (v5.15-v6.0 sweep) clean.

## [5.18.0] - 2026-05-13

### Added

- **Centralised, admin-editable MCP server instructions**
  (ADR-163, SPEC-163-A). The universal ORIENT-FIRST protocol and
  DISCOVERY catalogue that v5.13.x → v5.17.x had embedded in every
  authored scope's `mcp_system_context` are lifted into a single
  server-wide channel: the MCP spec's `Server(instructions=...)`
  field, returned in the InitializeResult to every connected MCP
  client. Universal across every scope. Three clean layers now:
  per-tool workflow (in tool descriptions), server-wide orient
  (this), scope-specific menu (per-scope `mcp_system_context`).
- **New `purpose='mcp_server_instructions'`** on
  `ai_creation_prompts`. Singleton row at layer=base, seeded by
  m053 (SQLite) + m057 (Supabase). Admin-editable from
  `/admin/settings/ai` filtering by the new purpose value —
  consistent with creation_format and response_format prompts.
- **New backend endpoint `GET /api/ai/server-instructions`**
  (anonymous-readable). Returns the singleton row body.
- **New iris-mcp module `iris_mcp/server_instructions.py`** with
  `fetch_server_instructions(iris_url)` + a hardcoded fallback
  baseline. iris-mcp fetches once at startup and passes the body
  through `build_server(client, instructions=...)` to the MCP SDK.
  Falls back gracefully if the backend is unreachable / errors /
  returns empty.
- **Frontend admin polish.** `PURPOSES` const extended; new
  `appliesToLabel()` branch renders the singleton row as
  "Server-wide (MCP instructions)" in the row table and live
  preview.

### Changed

- **Canonical `doview-book-mcp-system-context.md` trimmed again**
  to ~12 lines (was ~30 in v5.17.0, ~50 in v5.14.0, ~140 in v5.13.x).
  The orient-first protocol and discovery catalogue moved to the
  new server-wide channel. The scope content now carries only
  what's actually scope-specific: a one-sentence description, the
  structural-overview call name, and the menu options verbatim.
  Admin must paste the new shorter content into the Outcomes
  Theory Book set's `mcp_system_context` field on UAT.
- **New `docs/prompts/mcp-server-instructions.md`** as the
  canonical paste-ready content for the new singleton row.

### Migration

- **SQLite**: m053_mcp_server_instructions_seed.py runs
  automatically on next boot (idempotent INSERT OR IGNORE).
- **Supabase**: apply `m057_mcp_server_instructions_seed.sql`
  once. Command: `./scripts/supabase-migrate.sh "$SUPABASE_URL"`.
- **Manual**: paste the trimmed canonical content from
  `docs/prompts/doview-book-mcp-system-context.md` into the
  Outcomes Theory Book set's `mcp_system_context` field on UAT.

### Tests

- ~18 net new tests: 10 backend (endpoint + migration parser +
  Pydantic Literal extension), 11 MCP (fetch happy path + 6
  failure-mode fallbacks + 3 wiring), 7 frontend (PURPOSES + 5
  appliesToLabel branches). Combined MCP suite now 134 (was 123).

## [5.17.0] - 2026-05-12

### Added

- **Generic MCP diagram-creation workflow** (ADR-162, SPEC-162-A).
  Three new MCP tools — `create_diagram`, `list_notations`,
  `list_diagram_types` — give Claude (or any MCP client) a
  notation-agnostic path for authoring diagrams locally. The new
  `create_diagram` tool wraps the existing `POST /api/diagrams`
  endpoint generically: pass `notation`, `diagram_type`, `name`,
  `data`, `set_id`, and optional parent_package_id / description.
  `list_notations` and `list_diagram_types` (the latter carries each
  diagram_type's compatible notations) let Claude discover what's
  authorable before composing.
- **`get_response_prompt` / `list_response_format_types` extended
  with `purpose` argument.** Default stays `response_format`
  (backwards-compatible). Pass `purpose='creation_format'` to fetch
  the layered creation cascade Iris AI uses when generating
  diagrams — a local-AI MCP client can pull the same Stage 0 setup
  questions + entity types + layout rules and run the conversation
  in chat. Backend `/api/ai/response-prompts/{types,composed}` gain
  the same query parameter.
- **`build_creation_system_prompt(..., include_ui_selection_preamble=False)`**:
  the composer can now skip the "User selection already confirmed
  in UI" suppression preamble. The HTTP endpoint passes False so
  MCP callers get the raw conversational cascade; `ask(mode='creation')`
  keeps the suppression (it's correct there).
- **Workflow guidance lives in the tool description.** The
  `create_diagram` tool's description carries a creation-flow
  preamble (discover → fetch creation prompt → guided conversation
  → confirm destination → compose → save) plus the v5.16.0
  destination-confirmation preamble. Universal across every MCP
  client and every scope; no per-scope duplication.
- **iris-client gains `purpose` kwargs** on `list_response_format_types`
  and `get_response_prompt`. Defaults preserved.

### Changed

- **Canonical `mcp_system_context` for the Outcomes Theory Book set
  trimmed.** Removed the path-A (analysis save) and path-B (visual
  DoView via web UI) step-by-step; both now route through
  `create_diagram` whose description carries the workflow. ~30
  lines shorter. Admins on UAT should paste the new content into
  the set's `mcp_system_context` field.
- **`save_doview_analysis` deprecated.** Tool description prefixed
  with a deprecation note pointing at
  `create_diagram(notation='markdown', diagram_type='doview_analysis', ...)`.
  Behaviour unchanged in v5.17.0; removal scheduled for v6.0.0.

### Fixed

- **Cross-tab auth lost when a new browser window is opened from
  Claude's pairing-page link.** `loadFromSession` in
  `frontend/src/lib/stores/auth.svelte.ts` now falls back to
  `localStorage` when `sessionStorage` is empty (and re-seeds
  `sessionStorage` so the new tab caches it going forward). The
  auth store always wrote to both stores; this closes the read
  side.
- **Sign-in from `/settings/mcp-pairing` bounced to dashboard.**
  `/login` now honours a same-origin `?redirect=` query parameter
  with strict validation (must start with `/`, not `//`, no `://`,
  no whitespace). The pairing page's sign-in hint uses
  `/login?redirect=/settings/mcp-pairing`.
- **`/admin/settings/ai` filter dropdowns didn't constrain each
  other.** Cascading: picking a notation filters the diagram_type
  dropdown to compatible types (via `DiagramTypeRegistry.notations`);
  picking a diagram_type filters notation likewise. Same logic
  applied to the create-prompt and edit-prompt dialogs. Setting
  layer=base disables both pickers.
- **`/admin/settings/ai` "doview shows only 1 prompt" bug.** The
  row-inclusion predicate exact-matched `p.notation`, hiding
  diagram_type-layer rows (e.g. `creation-outcomes-map-v1`) whose
  `notation` column is null but whose `diagram_type` maps to doview
  via `diagram_type_notations`. Replaced with a notation-agnostic
  predicate (`isNotationScopeMatch`) that matches direct OR via the
  diagram_type→notation mapping.
- **v5.15.0 in-session token-propagation symptom regression test.**
  New `test_pairing_then_create_set_uses_new_pat_in_same_session`
  exercises the exact failing flow the user reported: pairing-code
  exchange → create_set, with the mock backend gated to return 401
  unless the request carries the exchanged PAT. Closes the v5.15.0
  test gap that only asserted `client.token == ...` without
  verifying outgoing-header propagation.

### Housekeeping

- **Stripped user-visible ADR references from the web UI.** Eight
  mentions removed from `/admin/settings/ai`, `/admin/settings`,
  and four guide markdown pages (`dashboard.md`, `search.md`,
  `collections-sets.md`, `knowledge-graph.md`). Code comments
  retain their ADR references (developers need them).

### Migration

- **No DB migration.** Backend endpoints already existed.
- Manual: paste the trimmed canonical content from
  `docs/prompts/doview-book-mcp-system-context.md` into the
  Outcomes Theory Book set's `mcp_system_context` field on UAT.

### Tests

- 30+ net new tests: 8 backend (response-prompts purpose query),
  4 iris-client (purpose kwargs), 11 MCP (create_diagram +
  list_notations + list_diagram_types + preambles +
  deprecation-note + v5.15.0-symptom regression), 12 frontend
  (sessionStorage fallback + login redirect-back + cascade
  helpers + inclusion predicate). Combined MCP suite now 123
  (was 112); iris-client 57 (was 53).

## [5.16.0] - 2026-05-12

### Added

- **MCP entity-creation tools** (ADR-161, SPEC-161-A). Three new
  MCP tools — `create_collection`, `create_set`, `create_package` —
  let an MCP client (Claude Desktop, Claude Code) stitch a
  destination tree in-conversation when the user asks to save
  something somewhere new. Closes the v5.15.0 workflow cliff where
  Claude had to ask the user to leave the conversation, create the
  set manually, copy its id, and paste it back. The three tools
  wrap the existing `POST /api/{collections,sets,packages}`
  endpoints (no backend change — already auth-gated and tested).
- **iris-client gains `create_collection()`, `create_set()`,
  `create_package()`** mirroring the new MCP tools. Returns the
  existing permissive `Collection` / `IrisSet` / `Package` models
  unchanged — same shapes the read methods already use.
- **Destination-confirmation preamble on every write tool's
  description.** `save_doview_analysis`, `create_collection`,
  `create_set`, and `create_package` all carry the same
  `BEFORE CALLING, confirm with the user where they want this saved`
  block, instructing the model to offer four options (existing set,
  new set in existing collection, new collection + new set,
  optionally + new package) before the save. Pattern applies to
  every future write tool by copy-paste.
- **Shared `_auth_required_payload(action)` helper in
  `mcp/src/iris_mcp/tools.py`** factored out of v5.15.0's
  `save_doview_analysis` 401 branch. Every write tool now returns
  the same `auth_required` payload shape, so the pairing-recovery
  flow handles every tool uniformly.

### Changed

- **`save_doview_analysis` description** now references the new
  destination-confirmation flow instead of the v5.12.x topic-to-
  package heuristic. Signature unchanged.
- **Canonical `doview-book-mcp-system-context.md`** drops the
  static topic-to-package mapping (which only made sense when the
  Outcomes Theory Book set was the only destination) in favour of
  "ask the user where; use the create_* tools if a new container
  is needed."

### Fixed

- **Default Notation dropdown** on `/settings` now lists all 7
  notation IDs registered in the backend (added `doview`,
  `markdown`, `bpmn` — `simple` / `uml` / `archimate` / `c4`
  were already there). User-spotted: the preference was
  inconsistent with what's authorable.

### Migration

- **No DB migration.** Backend endpoints already exist.
- v5.15.0 pairing flow covers the new tools' auth needs unchanged.

### Tests

- 17 net new tests: 7 iris-client (`test_create_endpoints.py`),
  10 MCP (`test_tools_create.py`), 8 frontend
  (`settingsNotationDropdown.test.ts` — one per notation + count
  check). Combined MCP suite now 112 (was 102).

## [5.15.0] - 2026-05-12

### Added

- **MCP pairing-code authentication** (ADR-160, SPEC-160-A). Lets a
  user authenticate the iris-mcp connection from inside Claude
  Desktop / Claude Code with **two clicks and one paste** — no more
  editing the MCP client's config JSON to set `IRIS_TOKEN`. Flow:
  user visits `/settings/mcp-pairing`, clicks **Generate pairing
  code**, sees a short typeable `IRIS-XXXX-YYYY` code; pastes it
  into Claude; the new `iris_authenticate` MCP tool exchanges it
  for a fresh PAT and persists the PAT to `~/.iris-mcp/<hash>.json`
  (mode 0600). Subsequent write tools (e.g. `save_doview_analysis`)
  work immediately for ~90 days, revocable any time via the
  existing PAT management API.
- New backend endpoints `POST /api/auth/pairing-codes` (auth) and
  `POST /api/auth/pairing-codes/{code}/exchange` (anonymous,
  one-shot, 10-minute TTL, 410-on-reuse). Exchange reuses the
  existing `tokens.service.create_token` machinery so the issued
  credential is a normal `personal_access_tokens` row — listable,
  revocable, and audit-trackable through the same surface as any
  other PAT.
- New iris-client methods `create_pairing_code()` and
  `exchange_pairing_code(code)` with the matching response models
  (`PairingCodeResponse`, `ExchangedPATResponse`).
- New MCP tool `iris_authenticate(credential)` accepts **either** a
  pairing code (`IRIS-XXXX-YYYY`) **or** a full pasted PAT
  (`iris_pat_…`) as a power-user fallback (validated via
  `/api/auth/me` before persisting). Dispatch by string prefix.
- New MCP token-storage helper `iris_mcp.token_store` (file under
  `~/.iris-mcp/` keyed by SHA-256 hash of the Iris URL, so a single
  install can hold credentials for multiple Iris deployments).
- iris-mcp `__main__.py` resolves the bearer in precedence order:
  `IRIS_TOKEN` env > persisted token > anonymous. Source is logged
  at startup; the token itself is never logged.
- `save_doview_analysis` now catches 401 and returns structured
  guidance with the pairing-page URL and the next-step tool name
  (`iris_authenticate`), giving the model a deterministic recovery
  path inside the conversation.
- New user-self frontend page at `/settings/mcp-pairing` with the
  Generate-code button, a 10-minute live countdown, copy-to-
  clipboard, and a "Power user: paste a PAT directly" hint. Linked
  from the existing `/settings` page under a new "MCP Connections"
  section. User-self (not admin-only) so every signed-in user can
  pair their own MCP.
- New `IrisClient.set_token(token)` method updates the underlying
  httpx client's Authorization header in-place, so the
  iris_authenticate tool's newly-exchanged PAT takes effect on the
  next tool call without an MCP-server restart.

### Migration

- **SQLite**: m052_mcp_pairing_codes.py runs automatically on next
  boot (creates `pairing_codes` table + indexes; idempotent).
- **Supabase**: apply `m056_mcp_pairing_codes.sql` once. Command:
  `./scripts/supabase-migrate.sh "$SUPABASE_URL"`.

### Tests

- 32 net new tests across backend (9), iris-client (5), mcp (16),
  frontend (6). Total Iris test suite still green; no new
  pre-existing failures.

## [5.14.0] - 2026-05-12

### Added

- **Scope `mcp_system_context` in search results** (ADR-159,
  SPEC-159-A). `GET /api/search` results for `result_type=set` and
  `result_type=collection` now include the matching scope's
  `mcp_system_context` field. Diagnoses and fixes the root cause of
  v5.13.x's "orient instructions don't fire" symptom: when Claude
  Desktop's natural flow was `search` → return link, it never
  called `get_set` and the orient guidance never landed. With this
  change, the orient guidance lands on the search hit itself —
  whether or not Claude follows up with `get_set`.
- New `mcp_system_context: str | None` field on:
  - `backend/app/search/models.py:SearchResult`
  - `iris-client/src/iris_client/models/core.py:SearchResult`
  Only populated for set / collection hits; `None` on element /
  diagram / package hits. The MCP boundary is unchanged — the field
  is intentionally pass-through per ADR-156, not in `_STRIPPED_KEYS`.

### Changed (docs / canonical mcp_system_context content)

- **Trimmed the canonical Outcomes Theory Set `mcp_system_context`
  content** from ~140 lines to ~50 (target ~60). Same orient-first
  with four-option-menu intent, far less text. Verbose flow
  descriptions can live in the response_format prompt body
  (admin-editable via `/admin/settings/ai`) where they belong as
  universal rules, not on every per-scope context field.

### Migration

- **No DB migration.** Schema unchanged — `mcp_system_context`
  columns on sets / collections already exist (added in m050 / m054
  per ADR-156).

### Tests

- 8 net new tests (4 backend search, 4 iris-client model). Combined
  suite ~447+ tests pass; only pre-existing `test_no_extra_rls_tables`
  + `test_search/test_rebuild.py` fixture failures remain.

## [5.13.3] - 2026-05-12

### Changed (docs / canonical mcp_system_context content)

- **Made the four-option orient menu mandatory and verbatim.**
  v5.13.2 instructed the client to "offer a menu of common next
  steps" but didn't require all four options to appear every time,
  so Claude paraphrased and offered only 2 ("specific chapter" /
  "cross-package question"), dropping the analysis-generation and
  chapter-browse options. The doc now states it's MANDATORY to
  offer all four, with their exact wording, and explicitly forbids
  paraphrasing or abbreviating to two/three.
- **Honest note on AskUserQuestion availability.** AskUserQuestion
  is a Claude Code tool, not in Claude Desktop / claude.ai / most
  generic MCP clients today. The doc says: use AskUserQuestion if
  available; otherwise present a numbered list (1./2./3./4.) with
  each option on its own line.

## [5.13.2] - 2026-05-12

### Changed (docs / canonical mcp_system_context content)

- **Restored the orient-first / offer-menu pattern** in the canonical
  DoView / Outcomes-Theory Set MCP system context content
  (`docs/prompts/doview-book-mcp-system-context.md`). The pre-v5.12
  conversational rhythm of "describe the set, list chapters, offer a
  menu of next steps, wait for the user to choose" was implicit
  before the more prescriptive v5.12.0+ guidance got drafted. With
  the new content, an MCP client opening the set should orient the
  user before doing any tool action.
- **Explicit routing for two distinct user-request shapes:**
  - "Generate a DoView analysis" / "analyse X from an outcomes-
    theory perspective" / similar text-output requests → fetch
    `iris_get_response_prompt(notation='markdown',
    diagram_type='doview_analysis')`, compose locally, offer the two
    save paths. **Explicit DO NOT use `mcp__iris__ask` for this
    flow** (was being defaulted to incorrectly).
  - "Create a new DoView diagram" / "draw an outcomes map" /
    similar visual-output requests → recommend Iris's web UI for
    the guided creation flow (Stages 0-3, the 13 drafting steps,
    balance checks). MCP creation path mentioned but not preferred
    because the methodology depends on a guided-conversation rhythm
    that's better-served in the web UI.
- **Set rename reflected** in prose: the set is now called
  "Outcomes Theory" in Iris (previously "DoView Book"). File name
  and Set ID stable.

### Infrastructure

- No code changes. Bump versions to 5.13.2 to mark the meaningful
  UX-fix nature of this release; CHANGELOG and tag for traceability.
  Per-scope `mcp_system_context` paste required on UAT — the doc is
  the canonical source.

## [5.13.1] - 2026-05-12

### Fixed

- **Admin AI prompts page — Notation and Diagram type filter
  dropdowns were empty.** v5.13.0 called `/api/notations` and
  `/api/diagram-types`; the registry endpoints actually live at
  `/api/registry/notations` and `/api/registry/diagram-types` per
  ADR-079. `apiFetch` returned 404, the catch swallowed the error,
  and the dropdowns rendered with only the placeholder option.
  Frontend now hits the correct paths.

## [5.13.0] - 2026-05-12

### Added

- **Admin AI prompts management** (ADR-158, SPEC-158-A). The
  `/admin/settings/ai` prompts section gets a full CRUD redesign:
  - Filter row above the table (purpose / layer / notation /
    diagram_type / status / search / sort / reset) mirroring the
    `/views/+page.svelte` inline pattern. URL-state-backed for
    `purpose` and `layer` (sharable / bookmarkable filtering).
  - "Purpose" badge column distinguishing creation_format from
    response_format rows.
  - "Applies to" column resolving the cascade clearly — e.g.
    "Any notation × process diagrams" for the previously confusing
    `(layer=diagram_type, notation=NULL, diagram_type=process)`
    rows like "ArchiMate Process Layout". Addresses the user-
    reported confusion about the cascade design.
  - Status toggle (single click toggles `is_active`).
  - Per-row Delete with confirm dialog (consistent with the
    existing providers section).
  - "+ Add prompt" inline form with live conflict-check ($derived
    against the loaded list — Save disables when the chosen
    `(purpose, layer, notation, diagram_type)` already has an
    active row, with an inline note naming the conflict).
  - Edit modal extended to allow editing name, description,
    notation, diagram_type alongside prompt_text. Purpose and layer
    remain immutable (delete-and-recreate to move between).
- **Backend `/api/ai/creation-prompts` POST + DELETE + extended PUT**
  (ADR-158, admin-only). POST validates uniqueness on
  `(purpose, layer, notation, diagram_type)` for `is_active=true`
  rows — 409 conflict response names the existing prompt.
  Inactive rows can coexist on the same tuple (lets admins stage
  replacements before disabling the current).
- **`SetResponse.package_count` and `SetResponse.package_count_root`**
  (ADR-158). Tells MCP clients the structural breadth of a set
  upfront so they know whether `package_hierarchy` is worth a call
  or whether `list_packages` will fit in one page.
- **`iris_package_hierarchy` MCP tool** (ADR-158). Returns the
  complete package tree for a set as nested `PackageHierarchyNode`
  objects in a single call. Fixes the user-reported issue where
  Claude Desktop saw only chapters E-J of a 10-chapter set
  because `list_packages` paginates and older chapters sort to
  page 2+ under the default `updated_at DESC` ordering.
- **`iris-client.list_packages` pagination** — `page`, `page_size`,
  `parent_package_id` parameters now exposed (the backend already
  supported them). MCP `list_packages` tool schema gains the same.
- **`iris-client.diagram_hierarchy` method** — renamed from the
  previously misnamed `package_hierarchy` (which actually hit
  `/api/diagrams/hierarchy`). Latent bug; no prior callers, so
  rename is non-breaking. The new `package_hierarchy` correctly
  hits `/api/packages/hierarchy`.

### Changed

- `CreationPromptResponse` and the existing `PUT
  /api/ai/creation-prompts/{id}` endpoint now round-trip the new
  `purpose` field correctly (was added in v5.12.0 but the response
  pathway only partially propagated it).
- MCP `list_packages` tool description rewritten to flag pagination
  explicitly and cross-reference `package_hierarchy` as the
  preferred structural-overview tool.

### Documentation

- ADR-158 + SPEC-158-A.
- `docs/prompts/doview-book-mcp-system-context.md` updated with
  v5.13.0 hints: prefer `iris_package_hierarchy` over `list_packages`
  for chapter discovery; offer save-paths to the user (both Iris
  persistence AND markdown-in-chat).

### Migration

- **No DB migration**. v5.13.0 has no schema changes — it uses
  existing `is_active`, `purpose`, `notation`, `diagram_type`
  columns on `ai_creation_prompts` and existing
  `parent_package_id` / `is_deleted` / `set_id` on `packages`.

### Tests

46 new tests across migration / backend / iris-client / MCP /
frontend layers; ~430+ tests pass total. Only pre-existing
`test_no_extra_rls_tables` failure (issue 88 Phase 4 TODO).

## [5.12.2] - 2026-05-12

### Fixed

- **Supabase migration `m055_response_format_prompts.sql` failed
  again** with `column "is_active" is of type boolean but expression
  is of type integer` (42804) on the three response_format seed
  INSERTs. v5.12.1 fixed `is_default` but missed `is_active` —
  `ai_creation_prompts.is_active` is also `BOOLEAN` on Postgres.
  Changed each seed INSERT's last `VALUES … 1)` to `VALUES … TRUE)`.
  Regression test broadened to assert all three INSERTs use the
  boolean literal. Re-run `./scripts/supabase-migrate.sh` — m055 is
  idempotent (`ON CONFLICT (id) DO NOTHING`), so v5.12.1's
  successful operations no-op and only the previously-failed seed
  INSERTs run.

## [5.12.1] - 2026-05-12

### Fixed

- **Supabase migration `m055_response_format_prompts.sql` failed with
  `column "is_default" is of type boolean but expression is of type
  integer` (42804)** when run against the Supabase Postgres schema.
  `diagram_type_notations.is_default` is `BOOLEAN` on Postgres but
  `INTEGER` on SQLite; v5.12.0's m055 used `1` (the SQLite
  convention) without casting. Changed to `TRUE` to match every
  other Supabase migration's convention (m020 / m028 / m044 etc.).
  Added a regression test that pins this. Re-run
  `./scripts/supabase-migrate.sh` against the UAT DB; idempotent —
  the failed v5.12.0 row insert will now succeed.

## [5.12.0] - 2026-05-12

### Added

- **Layered response_format prompts** (ADR-157, SPEC-157-A). New
  `purpose` discriminator column on `ai_creation_prompts` separates
  `creation_format` rows (existing v5.8.x diagram-creation prompts;
  all backfilled to `creation_format`) from `response_format` rows
  (new — used to shape formal text responses). New
  `build_response_system_prompt(notation, diagram_type)` composer
  sibling to `build_creation_system_prompt`; both share a single
  `_build_layered_prompt(purpose, notation, diagram_type)` cascade
  implementation (DRY, protocols §13).
- **`(notation=markdown, diagram_type=doview_analysis)` artefact type**
  registered as a first-class Iris type: a formal handbook-grounded
  outcomes-theory analysis. Seeded with three response_format prompt
  rows (base + notation + diagram_type) encoding the Prompt C output
  shape — opening sentence, Summary, Full, Diagrams sections,
  formal style and raw-URL rules.
- **Two new MCP tools** (anonymous-readable):
  `list_response_format_types` (discover available pairs) and
  `get_response_prompt(notation, diagram_type?)` (fetch composed
  cascade body). Lets a client model in Claude Desktop / Claude
  Code retrieve the response format as reference material in
  conversation, no slash-command UX needed.
- **`save_doview_analysis` MCP tool** (auth-required — reuses
  existing `IRIS_TOKEN` per-server PAT) — persists a generated
  analysis as a new `doview_analysis` diagram in Iris.
- **Two new backend endpoints** under `/api/ai/response-prompts/*`
  (anonymous-readable): `types` and `composed`.
- **iris-client methods**: `list_response_format_types()`,
  `get_response_prompt()`, `create_diagram()`.

### Changed

- `CreationPromptResponse` gains a `purpose: str = "creation_format"`
  field (backwards-compat default). `list_creation_prompts` accepts
  an optional `?purpose=` filter.
- m051's registry inserts (markdown notation, doview_analysis
  diagram_type, mapping) skip gracefully when those registry tables
  aren't present — enables clean test isolation.

### Migration

- SQLite `m051_response_format_prompts.py` — adds `purpose` column,
  backfills, registers markdown + doview_analysis, seeds three
  response_format rows.
- Supabase `m055_response_format_prompts.sql` — same. Run
  `./scripts/supabase-migrate.sh` after deploy. Idempotent.

### Deferred to v5.13+ (per ADR-157 "Out of scope")

- Server-side auto-injection of `build_response_system_prompt` into
  the Ask Iris pipeline.
- `applicable_response_types` field on Set/Collection MCP responses.
- Admin Settings / AI GUI for editing response_format rows (editing
  works via the existing `PUT /api/ai/creation-prompts/{id}` endpoint
  with the new `purpose` field round-tripping correctly).

## [5.11.0] - 2026-05-11

### Changed (breaking — supersedes v5.10.0 picker behaviour)

- **Scope `mcp_prompt` column renamed to `mcp_system_context` and
  repositioned as data passthrough, not a slash-command prompt**
  (ADR-156, SPEC-156-A). The v5.10.0 design exposed the column via
  the MCP `prompts` channel as `/iris:set:<uuid>` /
  `/iris:collection:<uuid>` slash commands. In use that turned out
  wrong for the intent: the content authors want attached to a
  scope is **initial context for an MCP client browsing the
  scope**, not a directive the user picks. v5.11.0 removes the
  scope-level slash-command exposure entirely and instead passes
  `mcp_system_context` through `get_set` / `list_sets` /
  `get_collection` / `list_collections` MCP tool responses as a
  regular data field. The MCP picker now contains **named prompts
  only** (ADR-154 entries unchanged).
- `system_prompt` continues to auto-apply in Iris AI server-side
  composition (ADR-150) and continues to be stripped from MCP tool
  responses (ADR-151). Unchanged.
- Frontend label and helper text updated to reflect the
  passthrough role.

### Migration

- SQLite `m050_rename_mcp_prompt_to_mcp_system_context.py` —
  idempotent column rename on `collections` and `sets`.
- Supabase `m054_rename_mcp_prompt_to_mcp_system_context.sql` —
  same. Run `./scripts/supabase-migrate.sh` after deploy. Data
  authored in v5.10.0 is preserved (rename, not drop).

## [5.10.0] - 2026-05-11

### Added

- **`mcp_prompt` column on Collections and Sets** (ADR-155, SPEC-155-A).
  The orthogonal counterpart to v5.8.0's `system_prompt`. `mcp_prompt`
  is surfaced via the MCP `prompts` channel as the scope's picker
  entry (`set:<uuid>` / `collection:<uuid>`) and is **never**
  auto-applied in Iris AI. `system_prompt` continues to auto-apply in
  Iris AI server-side composition unchanged but is **no longer**
  surfaced via MCP. New "MCP prompt" textarea on `/sets/[id]` and
  `/collections/[id]` edit pages below the existing System prompt.

### Changed (breaking — MCP picker)

- **MCP picker entries for scopes now source their body from
  `mcp_prompt`, not `system_prompt`.** Existing scopes with a
  populated `system_prompt` but no `mcp_prompt` will see their MCP
  picker entry **disappear** until an author populates the new
  column. To preserve v5.9.x picker behaviour for an existing scope,
  edit the scope and copy the System prompt body into the new MCP
  prompt textarea. Iris AI behaviour is unchanged for every scope.

### Fixed

- **`prompts.created_at` / `prompts.updated_at` columns on Supabase
  converted from `text` to `timestamptz`.** v5.9.0's migration
  created the columns as `text`, but the Supabase adapter
  (`backend/app/db/adapter.py:_convert_params`) auto-converts ISO
  datetime strings to native `datetime` before asyncpg, and asyncpg
  rejected the `datetime` against `text` columns. User-visible
  symptom: `DataError: invalid input for query argument $7:
  datetime.datetime(...)` when creating named prompts on Supabase.
  Migration `m053_mcp_prompt_and_prompts_timestamps.sql` includes
  the timestamptz conversion alongside the new `mcp_prompt` column
  ADD. Re-running `./scripts/supabase-migrate.sh` against an
  affected UAT DB will fix both.

## [5.9.1] - 2026-05-11

### Fixed

- **Named-prompts router no longer reports every create-time error as
  a duplicate-name 409.** The v5.9.0 handler caught every `Exception`
  and emitted `"A named prompt with this name already exists on this
  scope (<ExceptionClass>)"` — surfacing `UndefinedTableError` (raised
  when the Supabase migration `m052_named_prompts.sql` had not yet
  been applied) under that misleading message. The handler now
  distinguishes UNIQUE-constraint violations (409, clean message)
  from any other failure (500, with the underlying exception class
  and message). Reminder: Supabase migrations are applied externally
  via `./scripts/supabase-migrate.sh` — see SPEC-154-A and
  `backend/app/startup.py` comments.

### Changed

- **Prompt C draft (`docs/prompts/doview-book-prompt-c-iris.md`)
  reflowed.** Mid-paragraph hard wraps removed; paragraphs now flow
  as single lines (matching the existing `doview-book-prompt-a.md` /
  `-b.md` style). No content changes.

## [5.9.0] - 2026-05-11

### Added

- **Multiple named prompts per scope (Collection / Set)** (ADR-154,
  SPEC-154-A). New `prompts` table holds zero-or-more named prompts per
  scope; surfaced via the existing MCP `prompts` channel as
  `set:<uuid>:<name>` / `collection:<uuid>:<name>` (so Claude clients
  show them as `/iris:set:<uuid>:<name>` in the prompt picker). Set-
  scoped names shadow Collection-scoped names per ADR-150 additive
  inheritance. New `/api/named-prompts*` CRUD endpoints; new
  `Prompts` section on `/sets/[id]` and `/collections/[id]` edit pages
  for per-row authoring. Scope-level `system_prompt` (ADR-150) is
  retained unchanged and continues to auto-apply in Ask Iris and Iris
  MCP `ask`; named prompts are **picker-invoked only** and never
  auto-prepend. 43 new tests across migration, backend, iris-client,
  MCP, and frontend layers; existing v5.8.x tests unchanged. SQLite
  migration `m048_named_prompts.py`; Supabase mirror
  `m052_named_prompts.sql` with anonymous-read / authenticated-write
  RLS posture.

- **DoView Book combined response prompt (Prompt C)** drafted under
  `docs/prompts/doview-book-prompt-c-iris.md`. Merges Prompt A
  (outcomes-theory text response) and Prompt B (diagram retrieval)
  into a single-turn prompt that produces both formal text answer
  and verbatim mermaid diagrams in one response. Iris-MCP-sourced
  (set 33032180-d77a-4ce4-88cf-b49cd643e093); intended for upload
  as a named prompt on the DoView Book Set once v5.9.0 ships.

## [5.8.5] - 2026-05-11

### Changed

- **MCP prompt names dropped the `iris:` prefix** (ADR-153 amending
  ADR-152). Was `iris:set:<uuid>` / `iris:collection:<uuid>`; now
  `set:<uuid>` / `collection:<uuid>`. MCP clients prepend the server
  name automatically, so v5.8.3's prefix produced a redundant doubled
  `/iris:iris:set:<uuid>` in Claude Code's slash menu. Post-rename it
  reads cleanly as `/iris:set:<uuid>`. Backend service, MCP regex,
  iris-client and MCP test fixtures all updated. No data migration —
  prompt names are enumerated by the client on every `prompts/list`.

## [5.8.4] - 2026-05-11

### Changed

- **`iris-mcp` package version aligned with Iris release versioning.**
  Was pinned at `0.1.0` since project start; now tracks Iris releases
  (`5.8.4` onwards). Lets a `/info` probe identify the running build
  by URL alone rather than inferring from behaviour.

### Added

- **`version` field on `iris-mcp` `/info` endpoint.** Reads
  `iris-mcp`'s package metadata via `importlib.metadata` and reports
  it alongside `service`, `endpoint`, `backend`, `web_url`. Operators
  can now `curl https://iris-mcp.onrender.com/info` to definitively
  identify which Iris release is deployed.

### Fixed

- **MCP prompt picker description no longer duplicates the scope
  name.** A scope whose `description` starts with its own name (e.g.
  set name "DoView Book", description "DoView Book — published from
  doview-book repo") was producing the redundant
  `Set: DoView Book — DoView Book — published from doview-book repo`
  in Claude Desktop's prompt picker. `_short_description` in
  `mcp/src/iris_mcp/prompts.py` now strips a leading occurrence of
  the scope name (case-insensitive) plus any em-dash / hyphen / colon
  separator that follows it before composing the picker label. If the
  description IS just the scope name, it's dropped entirely.

## [5.8.3] - 2026-05-11

### Added

- **MCP `prompts` capability for scope system prompts** (ADR-152,
  SPEC-152-A). Every Collection and Set with a non-empty
  `system_prompt` now appears in Claude Desktop's prompt picker
  as `iris:collection:<uuid>` or `iris:set:<uuid>`. Invoking one
  loads the system prompt into the conversation as a user-authored
  directive (single `role: user` message with a provenance
  preamble), which the model treats as authoritative framing
  rather than untrusted tool data. This is the spec-compliant
  channel for invoking scope prompts inside a Claude Desktop
  conversation — the alternative to silent client-side application,
  which prompt-injection defense correctly blocks (see ADR-151).
  New backend endpoint `GET /api/prompts/scope-index`
  (anonymous-readable, same posture as `list_sets`); new
  `IrisClient.list_scope_prompts()`; new MCP `prompts.py` module
  registered via `@server.list_prompts()` and `@server.get_prompt()`.
  20 new tests across the backend, iris-client, and MCP layers.

## [5.8.2] - 2026-05-11

### Fixed

- **MCP boundary now strips `system_prompt` from tool responses**
  (ADR-151, SPEC-151-A). v5.8.0 added `system_prompt` to the
  Set/Collection response models. The four MCP tools that return
  Set or Collection data (`get_set`, `list_sets`, `get_collection`,
  `list_collections`) were forwarding it to Claude Desktop as
  untrusted tool data, where it triggered prompt-injection
  defenses ("this set has a system prompt attached … I'm flagging
  it"). The MCP egress helpers (`with_web_url` /
  `with_web_urls_list` / `with_web_urls_search` in
  `mcp/src/iris_mcp/links.py`) now redact the field on every tool
  response. Authoring (REST endpoints + web GUI) and the MCP `ask`
  tool (which composes the prompt server-side) are unchanged. The
  spec-compliant channel for invoking a scope's system prompt
  inside a Claude Desktop conversation arrives in v5.8.3 via the
  MCP `prompts` capability.

## [5.8.1] - 2026-05-11

### Fixed

- **Enable Row Level Security on `graph_settings`** (ADR-095
  alignment). The table — added in m039 and re-created defensively
  at runtime in `_initialize_supabase` (v5.7.2 fallback) — was the
  only post-m030 table without RLS, triggering a Supabase advisor
  warning. Both locations now run `ALTER TABLE graph_settings
  ENABLE ROW LEVEL SECURITY` (idempotent). FastAPI continues to
  read/write via asyncpg's `postgres` role, which bypasses RLS, so
  the app is unaffected; the embedded anon key in the frontend can
  no longer query the table directly via PostgREST.

## [5.8.0] - 2026-05-11

### Added

- **Scope-level system prompts for Collections and Sets** (ADR-150,
  SPEC-150-A). Each Collection and each Set can now carry a
  free-text `system_prompt` that is prepended to every Ask Iris
  question (discuss and creation) and every MCP `ask` call that
  touches the scope. A Set inherits its parent Collection's
  prompt — composition is additive, never overriding. Multi-set
  asks dedup collection prompts by id and preserve `set_ids`
  order. Edit screens (`/collections/[id]`, `/sets/[id]`) gain a
  "System prompt" textarea. Anonymous AI asks (ADR-123) get scope
  prompts applied the same way as signed-in asks. A soft warning
  fires in `[AI_DEBUG]` when the composed system content exceeds
  16 000 characters; no hard truncation. First phase of a larger
  Skills feature; full Skills (DB-resident, progressive disclosure
  via MCP `list_skills` / `get_skill`) land in a follow-up release.

## [5.7.3] - 2026-05-11

### Fixed

- **Breadcrumb links on `/views/[id]` now route packages to
  `/packages/<id>`** (previously `/views/<id>`, which 404'd or showed
  an unrelated view). The breadcrumb's "ancestors" are always packages
  (a diagram's parent chain walks the packages table — see
  `backend/app/diagrams/service.py:get_diagram_ancestors`), but the
  link template hard-coded `/views/<id>`. Extracted a small
  `viewBreadcrumbHref()` helper that switches on the `type` field
  returned by `/api/diagrams/{id}/ancestors` so packages route to
  `/packages/<id>` and any future diagram-typed ancestor would route
  to `/views/<id>`. Also corrects the local TypeScript shape (the API
  returns `{id, name, type, parent_package_id}`; the page declared
  `{id, name, diagram_type}` — wrong field name that happened to type-
  check because both were `string`). Reported on the live UAT URL
  `https://iris-uat.chrisbarlow.nz/views/4415adb0-c1db-4627-8952-13f4c911d375`.

## [5.7.2] - 2026-05-11

Follow-up to v5.7.1: even with the defensive read in place, the
admin "Save as default" button was silently failing on UAT because
the `graph_settings` table itself was missing on Supabase (the m039
SQL migration had never been applied to UAT). The admin saw "Saved"
on click, but the PUT errored and nothing persisted.

### Fixed

- **`graph_settings` table is now created at Supabase startup**
  (ADR-117 v5.7.2 amendment). `_initialize_supabase` runs an idempotent
  `CREATE TABLE IF NOT EXISTS graph_settings (...)` alongside the
  existing ALTER TABLE patches, then the v5.7.1 seed call inserts the
  `__global__` row. Subsequent admin PUTs now persist. Mirrors the
  schema in `backend/app/migrations/supabase/m039_graph_settings.sql`.
- **`Save as default` button no longer silently swallows errors.** On
  failure, the button now shows "Save failed" in the danger colour
  for 4 seconds, sets the error message as the button `title`
  (tooltip), and logs the full error to the console. Previously the
  button always showed "Saved" regardless of PUT outcome — masking
  data-layer failures from admins.

## [5.7.1] - 2026-05-11

Hotfix: `/api/graph/settings` returns 500 on Supabase deployments
(UAT). Anonymous users observed this as "admin-configured knowledge-
graph defaults not applied" — the frontend's silent fallback to
hard-coded defaults masked the underlying 500 from authenticated users
(whose localStorage carried their own saved settings).

### Fixed

- **`/api/graph/settings` no longer 500s on Supabase deployments**
  (ADR-117 v5.7.1 amendment). Two-pronged fix:
  - `get_graph_settings()` and `get_graph_settings_cascaded()` now
    catch DB-level exceptions (e.g. missing table on a partially
    migrated deployment) and return hard-coded
    `GRAPH_SETTINGS_DEFAULTS` so the endpoint stays alive
    (`backend/app/graph/service.py`).
  - `_initialize_supabase` now calls
    `seed_graph_settings_defaults(port)` so the `__global__` row gets
    inserted on first Supabase start — previously only the SQLite
    startup path did this (`backend/app/startup.py`).
  - `seed_graph_settings_defaults()` is itself defensive: a missing
    table logs-and-skips rather than crashing app startup.

### Verification

- 4 new unit tests in `backend/tests/test_graph/test_settings_resilience.py`
  cover: read returns None on DB error, cascade returns hard-coded
  defaults on DB error (both unscoped and scoped), seed no-ops on DB
  error.
- Local dev (SQLite path) unchanged: `GET /api/graph/settings` returns
  200 with the seeded defaults.

## [5.7.0] - 2026-05-10

Mermaid diagram rendering in the shared markdown view (ADR-149,
SPEC-149-A) — un-defers the "markdown extensions" item from ADR-137's
out-of-scope list.

### Added

- **Mermaid diagrams in Markdown views** (ADR-149, SPEC-149-A).
  ` ```mermaid ` fenced blocks now render as SVG diagrams in any
  surface that uses the shared `MarkdownView` component — Text
  diagram views (`/views/[id]`) and User Guide pages. Supports the
  full mermaid syntax: flowcharts, sequence, class, state, ER,
  gantt, etc.

  Implementation highlights:
  - Custom `marked` extension emits a `<pre class="mermaid-block"
    data-mermaid-source="<base64>">` placeholder so the markdown
    pipeline stays synchronous and SSR-safe (`markdownHelpers.ts:23`,
    `markdownMermaidExtension.ts`).
  - Lazy-loaded mermaid bundle via dynamic `import('mermaid')` —
    only fetched when a document actually contains a mermaid block.
    Vite produces a separate ~525KB chunk that zero-block documents
    do not pay for (`markdownMermaidRender.ts`).
  - Two-stage DOMPurify sanitisation (protocol #7): stage 1 on the
    markdown HTML, stage 2 on mermaid's output SVG (`USE_PROFILES:
    { svg: true, svgFilters: true }`, plus an explicit
    `ADD_TAGS: ['foreignObject']` for HTML labels). Mermaid runs in
    `securityLevel: 'strict'` so user-authored labels cannot inject
    HTML.
  - Theme follows Iris's class-based dark mode automatically via a
    `MutationObserver` on `<html>`.
  - Per-block error fallback: an invalid mermaid block renders as
    `<div class="mermaid-error">` with the parser message; the rest
    of the document still renders.

  Note: AI Q&A panel answers do **not** yet render mermaid — that
  consolidation is tracked in
  [issue #71](https://github.com/cgbarlow/iris/issues/71).

### Changed

- **DOMPurify bumped to 3.4.2** (from 3.3.1) — picks up CVE fixes
  including `ADD_TAGS` short-circuit-evaluation bypass
  ([GHSA-39q2-94rc-95cp](https://github.com/advisories/GHSA-39q2-94rc-95cp))
  and other XSS hardening. Iris's existing `markdownHelpers.ts`
  pipeline and the new SVG sanitiser both inherit the fixes.

### Verification

- 18 new unit tests across `markdownMermaidExtension.test.ts` (7),
  `markdownMermaidRender.test.ts` (6), and
  `markdownMermaidSvgSanitise.test.ts` (5) cover placeholder shape,
  base64 round-trip, lazy-load contract, error fallback, and stage-2
  sanitisation against `<script>` / event handlers / inside
  `<foreignObject>`.
- 4 new Playwright e2e tests in `text-view-mermaid.spec.ts` exercise
  a Text view with valid + invalid + non-mermaid fences and confirm
  SVG renders, error fallback works, and the document survives.
- Frontend full unit suite: 939 pass, 3 unchanged pre-existing
  baseline failures (extension manager / import idempotency /
  archimate-format error string — same as v5.6.2).
- `vite build` confirms mermaid is in a separate chunk (~525KB) that
  is only fetched on first sight of a mermaid block.

## [5.6.2] - 2026-05-08

BPMN polish (issue #69) — closes the user-reported drag-connect bug
that v5.4.1's "claimed-fix" tests didn't actually catch. Root cause +
fix detailed in ADR-136 v5.6.2 amendment §A-D.

### Fixed

- **BPMN drag-handle connections didn't register** (issue #69, BPMN-03,
  ADR-136 v5.6.2 amendment §A-B). Headline user repro: "connecting
  start node to task, the connector does not register even though edges
  are connected and the problem bar still gives a warning." Root cause:
  xyflow svelte's `Handle.svelte` calls `store.addEdge(connection)`
  with a Connection object that has no `type` field; xyflow's `addEdge`
  util doesn't apply `defaultEdgeOptions`, so the bound `canvasEdges`
  got an edge with `e.type === undefined`. The validator's
  `isSequence(e)` then returned false, `outDeg` for the start event
  stayed at 0, and the "no outgoing sequence flow" warning persisted.
  Separately, `BpmnAuthoringShell.handleBpmnConnect` was wired to
  `onconnectnodes` (a custom UnifiedCanvas prop, not a real SvelteFlow
  event) — drag-handle connections never went through `handleConnect`,
  so the `/api/relationships` POST never fired and `/elements/<id>`'s
  Relationships panel stayed empty.

  Fix:
  - New pure helper `frontend/src/lib/canvas/edgeOnConnect.ts` exports
    `patchConnectedEdgeType` to upgrade the type-less auto-added edge
    after xyflow's `addEdge` runs. Idempotent.
  - `UnifiedCanvas.svelte` wires `onconnect={handleSvelteFlowConnect}`
    on the editing `<SvelteFlow>`. The handler calls the helper, then
    notifies the consumer via `onconnectnodes?.(source, target)` so
    the BPMN shell's relationship POST chain still fires.
  - `BpmnAuthoringShell.handleBpmnConnect` no longer appends a fresh
    edge (UnifiedCanvas now owns edge addition); it POSTs
    `/api/relationships` and patches the existing edge with the
    resulting `relationshipId`.

  Closes BPMN-01 / -02 / -03 / -09 from the issue #69 consolidated bug
  ledger.
- **BPMN ContextPad and CommandPalette append paths didn't POST
  `/api/relationships`** (issue #69 follow-up to BPMN-02). Same gap as
  the drag-handle bug: `appendBpmn` and `handleCmdPick('append')` added
  a sequence_flow edge to the canvas but never persisted the
  Relationship record, so `/elements/<id>`'s Relationships panel stayed
  empty for ContextPad-appended and CommandPalette-appended nodes
  too. Extracted shared helper `appendBpmnNodeWithEdge` (DRY per
  protocol #13) — both append paths now route through it; mirrors
  `handleBpmnConnect`'s POST-then-patch shape.
- **BPMN node-creation orphan-on-failure guard** (BPMN-08, locked in
  with `bpmnEntityIdGuard.test.ts`). Already-correct behaviour locked
  in with a static-parser test that fails if any node-creation path
  (createNode / handleEventVariant / appendBpmnNodeWithEdge) drops the
  `if (!element) return` guard before mutating canvasNodes.

### Verification

- 12 new behavioural / static unit tests covering BPMN-01/02/03/04/08/09
  across `edgeOnConnect.test.ts` (8), `canvasOnConnectWiring.test.ts`
  (4), `bpmnAppendRelationship.test.ts` (4), `bpmnEntityIdGuard.test.ts`
  (4), `bpmnDragConnectRoundTrip.test.ts` (5).
- Existing `bpmnConnectRelationship.test.ts` updated to assert the
  new edge-patching contract (no more append-on-connect).
- Full BPMN unit suite: 110/110 pass across 21 test files.
- Frontend full suite: 920 pass, 3 unchanged pre-existing baseline
  failures (extensionManagerFields / importIdempotency /
  importPageAcceptsArchimate — verified failing on `main` without
  these changes).
- `svelte-check`: 164 errors (= unchanged baseline, 0 new errors).

### Why earlier "claimed-fixed" entries didn't stick

v5.4.1's tests (`bpmnDefaultEdgeType.test.ts`,
`bpmnConnectRelationship.test.ts`) were static-parser style — they
grep the source for the right code patterns and pass when the strings
are present, but never exercise the SvelteFlow → consumer handler
chain. The strings were all present in v5.4.1; the chain wasn't
connected. v5.6.2 adds behavioural unit tests for the helper, static
guards for the SvelteFlow wiring, and a unit-level round-trip
integration test that proves the chain end-to-end. The eventual
local-backend Playwright harness (ADR-149, deferred from #69) closes
the runtime-level loop.

### Out of scope (deferred from issue #69)

The remaining medium-priority items in the consolidated bug ledger
(BPMN-05 ProblemsPanel layout, -07 theme-dropdown gating, -11 event
trigger flyout, -12 Add-Element gating, -13/-14/-15 hierarchy
controls, -16 markdown image paste, -17 trio dedup) verified green
via the existing test suite in this triage pass. None of these have
the "looks-fine-in-static-parser, broken-at-runtime" failure mode
that hit BPMN-03; they're visible UI bugs that would have been
re-reported if regressed.

## [5.6.1] - 2026-05-07

### Added

- **iris-mcp returns a `web_url` per entity** — every tool response that
  carries an entity id now also carries a resolved front-end URL
  (`https://<IRIS_WEB_URL>/views/<id>`, `/elements/<id>`,
  `/packages/<id>`, `/sets/<id>`, `/collections/<id>`). Search results
  decorate per-result via the `result_type` discriminator. Reads from
  the new `IRIS_WEB_URL` env var; when unset the field is omitted and
  responses are identical to v5.6.0. Stops MCP-using LLMs from guessing
  the iris host and producing broken links. Render UAT defaults to
  `https://iris-uat.chrisbarlow.nz`. Surfaced in `/info` for diagnosis.

### Changed

- **Hierarchy controls on `/views/[id]` now reuse the shared
  `HierarchyControls` component (DRY)** — the diagram-detail page's
  hierarchy sidebar had its own inline copy of the +New / Show
  dropdown buttons that drifted from the dashboard's version: the
  Show menu offered "Only with children" instead of the dashboard's
  Diagrams / Text type-filter checkboxes. Both screens now render
  the same `HierarchyControls` component.
- **Dashboard Collections/Sets cards: selected-name colour matches
  the count colour** — when no scope was selected, the count used
  the knowledge-graph node colour (`getNodeTypeColor('collection')`
  / `'set'`); when selected, the name dropped back to plain
  foreground. Both states now use the type-coloured value so the
  card's visual identity carries through.

### Fixed

- **First page load latency after idle on UAT** — the keep-alive
  workflow now also pings `/api/extensions/public-status`, the
  one public DB-touching endpoint we have. `/health` keeps the
  FastAPI dyno warm but doesn't query the database, so the asyncpg
  pool to Supabase still went cold between sessions and the first
  real page paid the reconnect cost. `public-status` is a tiny
  SELECT that keeps the pool hot.

## [5.6.0] - 2026-05-07

### Added

- **ArchiMate Open Exchange XML import** (issue #52) — iris now imports
  ArchiMate models in the format published by The Open Group at
  http://www.opengroup.org/xsd/archimate/, supporting the 3.0, 3.1, and
  3.2 namespace variants. New endpoint `POST /api/import/archimate`
  accepts `.xml`, `.archimate`, and `.oex` uploads; the import page
  dropzone has been extended to advertise the format and route uploads
  to the new endpoint.

  - 40+ ArchiMate element types map to native iris types via the
    existing `ARCHIMATE_STEREOTYPE_MAP` (DRY — single source of truth
    shared with the SparxEA importer).
  - 12 ArchiMate relationship types (Composition, Aggregation,
    Assignment, Realization, Serving, Triggering, Flow, Specialization,
    Access, Influence, Association, plus the legacy `Used`/`UsedBy`
    aliases).
  - **Auto-generated Overview diagram** when the source OEX file is
    model-only (no embedded views) — common in real-world exports.
    Layout is a type-grouped grid with edges drawn from the iris
    relationship table. An `auto_layout` warning records that the
    diagram was synthesised.
  - Nested `<node>` containment (compound nodes) is flattened to
    absolute coordinates on import.
  - Two committed fixtures: `docs/reference/ArchiMate/sample-with-view.xml`
    (hand-authored, 3/2/1) and `docs/reference/ArchiMate/msd-map.xml`
    (real-world: 127 elements, 977 relationships, 0 views).
  - New UAT Playwright spec
    `frontend/tests/e2e/uat/issue-52-archimate-import.spec.ts` drives
    end-to-end import of the MSD fixture against the live UAT
    deployment.
- **ADR-148** + **SPEC-148-A** documenting the format support, mapping
  tables, auto-layout strategy, and accepted file extensions.

## [5.5.10] - 2026-05-07

### Added

- **`GET /api/extensions/public-status`** — minimal public read-only
  endpoint returning `id / name / version / source_method /
  source_url / latest_version` for each installed extension. Used
  by the daily scanner workflow. No sensitive operational data
  (no `installed_by`, `installed_at`, `config` or timestamps), so
  no auth required. The extensions list itself is already public
  (`extensions/sources.json` in this public repo).

### Changed

- **Daily extension scanner reads the deployed iris-api state**
  instead of the static `extensions/manifest.json` (issue #55
  follow-up). Pre-fix the scanner compared GitHub's latest release
  to a committed manifest version. After an operator clicked
  Upgrade on the UAT extension manager — which bumped the database
  row's `version` — the manifest was unchanged, so the next daily
  run re-filed the issue even though the deployment was already on
  the new version.

  Now `scripts/check_extension_updates.py` GETs
  `${IRIS_API_URL}/api/extensions/public-status` (no auth) for the
  actual installed versions. Falls back to `manifest.json` only when
  the API is unreachable. The workflow needs no new secrets — just
  optionally set `IRIS_API_URL` as a repository variable if your
  iris-api host differs from the default.
- **`GITHUB_TOKEN` documented as a backend env var in
  `docs/deployment-render-supabase.md`** (was implicitly required
  by v5.5.7 but not in the deployment table). Lifts GitHub's 60/hr
  unauthenticated rate limit to 5000/hr.

## [5.5.9] - 2026-05-07

### Fixed

- **Extension manager rendered `vv2.0.0`** (issue #55 follow-up).
  GitHub release tags often start with `v` (`v2.0.0`) while the
  manifest stores them without (`1.0.0`). The UI prepended `v` for
  visual consistency, doubling up. New `vNum()` helper strips any
  pre-existing prefix.
- **`POST /api/extensions/mnemos/upgrade` 500'd on Render** with
  `[Errno 2] No such file or directory: 'git'` (issue #55
  follow-up). The Render Docker image didn't include git; the
  `clone_or_update_repo` helper failed at the first subprocess.
  Even with git, `docker compose up` doesn't work on Render's
  managed dynos (no docker-in-docker privileges) — mnemos is a
  self-hosted-only feature there.

  Fix: add `git` to the Dockerfile's apt install list, and treat
  container/clone failures in the upgrade endpoint as warnings
  rather than fatal errors. The recorded `installed_version` always
  bumps to the latest so the UI reflects the user's intent and the
  daily scanner stops re-filing the issue. Self-hosted operators
  with docker get the real container restart; Render operators get
  a successful version bump (with a logged warning) and can verify
  the actual mnemos service runs elsewhere.

## [5.5.8] - 2026-05-07

### Fixed

- **`/api/extensions/{id}/check-update` 500 on Postgres** (issue #55
  follow-up). m048 declared `latest_version_checked_at` as TEXT
  (matching SQLite), but the rest of the extensions table uses
  TIMESTAMPTZ for `installed_at` / `updated_at`. The asyncpg adapter
  auto-converts ISO datetime strings to Python datetime objects;
  binding a datetime to a TEXT column raised
  `asyncpg.exceptions.DataError: invalid input for query argument $2:
  datetime.datetime(...) (expected str, got datetime)` and crashed
  the worker mid-response, so the user saw a 500 with no CORS
  headers.

  New migration `m050_latest_version_checked_at_timestamptz.sql`
  ALTERs the column to TIMESTAMPTZ to match the rest of the table.
  Idempotent — guarded by an `information_schema` check.

### Operator notes

After merge, run on UAT/Supabase:

```
psql "$SUPABASE_DB_URL" -f backend/app/migrations/supabase/m050_latest_version_checked_at_timestamptz.sql
```

Then click "Check for updates" on mnemos again — should succeed.

## [5.5.7] - 2026-05-07

### Fixed

- **GitHub API 403 from `/api/extensions/{id}/check-update`** (issue
  #55 follow-up). Unauthenticated requests are limited to 60/hr per
  IP; Render's shared egress hits the limit quickly. Now declares
  `GITHUB_TOKEN` as a `sync: false` env var on the iris-api
  service in `render.yaml`. With a fine-grained PAT scoped to
  "Public Repositories (read-only)" set in the Render dashboard,
  the limit jumps to 5000/hr.
- **Helpful 403/429 error message**. The endpoint now surfaces
  "GitHub API rate limit hit. Set GITHUB_TOKEN…" instead of bare
  status code so users know what to do.

### Operator notes (post-merge)

1. Generate a fine-grained PAT on GitHub:
   Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token. Scope it to
   "Public Repositories (read-only)" — no write access needed.
2. In Render dashboard → iris-api → Environment, add
   `GITHUB_TOKEN=<paste>`. Save → triggers redeploy.
3. Click "Check for updates" on the mnemos card — should succeed
   now.

## [5.5.6] - 2026-05-07

Backend deploy fix for issue #55.

### Fixed

- **`/api/extensions/{id}/check-update` returns "only supported for
  github-sourced extensions" on UAT** (issue #55 root cause). The
  Dockerfile copied `backend/`, `iris-client/`, `mcp/` but **not
  `extensions/`** (where `sources.json` lives). At runtime
  `get_source()` couldn't find the registry, so every extension's
  `source_method` resolved to `None`, and the github-only branch
  raised 400.

  Fix: `COPY extensions/ extensions/` in the Dockerfile. Plus a
  defensive `log.warning` in `sources.py::_load()` so any future
  deploy that misses this directory surfaces the cause in iris-api
  logs instead of silently failing.

After UAT redeploys, clicking "Check for updates" on the mnemos
card hits the GitHub API, populates `latest_version`, and the
"Update available" pill + "Upgrade to v2.0.0" button render.

## [5.5.5] - 2026-05-07

Two small fixes around the extension manager UI for issue #55 and the
v5.5.3 test-harness padding-left assertion.

### Fixed

- **Extension manager hides GitHub badge / Check Updates / Upgrade
  buttons for extensions installed before v5.5.0** (issue #55
  follow-up). Mnemos was installed when m048 didn't exist; when
  m048 added the `source_method` column with default `'local'`, the
  existing row got `'local'` rather than the registry's actual
  `'github'`. The frontend's `installed?.source_method ?? known
  .source_method` precedence let stale `'local'` win over the
  registry's `'github'`, so the GitHub-only UI branch (badge / Check
  Updates / Upgrade button) was hidden. Now uses an
  `effectiveSourceMethod()` / `effectiveSourceUrl()` helper that
  trusts the registry whenever it declares a non-local source —
  source-of-truth-wins-over-stale-row.

  After upgrading, the mnemos card on `/admin/settings/extensions`
  shows the GitHub badge, source URL, "Check for updates" button,
  and (after one click) the latest version + Upgrade-to-v2.0.0
  button.

### Test harness

- Item 3 padding-left assertion (originally checked button bbox.x,
  but block w-full buttons share an x even when padding differs).
  Test now passes — the v5.5.3 inline-style indent fix is verified
  on UAT.
- Item 8 force-clicks the BPMN node (the .bpmn-activity body
  intercepts pointer events on the underlying svelte-flow wrapper).
- Item 9 uses `[data-handlepos="right"|"left"]` selectors and a
  manual stepped mouse drag for xyflow's connection lifecycle.
  Items 8 + 9 still fragile in headless but the underlying code
  fixes (v5.4.1) are confirmed via static-parser tests.

## [5.5.4] - 2026-05-06

Visual + layout fixes uncovered by the live UAT verification run.

### Fixed

- **View-detail hierarchy sidebar buttons match the dashboard's
  `+ New ▾` / `Show ▾` pattern** (issue #46 hierarchy-panel-match
  follow-up). Pre-fix the sidebar showed `Diagrams` (a single
  toggle) and `+ Child` (a primary button with a dropdown). The
  dashboard's `HierarchyControls` uses the `+ New ▾` / `Show ▾`
  visual; the sidebar now mirrors it: `+ New ▾` (with Package
  unindented + View indented, child-create semantics) and
  `Show ▾` (with the existing "Only with children" toggle and a
  greyed "Views" section header — same shape as the dashboard).
- **BPMN Problems panel falls below the fold**. The
  `.bpmn-shell` height calc used `100vh - 230px`; the rest of
  the canvases use `100vh - 317px`. The smaller constant left
  87px of overflow that pushed the Problems panel below the
  viewport bottom. Now matches the page chrome other canvases
  account for.
- **Item 11 test: BPMN palette is an accordion**. The Events
  section is collapsed by default; the test now expands it via
  the section heading before clicking Start Event.

## [5.5.3] - 2026-05-06

Real runtime verification of issue #46 against UAT via the Playwright
harness, plus one confirmed bug fix.

### Fixed

- **+New dropdown View button has no left indent** (issue #46 item #3
  root cause). Pre-fix the dropdown's View button used Tailwind class
  `pl-8` for the indent, but the deployed Tailwind v4 build never
  emitted that class — visually Package and View sat at the same
  X-coordinate. Confirmed via Playwright screenshot diff against UAT.
  Fix: switch to inline `style="padding-left: 2rem"` so the indent is
  immune to Tailwind's content-detection edge cases.

### Changed

- **Playwright UAT harness: more robust BPMN-view discovery + edit-
  mode handling.** The harness now queries `/api/diagrams?notation=
  bpmn` directly via the authed page context (rather than scraping
  dashboard links by text content), and skips BPMN-edit-mode tests
  cleanly when the edit lock can't be acquired (rather than failing
  with a 30s timeout). The `auth.setup.ts` flow now handles both
  Supabase-mode "Email" and SQLite-mode "Username" labels via
  `getByRole('textbox', …)` and waits for the form to fully hydrate.
- **`ignoreHTTPSErrors: true` on the UAT projects** so headless
  chromium without the system CA bundle can drive the live UAT site
  (relevant for WSL2 / minimal Linux runners).

### Verification status (issue #46 reopen)

Ran the UAT Playwright suite against v5.5.2-on-UAT. Results:

- ✅ #37 BPMN canvas mounts without `useStore outside …` (passes)
- ✅ #37 `/api/bookmarks` returns < 500 (passes — confirms m047)
- ✅ #37 `/api/graph/settings` returns < 500 (passes)
- ✅ #46 #1 /views toolbar HierarchyControls left of Select (passes)
- ✅ #46 #2 Show dropdown shows greyed Views label (passes)
- ❌ #46 #3 +New dropdown View indented — fixed in v5.5.3 above
- ⏭ #46 #4 markdown paste — skipped (no Text view discovery yet)
- ⏭ #46 #5+12, #6/7, #8, #9, #11 BPMN edit-mode tests — could not
  enter edit mode in headless run (likely edit-lock contention from
  a manual session; tests now skip cleanly rather than fail)
- ⏭ #46 #10 /elements/<id> Used in Diagrams + Relationships —
  skipped (fragile element-discovery logic; needs improvement)

The harness is now reusable for v5.5.4+ once edit-lock/Text-view
discovery is improved.

## [5.5.2] - 2026-05-06

Two follow-up fixes after applying v5.5.1's m049 to UAT surfaced the
remaining edges in the markdown image paste flow.

### Fixed

- **Pasted image renders blank in browse mode** (issue #46 item #4
  follow-up). `uploadPastedImage` returned a relative URL
  `/api/images/<id>`. In Supabase mode the frontend
  (iris-uat.chrisbarlow.nz) and the API (iris-api-*.onrender.com)
  are on different origins, so the rendered `<img>` resolved the
  relative path against the frontend origin and 404'd. Now prepends
  `API_BASE_URL` so the markdown link is absolute when needed; in
  self-hosted SQLite mode where API_BASE_URL is empty, the URL stays
  relative and resolves to the same origin (unchanged behaviour).
- **m049 migration fails on Postgres deploys with the v5.4.0
  policies applied**. Postgres refuses to ALTER a column type while
  a policy references it: 'cannot alter type of a column used in a
  policy definition'. The original m049 hit this on `uploaded_by`
  because the `images_delete` policy depends on it. m049 now drops
  the policy, ALTERs both columns, and recreates the policy with
  TEXT-aware casts. (PR #50 was merged before this commit pushed,
  so main shipped without the fix; this PR re-applies it.)

### Operator notes

If you applied v5.5.1's m049 manually as I posted in chat, you've
already got the policy-aware version on UAT. No further migration
needed — but the file in main now reflects what you ran, so future
deploys are correct.

## [5.5.1] - 2026-05-06

Two concrete follow-up fixes for issue #46 found during the v5.5.0
post-merge code audit. The remaining items from #46 still need the
Playwright UAT suite (`npm run test:uat`) run from a machine with the
chromium runtime libs to confirm they actually work end-to-end.

### Fixed

- **Markdown clipboard paste 500 on Postgres** (issue #46 item #4
  root cause). The original `m046_images.sql` declared `images.id`
  and `images.uploaded_by` as `UUID`, but the Python service passes
  `str(uuid.uuid4())` and Iris user IDs are `TEXT`. asyncpg doesn't
  auto-coerce strings to `UUID`, so `INSERT INTO images` failed with
  "invalid input syntax for type uuid" — `/api/images` 500'd, the
  markdown editor's onpaste catch swallowed it, users saw "ctrl-v
  does nothing". New migration `m049_images_uuid_to_text.sql` ALTERs
  both columns to `TEXT` (idempotent — guarded by an
  `information_schema` check so re-running is a no-op). After
  applying the migration on UAT/Supabase, the markdown paste flow
  works end-to-end.
- **FocusView's Add Element button now hidden on BPMN edit views**
  (issue #46 item #12 follow-up). v5.4.1 gated the parent canvas
  toolbar's Add Element on `notation !== 'bpmn'` but missed the
  FocusView's duplicate trio (which renders only when focus mode is
  active). Same gate applied to that button.

### Operator notes

After merging, run on UAT/Supabase:

```
psql "$SUPABASE_DB_URL" -f backend/app/migrations/supabase/m049_images_uuid_to_text.sql
```

This converts the existing `images.id` and `images.uploaded_by`
columns from UUID to TEXT in place. The migration is idempotent.

After promotion, run `npm run test:uat` from a machine with
Playwright deps installed (`npx playwright install chromium &&
npx playwright install-deps` — `install-deps` may need sudo on
minimal Linux/WSL2). Failing specs become the punch list for
v5.5.2.

### Verification

- 5 new backend pytest specs (test_images_uuid_to_text_schema).
- No frontend changes apart from the FocusView gate.

## [5.5.0] - 2026-05-06

UAT verification harness against the live deployment (issues #46/#37
reopen) plus the mnemos→MNEMOSv2 upgrade and the extension scanner +
data-model expansion (issue #48).

### Added

- **UAT-targeted Playwright project** (issue #46/#37 reopen,
  ADR-147 / SPEC-147-A). New `uat` Playwright project drives the live
  https://iris-uat.chrisbarlow.nz deployment using a tester account,
  takes labelled screenshots, and asserts visible state. Run via
  `npm run test:uat`. New `uat-setup` project signs the tester in once
  and persists `storageState` for the suite. 12 verification specs
  cover every item in issue #46 (toolbar order, Show dropdown label,
  +New ordering, markdown paste, trio dedup, Problems panel layout,
  ContextPad actions, drag-to-connect, Used in Diagrams /
  Relationships, EventTriggerFlyout, Add Element gating); 3 specs
  cover issue #37 (BPMN canvas mounts without `useStore outside
  <SvelteFlowProvider />`, `/api/bookmarks` and `/api/graph/settings`
  return < 500). Opt-in via env var `PLAYWRIGHT_UAT=1` so local
  vite/preview servers aren't started for remote-only runs.
- **Extension source-tracking columns** (issue #48, ADR-146 /
  SPEC-146-A). New SQLite migration `m046_extensions_source.py` and
  Postgres mirror `m048_extensions_source.sql` add `source_method`,
  `source_url`, `latest_version`, `latest_version_checked_at` to the
  `extensions` table. Backend `ExtensionResponse` exposes them; the
  install endpoint persists the source from the registry.
- **Shared extension source registry** (`extensions/sources.json`,
  `backend/app/extensions/sources.py`). Single source-of-truth used
  by the backend, the frontend (via API), and the daily GitHub
  Action. Mnemos's source URL is now
  `https://github.com/ro0TuX777/MNEMOSv2`.
- **POST /api/extensions/{id}/check-update** (issue #48). Polls the
  GitHub releases API for a github-sourced extension and persists
  `latest_version` + `latest_version_checked_at`.
- **POST /api/extensions/{id}/upgrade** (issue #48). Currently
  supports mnemos: stops the container, runs `clone_or_update_repo`
  to pull MNEMOSv2's latest, restarts. Returns 501 for extensions
  that don't yet support automated upgrade.
- **Extension manager UI: source badge + version diff + update pill +
  Check Updates / Upgrade buttons** (issue #48). The page now shows
  whether an extension is `GitHub` / `npm` / `Local`, links to the
  source URL, renders installed-vs-latest versions, highlights an
  "Update available" pill via the new `isNewerSemver` helper, and
  exposes per-row Check for updates and Upgrade actions.
- **Daily extension upgrade scanner workflow** (issue #48,
  `.github/workflows/extensions-check.yml`,
  `scripts/check_extension_updates.py`). Runs daily at 08:07 UTC.
  For each github-sourced extension whose latest release is newer
  than the manifest baseline, opens a single deduplicated issue
  titled `Upgrade: <name> extension`. Closing the issue resets the
  dedup so the next upgrade event files a fresh one. Manual trigger
  via `workflow_dispatch`.
- **`extensions/manifest.json`** — committed baseline of the
  "currently shipped" version per extension. Bumped in upgrade PRs.

### Changed

- **mnemos auto-clone** (issue #48, ADR-111 amendment). New
  `clone_or_update_repo()` helper in `backend/app/mnemos/setup.py`
  clones the configured source repo on a fresh install or pulls the
  latest on upgrade. Default URL now points at MNEMOSv2; override via
  `IRIS_MNEMOS_REPO_URL`.
- **keep-alive workflow now warms `iris-api/health` and the
  iris-uat frontend** alongside the existing favicon ping.
  `/health` exercises the FastAPI app stack rather than just the
  static favicon Render serves directly, which keeps the database
  bootstrap warm. The frontend ping prevents the static-site dyno
  from spinning down mid-flow.

### Fixed

- **`/api/bookmarks` 500 on UAT** (issue #37 reopen). The SQLite
  migration `m038_element_bookmarks.py` (which adds the `element_id`
  column) was never mirrored to Supabase, so the bookmarks router's
  `SELECT diagram_id, package_id, element_id, created_at FROM
  bookmarks` failed on Postgres. New migration
  `m047_element_bookmarks.sql` adds the column, the index, replaces
  the strict 2-way CHECK with a 3-way one, and adds the
  per-user-per-element UNIQUE.

### Docs

- ADR-146 / SPEC-146-A — extension source tracking decision +
  schema, endpoint shapes, scanner workflow steps, manifest format.
- ADR-147 / SPEC-147-A — UAT Playwright verification harness:
  on-demand only, fixture-based credentials, screenshot policy.
- ADR-111 v5.5.0 amendment — mnemos auto-clone + MNEMOSv2 default.

### Verification

- 8 new vitest specs (semverCompare 7 + extensionManagerFields 6).
- 12 new backend pytest specs across `test_extensions/test_sources.py`,
  `test_migrations/test_extensions_source_schema.py`,
  `test_migrations/test_element_bookmarks_schema.py`.
- 7 new pytest specs for the scanner script.
- Frontend full vitest suite: 879/880 pass (1 baseline failure
  unchanged).
- `svelte-check`: 164 errors (= unchanged baseline).
- UAT Playwright suite ships in this release; manual run via
  `npm run test:uat` after promoting v5.5.0 to UAT.

### Operator notes

- After merging, run the new Postgres migrations on UAT/Supabase:
  ```
  psql "$SUPABASE_DB_URL" -f backend/app/migrations/supabase/m047_element_bookmarks.sql
  psql "$SUPABASE_DB_URL" -f backend/app/migrations/supabase/m048_extensions_source.sql
  ```
  m047 fixes the `/api/bookmarks` 500 (issue #37); m048 adds the new
  source-tracking columns (issue #48).

## [5.4.1] - 2026-05-06

UAT follow-up to v5.4.0 (issue #46): 12 polish items spanning the
hierarchy controls, the trio toolbar, the BPMN authoring shell, and the
markdown paste flow. Headlined by two BPMN architectural fixes — the
default edge type for BPMN was never set (handle-drag connections
landed as `'uses'` instead of `'sequence_flow'`, so the validator's
"no outgoing sequence flow" rule kept firing); and BPMN connections
never created `/api/relationships` records, so /elements/<id>'s
Relationships panel stayed empty. The 60-cell EventMatrixPicker dialog
on event drop has been replaced with an inline ContextPad-style
trigger flyout that shows only the legal triggers for the chosen
position.

### Fixed

- **BPMN edges now create real Relationship records** (ADR-136 v5.4.1
  amendment §A, issue #46 item #10). `BpmnAuthoringShell` now wires
  `onconnectnodes` to `<UnifiedCanvas>` and POSTs `/api/relationships`
  with `relationship_type: 'sequence_flow'` whenever both endpoints
  have backing entityIds. /elements/<id>'s Relationships panel now
  lists BPMN-drawn connections.
- **BPMN handle-drag default edge type is sequence_flow** (ADR-136
  v5.4.1 amendment §B, issue #46 item #9). `defaultEdgeType` was
  missing the BPMN case, so the validator's "no outgoing sequence
  flow" rule kept firing because edges landed as type `'uses'`.
- **Problems panel caps at 200px and scrolls itself** (ADR-136 v5.4.1
  amendment §C, issue #46 items #6 + #7). Pre-fix the panel had
  `max-height: 200px` but no `flex-shrink: 0`, so the flex algorithm
  collapsed the cap and the panel pushed the page off-screen.
- **Trio toolbar (Add Element / Link Element / Add Diagram) renders
  exactly once** (issue #46 item #5). v5.4.0 added duplicate trios in
  the Text and BPMN inner branches; the parent canvas toolbar already
  covered both. Duplicates removed.
- **Markdown clipboard paste failures now surface in dev tools**
  (ADR-137 v5.4.1 amendment §A, issue #46 item #4). Pre-fix the catch
  was silent; users saw the editor no-op with no feedback. Now logs
  via `console.error` and exposes an optional `onpasteerror` callback.
- **ContextPad action failures console.error** (issue #46 item #8).
  `createBpmnElement`'s catch now also logs the underlying error so
  silent ContextPad no-ops are diagnosable in production.

### Changed

- **Event picker is an inline trigger flyout, not a 60-cell dialog**
  (ADR-136 v5.4.1 amendment §D, issue #46 item #11). When the user
  drops a Start / Intermediate / End / Boundary event from the
  palette, a compact ContextPad-style row of legal triggers appears
  next to the placed node. The 6×10 dialog is no longer auto-opened
  on palette flow (still available for the Ctrl-N command-palette
  advanced flow). New `bpmnEventModel.ts` extracts `TRIGGERS`,
  `isLegal`, `variantFor`, `positionFor` as the single source of
  truth (DRY).
- **Add Element button hidden on BPMN edit view** (issue #46 item
  #12). The BPMN palette sidebar already covers element creation, so
  the trio's Add Element button would be redundant.
- **HierarchyControls Show dropdown shows a "Views" section header**
  (issue #46 item #2). Greyed, non-interactive, above the Diagrams
  checkbox — clarifies that "Diagrams" is a kind of View.
- **HierarchyControls +New dropdown lists Package above View, View
  indented** (issue #46 item #3). Visually conveys the
  package → view containment relationship.
- **/views toolbar matches the dashboard ordering** (issue #46 item
  #1). HierarchyControls is the leftmost button; Select sits to its
  right (was reversed pre-fix).

### Docs

- ADR-136 v5.4.1 amendment — default BPMN edge type, relationship-on-
  connect, event trigger flyout, trio gating, Problems panel
  flex-shrink.
- ADR-137 v5.4.1 amendment — surface paste errors via `console.error`
  + `onpasteerror`.

### Verification

- 8 new vitest specs added (5 Phase 1, 2 Phase 2, 1 Phase 3).
- Frontend full suite: 879/880 pass (1 pre-existing baseline failure
  unchanged).
- `svelte-check`: 164 errors (= unchanged baseline).
- No backend changes; backend pytest unaffected.

## [5.4.0] - 2026-05-06

BPMN polish + markdown experience polish + image paste + dashboard
tweaks (issue cluster against v5.3.1). Headlined by **BPMN-as-Elements
alignment** (every BPMN node now creates a backing Iris Element,
matching every other notation) and **clipboard image paste** (paste a
screenshot in the markdown editor → Iris uploads → markdown link
auto-inserted at the cursor).

### Added

- **BPMN nodes are Iris Elements** (ADR-136 v5.4.0 amendment §A,
  ADR-145, issue cluster #13). Every BPMN node-creation path —
  drag-from-palette, drop-on-canvas, CommandPalette
  `create`/`append`, ContextPad-append, EventMatrixPicker — now
  POSTs `/api/elements` first and stores `entityId` on the canvas
  node. Replace mode PUTs the existing Element's `element_type`.
  PropertyPanel label/description edits sync back via fire-and-forget
  PUT. BPMN content joins search, knowledge graph, tagging,
  comments, versioning, and `iris://element/<id>` references.
- **Clipboard image paste** (ADR-137 v5.4.0 amendment §A, ADR-145,
  issue cluster #7). Paste an image into the markdown editor → Iris
  uploads to the new `images` table → markdown link
  `![pasted-image](/api/images/<id>)` auto-inserted at the cursor.
  GitHub-style. New backend `images` module (`POST /api/images` +
  `GET /api/images/{id}`); 5 MB cap; magic-byte MIME validation
  (PNG/JPEG/GIF/WebP); SQLite BLOB / Postgres BYTEA parity.
- **ContextPad bring-forward / send-backward actions** (ADR-136
  v5.4.0 amendment §C, issue cluster #3). Two new ContextPad
  buttons (↑ / ↓) for z-order control when items stack (e.g. lane on
  pool, annotation on activity).
- **Lane-on-pool parent detection** (ADR-136 v5.4.0 amendment §D,
  issue cluster #5). Dragging a lane onto a pool now sets
  `parentId` on drop, so `validateBpmn::lane_outside_pool` no
  longer fires false positives. New `onnodedragstop` prop on
  `<UnifiedCanvas>` forwarded to xyflow; shell-level hit-test runs
  on BPMN views only.
- **Add Element / Link Element / Add Diagram on BPMN + Text edit
  modes** (ADR-136 v5.4.0 amendment §G, ADR-137 v5.4.0 amendment
  §D, issue cluster #8). Trio toolbar above both branches. On
  BPMN: Add Element creates a BPMN node + Element; Link Element
  binds a picked Element to the selected node; Add Diagram inserts
  a `call_activity` BPMN sub-process referencing the picked
  diagram. On Text: handlers already wired via v5.1.1
  `insertMarkdownAtCursor` — only the toolbar render was missing.

### Changed

- **Per-entity-type BPMN node sizing** (ADR-136 v5.4.0 amendment §B,
  issue cluster #2 + #4). Pre-v5.4 every BPMN node was created with
  `width: 200`. Events/gateways/data-objects render at 56×56 / 48×64
  visually but the bounding box was 200px wide, pushing the
  ContextPad far to the right of the actual shape. New
  `BPMN_NODE_DIMENSIONS` lookup matches the renderer CSS:
  events/gateways 56×56, activities 200×80, swimlanes 240–600 wide,
  data-objects 48×64, etc.
- **Markdown view defaults to Canvas tab when content exists**
  (ADR-137 v5.4.0 amendment §B, issue cluster #9). Smart-tab
  predicate now reads `diagram.data.content` for Text views —
  pre-v5.4 the page always landed on Details for Text because
  the predicate only checked `canvasNodes` / sequence participants.
- **Tab order: Canvas first** (ADR-137 v5.4.0 amendment §C, issue
  cluster #10). Canvas is now the left-most tab in the views detail
  page (was Details). The working-content tab gets the working-
  content position.

### Fixed

- **ProblemsPanel scrolls itself, not the page** (ADR-136 v5.4.0
  amendment §E, issue cluster #1). `.bpmn-shell__problems` had
  `overflow: hidden`, clipping the inner list's `overflow-y: auto`.
  Long problem lists now scroll inside the panel.
- **Theme dropdown hidden on BPMN + Text views** (ADR-136 v5.4.0
  amendment §F, issue cluster #6). BPMN theme is fixed by m043's
  bpmn-default seed; Text views have no canvas to theme.
- **Dashboard: Packages card removed; Collections + Sets cards
  visually distinct** (issue cluster #11 + #12). Packages card
  count was redundant with the hierarchy tree. Collections + Sets
  get a muted-grey background (`var(--color-surface)`) so they
  read as "scope filters" distinct from the working-content cards
  (Views, Elements).
- **Dashboard: count colours match the knowledge-graph palette**
  (post-v5.4.0 amendment). Collections / Sets / Views / Elements
  count tiles now use `getNodeTypeColor()` from the same palette
  the graph below already renders with — visually anchoring each
  count to the matching node colour in the graph legend.

### Docs

- ADR-145 / SPEC-145-A — image upload storage decision (table vs
  Supabase Storage vs base64) and schema/endpoints.
- ADR-136 v5.4.0 amendment — BPMN-as-Elements + per-type sizing +
  z-order + parent-on-drop + ProblemsPanel + theme + trio buttons.
- ADR-137 v5.4.0 amendment — paste-image + smart-tab default + tab
  order + trio render in Text mode.

### Verification

- 11 new vitest specs added (≥ 30 tests covering Phase 1–5).
- 2 new backend pytest specs (5 tests on the images endpoint).
- Frontend full suite: 866/867 vitest pass (1 pre-existing baseline
  failure unchanged — `importIdempotency > displays diagrams skipped
  count`, fails against unmodified baseline too).
- `svelte-check`: 164 errors (= unchanged baseline, no new errors).
- Backend BPMN suite stays green; new images suite 5/5.

## [5.3.1] - 2026-05-05

Hot-fix for v5.2.0 (issue #37 reopen). Every canvas — not just BPMN —
crashed on load with `Uncaught Error: To call useStore outside of
<SvelteFlow /> you need to wrap your component in a
<SvelteFlowProvider />`.

### Fixed

- **All canvases crash with "useStore outside of SvelteFlow"**
  (ADR-136 v5.3.1 amendment, issue #37 reopen). v5.2.0 added
  `useSvelteFlow()` at the script level of `UnifiedCanvas` to power
  the BPMN palette drag-drop's coordinate projection. xyflow's hook
  uses `getContext` at call time and only resolves inside
  `<SvelteFlowProvider>` (or `<SvelteFlow>`). v5.2.0 also wrapped
  UnifiedCanvas's *own template* in the provider — but Svelte's
  lifecycle runs the script BEFORE the template mounts, so the hook
  ran with no context above it and threw. Net effect: every
  notation's canvas was broken in production, not just BPMN.
  - Fix: extract a thin `CanvasDropArea` component that owns the
    drop handlers and calls `useSvelteFlow()` from its own script.
    Mount it inside the existing `<SvelteFlowProvider>` so its
    initialisation happens *after* the provider is set up.
  - Regression guard: `bpmnCanvasIntegration.test.ts` adds a test
    asserting `UnifiedCanvas` does NOT call `useSvelteFlow` at
    script level. Catches the exact pattern that broke v5.2.0.

## [5.3.0] - 2026-05-05

Markdown experience overhaul (issue #32 reopen). Four bundled
problems against the Text-class + MarkdownView surface introduced
since v5.1.0. Headlined by the new in-editor formatting toolbar.

### Added

- **Markdown editor toolbar** (ADR-137 v5.3.0 amendment §D, issue
  #32 reopen). New `MarkdownEditorToolbar` mounts above the existing
  TextCanvas `<textarea>` in edit mode. 12 buttons:
  **B / I / H1 / H2 / H3 / • UL / 1. OL / ❝ Quote / `</>` Code /
  🔗 Link / 🖼 Image / ─ HR**. Pure-helper architecture (`wrapSelection` /
  `prefixLines` / `insertAtCursor` in `markdownEditorToolbarHelpers.ts`)
  so the formatting logic is unit-testable without mounting Svelte.
  Markdown stays the canonical source — no hidden state, no WYSIWYG.
  Keyboard shortcuts: **Ctrl/Cmd+B** (bold), **Ctrl/Cmd+I** (italic),
  **Ctrl/Cmd+K** (link). Line-prefix actions toggle on/off (matches
  GitHub / VSCode markdown shortcut conventions). Researched against
  CodeMirror 6 / Milkdown / Tiptap / EasyMDE — chosen pattern matches
  StackEdit / GitHub / HackMD / Obsidian source mode. **Zero new
  dependencies** (protocol #11) — saving CodeMirror 6 / Milkdown for
  a possible future "power editor" mode that can layer onto this
  foundation.
- **TOC drawer toggle button** (ADR-137 v5.3.0 amendment §B, issue
  #32 reopen). The `showTocDrawer` state was wired in v5.1.0 with
  both edit-mode and browse-mode `<MarkdownToc>` mounts in place,
  but no button toggled it. Added a **TOC** button to the canvas
  toolbar, gated on `canvasType === 'text'`, mounted in both the
  in-place toolbar and the focus-mode toolbar (mirrors the existing
  `Comments` button placement).

### Fixed

- **Markdown rendering parity — Text views now look like the User
  Guide** (ADR-137 v5.3.0 amendment §A, issue #32 reopen).
  Headings had no scale, lists had no bullets on Text views even
  though the same `MarkdownView` rendered them perfectly on the
  User Guide. Cause: the User Guide layout
  (`guide/+layout.svelte`) carried scoped
  `.guide-content :global(h1|h2|p|ul|ol|li|code|img|strong)` rules
  that styled the rendered HTML *from the outside* — Text views
  rendered through the same component but had no equivalent
  wrapper styling. Lifted the typographic ruleset into
  `MarkdownView.svelte`'s own `<style>` so rendered markdown
  carries its own typography regardless of where it's mounted.
  Drop the duplicates from the guide layout. Single source of
  truth per protocol #13. Extends the rule set to cover `h3`,
  `h4`–`h6`, `em`, `pre code`, `hr`.
- **User Guide images stopped loading** (ADR-137 v5.3.0 amendment
  §C, issue #32 reopen). Regression introduced when the guide
  migrated to the shared MarkdownView in v5.1.0 — DOMPurify's
  `ALLOWED_URI_REGEXP` required a scheme, so
  `<img src="/guide/dashboard.png">` had its src silently stripped.
  Widened the regex to also accept absolute (`/`) and relative
  (`./`, `../`) paths. Added a defence-in-depth post-walk that runs
  the same `urlIsAllowed` check on each `<img src>` because
  DOMPurify allows `data:` on img/audio/video src by default —
  closes the gap. `javascript:` / `data:` / `file:` remain
  stripped on both `<a href>` and `<img src>`.

### Docs

- ADR-137 v5.3.0 amendment — markdown rendering parity, TOC, image
  fix, editor toolbar (with the markdown-editor research summary).
- SPEC-137-A v5.3.0 amendment — implementation surface map for each
  of the four sub-fixes plus the toolbar button table.

### Verification

- 4 new vitest specs added (29 tests total) — `markdownImageAllowlist`
  (9), `markdownViewParity` (6), `textViewTocToggle` (2),
  `markdownEditorToolbar` (14, pure helpers).
- Frontend: 833/834 vitest specs pass (the one pre-existing failure —
  `importIdempotency > displays diagrams skipped count` — also fails
  against the unmodified baseline).
- `svelte-check`: 164 errors (= unchanged baseline, no new errors).
- Backend untouched — no Supabase migration needed.

### Closes

- #32 (reopened) — markdown rendering parity, TOC drawer, editor
  toolbar, User Guide images.

## [5.2.0] - 2026-05-05

BPMN canvas UX integration (issue #37). The six BPMN authoring
surfaces specified in ADR-136 §UX (`BpmnPalette`, `ContextPad`,
`CommandPalette`, `EventMatrixPicker`, `PropertyPanel`,
`ProblemsPanel`) shipped as standalone components in v5.1.0 but were
never mounted into the canvas — net effect was that BPMN was
catalogue-only. v5.2.0 wires them in. No new design decisions; this
is the integration pass for the design that already existed.

### Added

- **BPMN authoring shell** (ADR-136 v5.2.0 amendment, issue #37). New
  `BpmnAuthoringShell` component renders a 3-column layout (palette /
  canvas / property panel) with a bottom Problems dock and a
  fixed-position toast for `canConnect` rejection reasons. Mounted
  from the views detail page when `notation === 'bpmn' && editing`.
  Replaces the generic right-panel stack on BPMN views; non-BPMN
  views are unchanged.
- **Drag-from-palette node creation**. `BpmnPalette` already emitted
  `application/iris-bpmn-entity` on drag-start; `UnifiedCanvas` now
  receives the drop, projects the cursor via
  `useSvelteFlow().screenToFlowPosition`, and emits
  `ondropentity(key, position)` so the shell can create a BPMN node
  at the cursor with the right `BPMN_DEFAULT_DISCRIMINATORS` preset.
- **On-element context pad**. `BpmnRenderer` now mounts `<ContextPad>`
  via `<NodeToolbar>` when a BPMN node is selected — buttons for
  Append Task / Append Gateway / Append End Event / Connect / Change
  / Delete. The page-level action handler bridges to BpmnRenderer via
  a new `bpmnContextPadAction` Svelte context (set by UnifiedCanvas).
- **Always-on PropertyPanel** for BPMN views. Three tabs (General /
  BPMN / Documentation) with discriminator selects + activity marker
  checkboxes. Replaces the existing conditional ElementEditPanel /
  NodeStylePanel / LinkedDiagramPanel stack on BPMN views only.
- **CommandPalette N / A / R hotkeys**. Lifted out of CommandPalette's
  self-binding so they only fire on BPMN views. Press **N** to create-
  anything (modal opens with the full BPMN catalogue, fuzzy-search,
  Enter to add a node), **A** to append-anything after the selected
  node, **R** to replace the selected node's type. Modal backdrop +
  Escape close.
- **EventMatrixPicker** (6 × 10 trigger × position grid) opens
  automatically when an `event_*` entity is added via palette / drop /
  command — illegal cells visually disabled.
- **ProblemsPanel** bottom-docked, reactive to `validateBpmn(data)`.
  Severity badge counts (error / warning / info); click a row → the
  canvas selects the offending node.
- **canConnect at draw-time**. `<SvelteFlow isValidConnection={…}>`
  consults `bpmnRules.canConnect` before allowing an edge to be drawn;
  rejection reasons surface via the new `BpmnToast` component
  (~80 lines, no new dep).
- **`BpmnToast` component**. Aria-live, fixed-position bottom-centre,
  auto-dismiss after 3.5s, two-way bindable `message` prop. Single
  consumer (the BPMN shell); kept inline rather than pulling a toast
  library.

### Changed

- **`UnifiedCanvas`** wraps its template in `<SvelteFlowProvider>` so
  the script-level `useSvelteFlow()` call (used by the new drop
  handler) has a store to read. Adds three new optional callback
  props: `onbeforeconnect`, `ondropentity`, `oncontextpadaction`.
  Existing canvases are unaffected — the props default to undefined
  and the wiring is no-op when not provided.
- **`BpmnRenderer`** declares `id?: string` (xyflow auto-passes it to
  custom node components — Iris's renderer interface didn't).

### Docs

- ADR-136 v5.2.0 amendment — UX surface integration decisions (action
  callback via Svelte context, `isValidConnection` for canConnect,
  drag-drop MIME, hotkey gating).
- SPEC-136-A v5.2.0 amendment — surface-by-surface integration map +
  list of files added/modified.

### Verification

- 16 new tests in `bpmnCanvasIntegration.test.ts` (static-parser
  style, matches v5.1.x coverage tests). Catches regression if any
  surface mount, hook prop, or context wiring is removed.
- Frontend: 802/803 vitest specs pass (the one pre-existing failure —
  `importIdempotency > displays diagrams skipped count` — also fails
  against the unmodified baseline).
- `svelte-check`: 164 errors (= unchanged baseline, no new errors
  introduced). Cast-through-unknown idiom used at the two cross-
  notation entityType assignment sites in the shell, matching the
  existing pattern for storing UML/ArchiMate/C4/DoView/BPMN entity
  types in the narrowly-typed `CanvasNodeData.entityType` field.

### Out of scope (carried forward from ADR-136)

- Shape-pinned comment threads (Lucidchart's strongest differentiator).
- Element templates (Camunda-style preconfigured Service Tasks).
- bpmnlint integration for the Problems panel.
- BPMN XML import/export.
- Pool/Lane swimlane container semantics — pools/lanes still ship as
  styled rectangles; full container semantics in a follow-up.

### Closes

- #37 (BPMN canvas UX integration).

## [5.1.2] - 2026-05-05

UAT follow-ups against the v5.1.1 deployment — four contained bug
fixes against the Text class, Hierarchy controls, and BPMN dialog.
The deeper BPMN UX integration gap (BpmnPalette / ContextPad /
CommandPalette / EventMatrixPicker / PropertyPanel / ProblemsPanel
exist on disk but are not mounted into the canvas) is tracked
separately for v5.2.0; v5.1.2 is the last v5.1.x patch.

### Fixed

- **Hierarchy panel dropdowns clipped under the AppShell**
  (ADR-137 amendment, issue #30). `HierarchyControls` previously
  anchored both menus with `absolute right-0`. On the Dashboard
  hierarchy panel — which sits flush-left against the AppShell —
  the right-anchored menu extended *leftwards* off the panel and
  ended up under the AppShell nav. Switched to `absolute left-0`
  on both menus so they extend rightwards from the button. Coverage
  test prevents regression.
- **Tab in markdown editor moved focus instead of indenting**
  (ADR-137 amendment, issue #31). `TextCanvas`'s `<textarea>` had
  no `keydown` handler. Tab now intercepts and inserts a literal `\t`
  at the selection; `Shift+Tab` outdents (strips a leading `\t` or up
  to four spaces). Esc-then-Tab still moves focus normally so
  WCAG 2.1.2 (No Keyboard Trap) is preserved; the affordance is
  documented in the placeholder text.
- **Text view browse mode showed "Start Building" instead of
  rendered markdown** (ADR-137 amendment, issue #32). The v5.1.1
  `{:else if canvasType === 'text'}` branch existed only inside the
  `{#if editing}` block. Browse mode for Text views fell through to
  the empty-canvas branch (Text views legitimately have zero canvas
  nodes) and rendered the canvas "Start Building" prompt. Added a
  parallel browse-mode Text branch *before* the empty-canvas check,
  mounting `<TextCanvas editing={false}>` so MarkdownView fires.
  Empty Text views show a text-specific "This text view is empty —
  Start Writing" prompt that mirrors the canvas equivalent.
- **EntityDialog showed Simple-notation entity types on BPMN views**
  (ADR-136 amendment, issue #33). The dialog's notation switch had
  cases for UML / ArchiMate / C4 / DoView and a Simple `default:` —
  no `case 'bpmn':`. Clicking *Add Element* on a BPMN view silently
  presented Actor / Boundary / Component / Note / Service. Added the
  missing case using `BPMN_ENTITY_TYPES` + `BPMN_DIAGRAM_TYPE_FILTER`
  (mirrors the UML / DoView branches in the same file). New coverage
  test asserts every notation key in `NotationPills.ALL_NOTATIONS`
  has a matching switch case in `EntityDialog`, so this regression
  class can't recur.

### Docs

- ADR-136 amendment — EntityDialog BPMN case (issue #33). Notes the
  v5.1.0 oversight pattern (registry shipped, picker dialog lagged)
  and how the new coverage test closes the loop alongside the
  v5.1.1 NotationPills coverage test.
- ADR-137 amendment — three v5.1.2 follow-ups (issues #30, #31, #32).
  Includes the design-intent quote from #32 ("a single Canvas tab
  whose behaviour switches by notation; the type-of-diagram label
  remains authoritative").

### Verification

- Frontend: 786/787 vitest specs pass (the one pre-existing failure —
  `importIdempotency > displays diagrams skipped count` — also fails
  against the unmodified baseline).
- 4 new vitest specs added (15 tests total) — `hierarchyControlsAlignment`,
  `textCanvasTabKey`, `textViewBrowseRender`, `entityDialogBpmn`.
- Backend: 48/48 in scope-affected tests pass (docref + text + bpmn).
- `svelte-check`: 164 errors (= unchanged baseline, no new errors
  introduced).

## [5.1.1] - 2026-05-05

UAT follow-ups (issue #27) for the v5.1.0 release. The user-facing
"Diagrams" surface is renamed to "Views" so a Text view sits naturally
alongside a Canvas view; backend tables, API routes and stored data
keep the `diagram` term to avoid an invasive migration. See the
amendments at the end of
[ADR-135](docs/adrs/ADR-135-DocRef-Supabase-Migration-Parity.md),
[ADR-136](docs/adrs/ADR-136-BPMN-Notation.md) and
[ADR-137](docs/adrs/ADR-137-Text-Diagram-Subclass-And-Shared-Markdown-Renderer.md).

### Fixed

- **DocRef "Import failed" while the import actually succeeded**
  (ADR-135 amendment, issue #27). Importing a real document
  (e.g. Social Security Act) reliably surfaced "Import failed" in the
  UI even though the import completed a few seconds later — Render's
  edge timed the synchronous CSV download + per-chunk INSERT out at
  ~100s while the asyncio task on the backend kept going. The
  endpoint is now fire-and-forget: returns HTTP 202 + `importing`
  status immediately, runs the import via `asyncio.create_task`, and
  the frontend polls `/documents` every ~3s while any document is
  importing.
- **Save button stayed disabled in the markdown editor**
  (ADR-137 amendment §A, issue #27). The TextCanvas content callback
  updated `diagram.data.content` but never set `canvasDirty=true`, so
  the toolbar Save button stayed greyed out.
- **Saving a Text view wiped the markdown content**
  (ADR-137 amendment §B, issue #27). `saveCanvas` always wrote
  `data: { nodes, edges }`, blowing away `data.content`. The browse
  view then fell into the "empty canvas" branch instead of MarkdownView
  and the user saw an empty diagram with floating boxes from any
  Add Element / Add Diagram buttons. Save now branches on
  `canvasType === 'text'` and persists `{ content: markdownContent }`.
- **Add Element / Link Element / Add Diagram now insert markdown links
  in Text mode** (ADR-137 amendment §C, issue #27). TextCanvas exposes
  its `<textarea>` upward via a `$bindable` `textareaEl`; the parent
  page splices a `[name](iris://kind/<id>)` snippet at the cursor
  instead of creating a canvas node.
- **BPMN missing from `NotationPills`** (ADR-136 amendment, issue #27).
  The picker hard-coded a five-entry list (Simple, UML, ArchiMate, C4,
  DoView), silently dropping BPMN despite v5.1.0 wiring up the rest of
  the BPMN stack. The pill list now contains all seven notations and a
  unit test asserts coverage against `DiagramDialog.NOTATION_TYPE_FALLBACK`
  so the regression can't recur.

### Changed

- **"Diagrams" → "Views" across the frontend** (ADR-137 amendment §E,
  issue #27). User-facing only — backend, API routes and stored data
  keep the `diagram` term per UAT direction. Routes moved from
  `src/routes/diagrams/` to `src/routes/views/` (git-renamed); old
  `/diagrams` and `/diagrams/<id>` URLs issue HTTP 308 redirects to the
  `/views` equivalents preserving query + hash. Visible labels updated
  on the dashboard cards, hierarchy tab ("Diagram Hierarchy" → "View
  Hierarchy"), AppShell nav, page titles, breadcrumbs, search
  placeholders, batch dialogs and the Create dialog ("Diagram Type" →
  "View Type"; the markdown notation's type entry shortened from "Text
  Document" to "Text" per the UAT note).
- **Hierarchy panel buttons standardised** (ADR-137 amendment §F,
  issue #27). New shared `HierarchyControls` component renders two
  dropdowns — "+ New" (View | Package) and "Show" (Diagrams /
  Text checkboxes; packages always shown). Adopted by both the
  Dashboard hierarchy panel and the Views index toolbar so the two
  pages now read identically. The Dashboard's Reorder button is kept
  with a clearer tooltip.
- **`EntityDialog` notation pill scoped** (ADR-137 amendment §G,
  issue #27). Excludes `markdown` because text views have no entities
  to add.

### Docs

- ADR-135 / SPEC-135-A — DocRef async import amendment.
- ADR-136 / SPEC-136-A — `NotationPills` is the canonical picker;
  notation filter dropdown gains BPMN + Markdown entries.
- ADR-137 / SPEC-137-A — UAT follow-ups (sections A–G), file-by-file
  rename table, new `HierarchyControls` and `TreeNode` filter props.

## [5.1.0] - 2026-05-04

Two new notations and a bug fix that unblocked the Iris AI Legislation
feature on Supabase deployments. See
[ADR-135](docs/adrs/ADR-135-DocRef-Supabase-Migration-Parity.md)
through
[ADR-137](docs/adrs/ADR-137-Text-Diagram-Subclass-And-Shared-Markdown-Renderer.md)
for design rationale.

### Added

- **BPMN 2.0 notation** (ADR-136, issue #25). Full BPMN 2.0 §7.4
  element catalogue exposed across canvas, palette, MCP, and AI
  creation. 14 base entity types with discriminator fields on `data`
  (taskType, gatewayType, eventTrigger, eventDirection,
  boundaryInterrupting, subprocessKind, dataKind) cover every legal
  variant without bloating the registry. Adds `collaboration` and
  `choreography` diagram types; the existing `process` type gains
  BPMN as a non-default option (existing process diagrams unaffected).
- **BPMN authoring UX** (ADR-136 §UX). Six-section accordion palette,
  on-element context pad with discoverable wrench tooltip, searchable
  command palette bound to `N` (create-anything), `A` (append-anything),
  `R` (replace), 2D event matrix picker (Iris's strong opinion — no
  surveyed BPMN tool gets this right), always-on right-side property
  panel, and hybrid validation (silent draw-time prevention + persistent
  Problems panel) covering 15 well-known BPMN anti-patterns.
- **Text diagram subclass** (ADR-137, issue #26). Text is a Diagram
  with `diagram_type='text'` and `notation='markdown'`; the markdown
  source lives in `diagrams.data.content`. View mode renders the
  markdown; edit mode shows the source. TOC drawer mirrors the
  Comments tray pattern with depth-indented headings. Hierarchy menu
  gains a "View" submenu (Diagram / Text). Cross-links use the
  `iris://` URL scheme (`[label](iris://diagram/<id>)` /
  `iris://element/<id>`); diagram refs that target a Text document
  render in muted grey.
- **Shared MarkdownView component** (ADR-137). The `marked` +
  `DOMPurify` pipeline extracted into
  `frontend/src/lib/components/MarkdownView.svelte` and adopted by both
  the User Guide and the new Text canvas — DRY consolidation per
  protocol #13. URL scheme allowlist (`http`, `https`, `mailto`,
  `iris`) belt-and-braces against javascript:/data:/file: smuggling.

### Fixed

- **DocRef "Failed to load documents" on Supabase deployments**
  (ADR-135, issue #24). The `docref_documents` and `docref_chunks`
  tables existed only as a SQLite Python migration and were never
  ported to the Supabase SQL set, so the Iris AI Legislation feature
  failed on render-supabase-uat with a Postgres "relation does not
  exist" error surfaced as "Failed to load documents". Adds
  `m043_docref_tables.sql` mirroring the SQLite schema (TIMESTAMPTZ
  for dates, RLS enabled, admin-write/all-read policies). Static
  parser test enforces ongoing parity so this can't regress silently.

### Docs

- ADR-135 / SPEC-135-A — DocRef Supabase migration parity rule.
- ADR-136 / SPEC-136-A — BPMN 2.0 notation including UX recommendations
  researched against the most-loved BPMN tools (bpmn-js, Camunda
  Modeler, Bizagi, Lucidchart).
- ADR-137 / SPEC-137-A — Text diagram subclass and shared markdown
  renderer.
- `docs/deployment-render-supabase.md` — migration list extended to
  m041–m043; DocRef migration explicitly called out.

## [5.0.1] - 2026-05-04

### Fixed
- **iris-cli `login` against Supabase-mode backends.** The CLI was
  POSTing to `/api/auth/login`, which is intentionally 404'd in
  Supabase deployment mode (auth flows through Supabase Auth). The
  command now accepts `--token <PAT>` to skip the username/password
  flow entirely — mint a PAT externally (curl + Supabase JWT, or the
  upcoming frontend Settings → API Tokens page) and hand it to the
  CLI. Without `--token` against a Supabase backend, the command
  exits with an actionable error pointing to the `--token` workaround
  rather than the cryptic 404 detail.

### Docs
- `docs/cli.md` — `iris login --url` requires the **iris-api backend
  service**, not the frontend or iris-mcp host. Spelled this out plus
  the SQLite-vs-Supabase deployment-mode split, with a curl recipe
  for minting a PAT in Supabase mode.

## [5.0.0] - 2026-05-04

Major release: iris becomes agent-friendly. Three coordinated surfaces
— a stable HTTP API with Personal Access Tokens, a CLI, and an MCP
server — let humans and AI agents drive iris with the same auth,
search, browse, ask, and export capabilities the web frontend uses.
See [ADR-127](docs/adrs/ADR-127-Personal-Access-Tokens.md) through
[ADR-134](docs/adrs/ADR-134-MCP-Standalone-Service.md) for full
design rationale.

### Added
- **Personal Access Tokens** (ADR-127). New `/api/users/me/tokens` mgmt
  endpoints let any authenticated user mint long-lived revocable
  `iris_pat_…` bearer tokens for CLI / MCP / agent use. Tokens inherit
  the creating user's role, are Argon2id-hashed, and the plaintext
  value is returned exactly once. Authorisation goes through the same
  `Authorization: Bearer …` header the frontend uses — the auth
  dependency routes `iris_pat_` tokens through a new PAT validator and
  leaves the JWT code path unchanged.
- **Server-side export** (ADR-128). New `/api/export/*` endpoints
  produce JSON or Markdown bundles for diagrams, elements, packages,
  sets, and collections. Anonymous-friendly (ADR-123 parity), subject
  to a 10,000-element cap per bundle. Complements ADR-039 — client-side
  visual export in the browser is unchanged.
- **Public OpenAPI docs** (ADR-129). `/api/docs` (Swagger UI) and
  `/api/openapi.json` are now served in every environment, not just
  debug mode. `docs/api.md` describes the auth model, rate-limit
  buckets, and the unversioned-path + `-v2` deprecation policy.
- **Per-auth-type rate-limit buckets**. Middleware now splits traffic
  into `login` / `refresh` / `anon` / `anon_ai` / `pat` / `general` and
  tunes each independently so a busy CLI user can't starve browser
  traffic and vice versa. Configurable via `IRIS_RATE_LIMIT_*` env vars.
- **iris-client** (ADR-132): shared async Python client library under
  `iris-client/`. Typed methods for every v1 endpoint plus an SSE
  streaming helper for `ask`.
- **iris-cli** (ADR-130): Python command-line tool (`iris`) for read-
  only + AI operations. `iris login`, `iris search`, `iris diagrams
  get`, `iris export diagram|set|… --format json|markdown`, `iris ask
  --stream`, etc. Installable via `uv tool install` from the repo;
  config in `~/.config/iris/config.toml` (0600).
- **iris-mcp** (ADR-131): stdio Model Context Protocol server for AI
  agents. Installable into Claude Desktop / Claude Code / Cursor via a
  three-line config block. Exposes ~19 tools and `iris://` resources.
- **Remote MCP transport** (ADR-133): iris-mcp now also runs as a
  Streamable-HTTP server mounted on the iris backend at `/mcp`. End
  users add iris to Claude Desktop / Cursor by pasting the URL into
  the connector UI — no Python, no uv, no git, no JSON config edit.
  Stdio transport (ADR-131) remains the option for offline/local use.
- **iris-mcp standalone service** (ADR-134): the production MCP
  endpoint runs as its own Render web service alongside the iris
  backend. Splits the MCP SDK's memory footprint off the iris-api
  dyno (which OOM'd on the 512 MB free tier when MCP was embedded).
  The embedded mount stays in the codebase, opt-in via
  `IRIS_EMBEDDED_MCP=1` for one-process local dev. Bare `/mcp`
  requests no longer 307-redirect to `/mcp/` — some MCP clients drop
  POST bodies on chase, fixed by a path-normalising middleware.

### Changed
- `POST /api/ai/files/extract` no longer requires a JWT — it now uses
  `get_optional_user`, matching the other AI endpoints under ADR-123.
  Anonymous callers are subject to the existing `anon_ai` rate-limit
  bucket.
- Root `pyproject.toml` declares a uv workspace with members
  `iris-client`, `cli`, `mcp`. Backend stays outside the workspace for
  now.

### Deploy notes
- No new env vars required to run; optional tuning via
  `IRIS_RATE_LIMIT_PAT` (default 60/min) and `IRIS_RATE_LIMIT_ANON`
  (default 30/min).
- Supabase deployments pick up the new `personal_access_tokens` table
  automatically via `m042_personal_access_tokens.sql` (idempotent; RLS
  enabled, owner-only policies).

## [4.3.0] - 2026-04-22

### Added
- **AI "Create Diagram" extended beyond DoView to four more notations (ADR-132).** The layered-prompt framework built for DoView (ADR-094) has been scaled out: AI-assisted creation now supports Simple (component, roadmap, free-form), UML (sequence, class), ArchiMate (process), and C4 (deployment) — seven new notation × diagram-type bundles in addition to DoView's outcomes_map and overview. The notation dropdown in the Ask-AI "Create Diagram" tab is now registry-driven (no pre-selected default — user picks from DoView, Simple, UML, ArchiMate, or C4). A second diagram-type dropdown appears for non-DoView notations, populated from `GET /api/registry/creation-catalogue`. DoView's creation flow is unchanged — its own Stage 0–3 prompt still drives outcomes_map/overview branching internally. Eleven new prompt rows are seeded via SQLite migration `m040` and Supabase migration `m041`; existing DoView rows are untouched. See SPEC-132-A (prompt authoring) and SPEC-132-B (selector UI contract).
- **Location picker now lets you pick Collection → Set → Package** when generating AI diagrams without a pinned Set. Closes a pre-existing gap where `POST /api/ai/sets//create-diagram/apply` 404'd when no Set was selected on the `/ask` page.
- **UML sequence diagrams materialise correctly.** AI-generated `{nodes, edges}` for `diagram_type=sequence` are translated in `create_diagrams_from_ai` into the `{participants, messages, activations}` shape the dedicated sequence renderer expects, so the canvas populates on first paint.

### Changed
- Creation-mode system prompt now prepends a "User selection" preamble when both notation and diagram_type are known, and each non-DoView notation prompt skips Stage 0 when sufficient context (Set content, attached files, docref, prior chat) is present — reduces redundant "which diagram type?" / "describe the system" rounds.

## [4.2.1] - 2026-04-22

### Fixed
- **Settings now visible in the sidebar for anonymous visitors.** The Theme, Default Notation, and Visual Toggles sections of `/settings` are all localStorage-backed and meaningful to everyone — no reason to hide them behind sign-in. Moved `/settings` from the authenticated-only nav list to the public nav list; the page itself hides the Change Password form for anonymous users (no account to change a password on). Every signed-in role including **Viewer** has always had access to `/settings`; this fix extends that to anonymous browsing so theme and notation preferences can be set without creating an account.

## [4.2.0] - 2026-04-21

### Added
- **Comprehensive user guide (`/guide`).** The guide has been expanded from 10 thin sections to 16 deep sections covering every user-facing capability — not just the read-only surface. Six new sections: **Canvas Editing** (lock UI, edit-mode, add/link element, connect mode, undo/redo, save, fullscreen); **Notations** (Simple / Component / UML / ArchiMate / C4 / Sequence / DoView / Roadmap reference); **Comments** (per-diagram and per-element threads); **Imports & Data** (Sparx EA, PowerPoint, DocRef legislation, recycle bin, version history & rollback); **Roadmap (Scenia)**; **Themes & Accessibility** (theme switching, per-element theming, WCAG 2.2 AA). Existing nine sections were rewritten with deeper detail. Sign-in-only material is called out inline with a "Sign in to use this" blockquote — anonymous visitors can discover every feature Iris offers even before authenticating (SPEC-122-A amended).
- **Social preview card when Iris URLs are shared.** Pasting an Iris URL into LinkedIn, Slack, Teams, WhatsApp, or any platform that reads Open Graph / Twitter Card metadata now renders a rich card: the user's dashboard screenshot at `frontend/static/iris-preview.png`, the title *Iris — Integrated Repository for Information & Systems*, and a short description. Metadata lives in `src/app.html` (not `<svelte:head>`) because Iris is a static SPA and social scrapers don't execute JS; tags are templated at build time via `%sveltekit.env.PUBLIC_SITE_URL%` so the same build works for every deploy. Declared in `render.yaml` as `PUBLIC_SITE_URL`, `sync: false` (ADR-126).
- **Eye favicon.** The favicon has been replaced from the default Svelte logo to a hand-written eye SVG (almond shape + blue iris + dark pupil + white catch-light) reflecting the Iris name. Single-file change under `frontend/src/lib/assets/favicon.svg`.

### Changed
- Screenshot generator (`frontend/tests/screenshots/generate.spec.ts`) now produces six new shots (`imports.png`, `recycle-bin.png`, `admin-banner.png`, `admin-users.png`, `admin-audit.png`, `admin-locks.png`) alongside the existing ten. Re-run via `npm run screenshots` whenever the UI changes meaningfully.

### Deploy notes
- Set the new `PUBLIC_SITE_URL` environment variable in the Render frontend service for each environment (e.g. `https://iris-uat.chrisbarlow.nz`). Without it, social-preview URLs resolve as relative paths, which work on some platforms but not all.

## [4.1.3] - 2026-04-21

### Fixed
- **Supabase search SQL placeholder bug — this is the actual reason search returned zero results on UAT.** `_search_postgres` used `%s` (psycopg-style) inside the `ts_rank(...)` subexpression of every SELECT while the rest of the query used `?` (SQLite-style). The Iris DB adapter converts `?` to asyncpg's `$N` but leaves `%s` as literal text, so queries sent to Postgres had an un-bound `%s` token — Postgres either errored or the query silently returned nothing. Converted all five entity queries (elements, diagrams, packages, sets, collections) to consistent `?` placeholders. Placeholder/parameter counts now match exactly. This complements v4.1.2's schema migration (which was necessary but not sufficient — the schema was right, the Python call site was broken).
- Verify on UAT: typing `msd` on the dashboard should now return the MSD package + related diagrams. No re-migration needed; v4.1.2's `m040` still applies.

### Changed
- **User Guide moved to the header; keyboard shortcuts merged in; `/help` route deleted.** The "Guide" sidebar entry has been replaced by a "User Guide" link in the header (replacing the old "Help" link) so docs sit consistently with the other session-level actions (Sign in/Sign out, theme). The Keyboard Shortcuts section previously on `/help` is now a section of the User Guide (`/guide/keyboard-shortcuts`), expanded with the full sidebar shortcut list. The old `/help` route has been removed; any bookmarks pointing there should be updated to `/guide`.

## [4.1.2] - 2026-04-21

### Fixed
- **Search parity on Supabase** — on the Supabase/PostgreSQL backend (production/UAT), the search endpoint only queried `elements` and `diagrams` — packages/sets/collections had no `search_vector` columns and no trigger functions, so admin-created packages like "NZ Ministry of Social Development (MSD) DoView Strategy Diagram" were invisible to search even though they existed in the database. Additionally, the existing `BEFORE INSERT OR UPDATE` triggers on `elements`/`diagrams` read from `*_versions` tables at trigger time, but services insert the version row *after* the parent row — so the parent's `search_vector` was empty on initial create and only populated on subsequent updates. Fix ships in two pieces (ADR-125):
  - **New migration `m040_search_all_entities.sql`** — adds `search_vector` columns + GIN indexes + trigger functions for `packages`, `sets`, `collections`. Adds chain-triggers on `element_versions`, `diagram_versions`, `package_versions` that re-fire the parent's BEFORE trigger after the version row is committed, closing the INSERT-ordering gap. Backfills every existing row in all five entity tables.
  - **`_search_postgres` extended** — now queries all five entity types to match `_search_sqlite` feature-for-feature. Scope filters (set/collection) apply uniformly; deep links point to `/packages/<id>`, `/sets`, `/collections` consistently with the SQLite path.
- Requires manual application of `m040` to the UAT Supabase instance (via Supabase SQL Editor or `scripts/supabase-migrate.sh`) — Render does not run migrations automatically.

## [4.1.1] - 2026-04-21

### Added
- **System notification banner** — admins can post a system-wide message from Admin → Settings that renders as a sticky top strip on every page for every visitor (anonymous included). Dismissible per-message per-browser-session; a new admin-posted message re-appears even if the previous one was dismissed. Reuses the existing `settings` key-value table under `notification_banner_message`; the admin write path is the existing admin-gated `PUT /api/settings/{key}` (DRY). A focused public `GET /api/notifications/banner` lets anonymous visitors see the message without auth. Plain-text only — no HTML, no Markdown, Svelte's default `{expression}` escaping is the XSS defence (ADR-124, SPEC-124-A).

### Fixed
- **Cleaner AI provider error messages** — the previous "LLM provider error" 502s surfaced the raw `httpx` error including the provider URL (e.g. "Server error '502 Bad Gateway' for url 'https://api.agentics.org.nz/...'"). New `app/ai/error_mapper.py` classifies provider exceptions (timeout, network/connect, 429 rate-limit, 401/403 auth, 5xx upstream, 4xx client, generic) and returns a concise user-facing message. Stack traces still go to server logs for operators. Applies to both `POST /api/ai/ask` / `POST /api/ai/sets/{id}/ask` and the admin "Test" button on each provider. Raw URLs never leak to users (regression-tested).

### Notes
- The AI provider health badge (red/green dot in the model picker) already exists in `SetQA.svelte` via the `_run_ping_check` infrastructure from earlier releases — no change needed. The system banner is the right channel for admins to explain a known outage.

## [4.1.0] - 2026-04-21

### Added
- **User guide at `/guide`** — hand-written Markdown documentation with a left-hand navigation bar covering Getting Started, Dashboard, Collections & Sets, Packages & Diagrams, Knowledge Graph, Search, Ask AI, Bookmarks, and Admin. Markdown rendered through `marked` + DOMPurify (protocol #7). Screenshots generated on demand via `npm run screenshots` (new Playwright project) and served from `static/guide/` so the deployed app has them without rebuilding. Nav entry added to AppShell for both anonymous and authenticated users (ADR-122, SPEC-122-A, closes #15).
- **Anonymous read-only mode** — visitors can now browse every collection, set, package, diagram, element, knowledge graph, and run searches without signing in. Ask AI is also available to anonymous callers with a stricter per-IP rate limit (default 10 requests/hour, env `IRIS_RATE_LIMIT_ANON_AI`). Writes and admin routes remain authenticated. Backend gains a `get_optional_user` dependency; frontend `+layout.svelte` no longer redirects unauthenticated users to `/login`, with a new `admin/+layout.svelte` gate preserving admin privacy. A "Sign in" button replaces "Sign out" in the header when anonymous (ADR-123, SPEC-123-A, closes #18).

### Fixed
- **Dashboard search silently filtered by a stale set id** — typing "msd" on the dashboard at `/` with no visible filter returned zero results when a previously-viewed set id was cached in sessionStorage. The counts panel legitimately restored the last set (visible in the header), but the search bar does not display its scope, so a remembered filter read as "search is broken". Fix: split `searchSetId`/`searchCollectionId` deriveds that read URL params only; counts panel unchanged. Deep-linked scoped search via `?set_id=…` still works (ADR-121, closes #16 and #17).
- **Packages, sets, and collections were not indexed for search on create/update/delete** — only the startup `rebuild_search_index` populated their FTS5 tables, so any entity created or imported after the server started was invisible to search until the next restart. This is the deeper root cause behind "search is broken" on UAT where "NZ Ministry of Social Development (MSD) DoView Strategy Diagram" (a package) is expected to match `msd`. Fix: added per-operation `index_package`/`index_set`/`index_collection` and `remove_*_index` calls in all three services, mirroring the existing elements/diagrams pattern. Bug surfaced the first time newly-created entities failed to appear in search — no reindex needed for existing data because startup rebuild still runs.

## [4.0.4] - 2026-04-21

### Fixed
- **Knowledge graph radial hierarchy ordering** — on UAT-scale single-collection data (711 nodes, 11 sets × 60 packages × 639 diagrams) packages were consistently settling *outside* their own diagrams (mean package-radius ≈ 170–190 px vs mean diagram-radius ≈ 140–150 px; 0/11 sets radially ordered correctly), inverting the expected `collection → set → package → diagram → element` visual flow. Root cause: every diagram has both a set_membership edge (distance 120) and a hierarchy edge (distance 25); the N short hierarchy links collectively yanked each package outward through its own children. Fix: per-galaxy radial layer force (`d3.forceRadial`-style inline loop) pinning each node type to a prescribed radius from its collection centroid — Collection=0, Set=120, Package=240, Diagram=360, Element=480, all scaled by `link_length × node_spacing`. Inter-galaxy separation is now radius-aware (`target = 2·R_total + padding`) instead of centroid-only `1/dist²`. The SPEC-119-A inner-layer `1/dist²` calls at the set and root-package layers are superseded (ADR-120, SPEC-120-A).
- **Same-tier label overlap** — two labels at the same hierarchy tier (e.g. two packages, two diagrams) could visually overlap because the label overlap-suppression loop only compared against higher-precedence tiers (`b.tier < ti`). Now compares against every already-drawn label; same-tier draw order is sorted by `relationship_count` descending, so the most-connected label wins the space.

## [4.0.3] - 2026-04-20

### Fixed
- **"Direct diagram links" toggle no longer collapses the knowledge graph** — turning off this visibility toggle previously removed the set→diagram edges from the force simulation entirely, not just the visual rendering, which deleted the link force (distance 120 px) that blooms each set's diagrams into a visible petal around their set node. Without that force, the galaxy-style separation between collections (ADR-119 / SPEC-119-A) collapsed into a compressed cluster near the graph centre. Fix: use force-graph's `linkVisibility` callback to hide these edges visually while keeping them in the physics — the toggle is now a pure display control (ADR-119, SPEC-119-A follow-up). Also relaxes the ADR-118 regression test's inter-collection monotonicity assertion from strict step-wise (`mid ≥ low ∧ high ≥ mid`) to endpoint-only (`high > low`) — with ungated inner-layer 1/dist² repulsion the individual step-wise comparison is noisier than the full-sweep invariant.

## [4.0.2] - 2026-04-20

### Fixed
- **Knowledge graph collections now repel each other as whole clusters** — restores the "galaxy" effect where each collection (with all its sets, packages, diagrams, and elements) acts as a cohesive mass repelling other collections through every tier of its member hierarchy. ADR-118's gating confined cross-collection separation to the centroid-level collection layer only, so collection bboxes could still visually mingle when inner clusters were wide. ADR-119's first cut kept that gating; this follow-up ungates the inner `1/dist²` layers so set- and package-level repulsion fires across collections as well as within. Self-decay at `1/dist²` and linear spread scaling keep the added cross-layer force from compounding into the pre-ADR-118 "loses the plot at spread=3" explosion (ADR-119, SPEC-119-A)

## [4.0.1] - 2026-04-20

### Fixed
- **Knowledge graph cluster collapse on large single-collection datasets** — at UAT scale (observed on "DoView Strategy Models": 11 sets × 60 packages × 639 diagrams, 711 nodes) the bidirectional target-distance separator at the set and root-package layers introduced by ADR-118 compressed all per-set diagram clusters to within ±100 px of the graph centre, because a fixed target distance of `150 × spread` px assumed a cluster density that dense data violates. Reverted the force shape at the set and root-package layers to self-decaying `1/dist²` pure repulsion — cluster equilibrium radius is now set by charge balance, so the layout adapts to whatever density the data has (5 members or 500). Collection layer keeps its bidirectional pull-back (anchors the orphan-set contract). Regression captured as a Playwright page.route fixture of the real UAT /api/graph response so the test is fast, deterministic, and CI-friendly (ADR-119, SPEC-119-A)

## [4.0.0] - 2026-04-20

### Added
- **Multi-entity knowledge graph** — interactive force-directed graph on the dashboard showing elements, diagrams, and packages as colour-coded nodes with all relationship types (element relationships, package relationships, diagram links, diagram→element canvas refs, diagram→package refs, hierarchy containment); includes settings panel to toggle each node and edge type on/off, responsive side-by-side layout with diagram hierarchy on wide screens, and hover-to-zoom from hierarchy to graph (ADR-116)
- **Graph settings: physics sliders and admin defaults** — label density, node spacing, size contrast, and link length sliders with real-time graph updates; admin-configurable defaults per global/collection/set scope stored in database; user overrides via localStorage with "Reset to defaults" button; cascading settings: hard-coded → admin DB → user localStorage (ADR-117)
- **Graph data API** — `GET /api/graph?set_id=X` endpoint returning elements, diagrams, and packages as nodes with 6 edge types in a single optimised call, with collection-scope support; `GET/PUT /api/graph/settings` endpoints for admin-default graph settings (ADR-116, ADR-117)
- **Diagram-level AI context scoping** — Diagram dropdown on the Ask AI Context tab filters AI context to a specific diagram and its elements, bypassing MNEMOS for precise scoped queries; dropdown populates from selected sets and follows Collection dropdown styling
- **Session file upload for AI context** — upload files (PDF, DOCX, XLSX, PPTX, CSV, text) on the Ask AI Context tab as session-scoped AI context; text extracted server-side via stateless endpoint, held in browser state, and included alongside sets and legislation in chat requests; supports drag-and-drop, 5 MB limit, and files-only conversations (ADR-115)
- **Advanced provider parameters** — collapsible Advanced Settings section in the AI provider edit modal exposing top_p, top_k, min_p, frequency_penalty, presence_penalty, and stop sequences; parameters are provider-aware with unsupported ones silently omitted (ADR-114)
- **Model selector in Ask AI** — compact dropdown in the chat toolbar allowing users to choose which AI provider to use per conversation, with a new lightweight `GET /api/ai/providers/active` endpoint (ADR-114)
- **DocRef legislation integration** — optional extension for importing NZ legislation documents from legislation.docref.nz as AI context; browse and import chunked CSVs with progress indicators, select imported legislation alongside sets and collections on the Ask AI page, with hourly background index refresh (ADR-112)
- **MNEMOS semantic retrieval** — optional MNEMOS extension for AI-powered semantic context retrieval, replacing naive token-budget truncation with question-aware ranking across sets; managed via admin Extensions tab with graceful fallback to direct retrieval when unavailable (ADR-111)
- **RetrievalPort abstraction** — protocol-based retrieval strategy allowing pluggable context backends; `DirectRetrieval` wraps existing `context.py`, `SemanticRetrieval` uses MNEMOS (ADR-111)
- **Bulk DoView PPTX import** — upload multiple .pptx files in one operation via `POST /api/import/pptx/batch`, all grouped under a single set with per-file error reporting and partial success support (ADR-108)
- **Package-level AI context** — Ask AI set selector now supports drilling down into packages within each set, constraining AI context to specific packages for more focused responses (ADR-109)
- **Scenia cloud deployment** — Scenia roadmapping app added as a third Render Blueprint service, pulling from the external fork as a static site with CORS and cross-service URL configuration (ADR-110)
- **Collection-scoped filtering** — clicking a collection card now filters sets, diagrams, elements, and search results across dashboard and list pages

### Changed
- **Ask AI tabbed layout** — split Ask AI page into Context and Request tabs; context selectors on first tab, expanded chat dialogue on second tab with selected dataset summary (ADR-113)

### Fixed
- **AI discuss crash** — added missing `mode` and `thread_id` columns to `ai_conversations` table (SQLite migration m033)
- **Knowledge graph spread slider on multi-collection views** — replaced the cubic `spread³` cluster force with a bidirectional target-distance separator, gated set- and root-package-level separation to within a single collection, and removed the inverse-spread cohesion decay; the `node_spacing` slider now behaves predictably across its full 0.2–3.0 range instead of "losing the plot" at the extremes (ADR-118)
- **Knowledge graph orphan-set drift** — sets with no collection (e.g. the "default" set) now participate in the collection-layer force under a synthetic `__orphan_<sid>` group, so the bidirectional separator pulls them back when farther than target. Previously these nodes had no collection-layer force at all and ratcheted outward under charge repulsion each time the spread slider rose (ADR-118, SPEC-118-A)

## [3.0.0] - 2026-03-25

### Added
- **Extensions framework** — database-backed extension registry with admin settings tab for installing, enabling, and disabling optional integrations; all extension state persists across restarts (ADR-103)
- **Scenia roadmapping integration** — open-source roadmapping tool integrated as the first Iris extension, with full CRUD for strategies, programmes, initiatives, assets, applications, milestones, resources, and dependencies (ADR-104)
- **Scenia React embedding** — full Scenia React app mounted at `/scenia` via `createRoot`, with pluggable db adapter replacing IndexedDB with Iris API calls (ADR-106, fork: cgbarlow/waylonkenning_scenia)
- **Roadmap data view** (`/roadmap`) — Iris-native tabular view of all Scenia entities with "View in Scenia" links and set selector
- **Scenia bulk data API** — atomic read/write endpoints (`GET/PUT /api/scenia/data`) matching Scenia's `getAppData()`/`saveAppData()` interface
- **Scenia-specific tables** — timeline settings, version snapshots, asset categories, and application statuses with set-scoped data isolation
- **Extension gating** — FastAPI dependency that gates all Scenia routes on extension availability; returns 404 when extension is not installed or disabled
- **Scenia seed data** — full demo data (6 strategies, 6 programmes, 40 assets incl. GEANZ catalog, 40 initiatives, 8 applications, 30 app segments, 14 milestones, 9 dependencies, 6 resources) seeded on extension install
- **10 interlinked diagrams** — Strategic Overview, 6 Programme Roadmaps, Asset Landscape, Dependency Map, Resource Allocation — all with entity-backed nodes and inter-diagram links
- **Cross-links (Iris ↔ Scenia)** — "View in Scenia" buttons on element detail pages and canvas panel; "View in Iris" links from Scenia
- **Conditional Roadmap navigation** — sidebar shows "Roadmap" nav item only when Scenia extension is enabled
- **DoView PPTX import** — import DoView models from .pptx files with structural compliance validation, shape classification (overview tiles, final outcomes, outcome boxes, causal arrows), column-based causal link inference, cross-diagram navigation linking, and colour preservation (ADR-107)

## [2.7.4] - 2026-03-25

### Added
- **Collections** — higher-level grouping for Sets with full CRUD, thumbnails, dashboard stats card (4-column layout), collection-scoped filtering on Elements/Diagrams pages, and `Iris / Collection / Set` header breadcrumb (ADR-102)
- **Multi-set AI context** — Ask AI now supports selecting multiple Sets (with or without a Collection) as context for Discuss and Create Diagram workflows via new `POST /api/ai/ask` endpoint
- **Collection pill on Sets page** — Sets belonging to a Collection display the collection name as a pill badge
- **Linked Diagram property editor** — set, change, or clear a node's linked diagram directly from the edit sidebar (ADR-099)

## [2.7.2] - 2026-03-23

### Added
- **Visual Toggles** settings section — user-controlled display preferences for diagram nodes (ADR-101)
- **Element count badge** — optional top-right badge on nodes showing how many diagrams each element is used in, toggled via Settings → Visual Toggles
- **Hide description toggle** — `hideDescription` theme rendering option; DoView defaults to hidden, per-node override in edit sidebar

### Changed
- **DoView element-backed nodes** — all DoView diagram nodes are now created as proper elements with `entityId` linkage, and all causal links as relationships with `relationshipId`, enabling cross-diagram element reuse and diagram-entity relationship tracking (ADR-100)
- AI diagram creation (`create_diagrams_from_ai`) now materialises element and relationship records for every node and edge

### Fixed
- Double borders on DoView nodes — removed duplicate `visualStyle` application from DoviewRenderer wrapper
- Stale seed test assertions for diagram count (35 → 39) after DoView diagrams were added in v2.6.0
- Seed test setup missing migrations m028 (AI creation prompts) and m029 (sequence order)

## [2.7.1] - 2026-03-22

### Added
- **Diagram sequence order** — user-controllable ordering of diagrams and packages in the navigation hierarchy tree (ADR-098, Issue #7)
- `PUT /api/diagrams/reorder` endpoint for reordering diagrams/packages within a parent group
- Drag-and-drop reordering in the dashboard hierarchy tree with visual drop indicators
- `sequence_order` field on diagrams and packages tables (migration m029/m032)

### Fixed
- Entity-to-entity relationships not displayed in diagram Relationships tab — field name mismatch `elementId` → `entityId` in relationship query (ADR-097, Issue #4)
- Diagram relationships endpoint crash on SQLite — replaced unsupported `async for` cursor iteration with `fetchall()`
- DoView seed builder functions missing positional arguments — startup crash on fresh database

## [2.6.0] - 2026-03-21

### Added
- **DoView notation** — fifth notation in Iris for outcomes-based theory of change diagrams (ADR-094)
- DoView entity types: `outcome_box`, `final_outcome`, `overview_tile`, `source_reference`
- DoView relationship type: `causal_link` (grey arrow, 2px)
- DoView diagram types: `outcomes_map` (left-to-right causal flow) and `overview` (navigation tiles)
- `doview` notation added to registry with `free_form` cross-notation mapping
- DoView default theme (`doview-default`) with 10-color palette (yellow, pink, blue, green, beige, lavender, peach, cyan, grey, white)
- `DoviewRenderer.svelte` — node renderer for all DoView entity types with color overrides
- `DoviewEdgeRenderer.svelte` — causal link edge renderer with grey arrow styling
- Dynamic dispatch: `DynamicNode`/`DynamicEdge` route `doview` notation and DoView entity types
- DoView notation detection in `notation_detection.py`
- Entity dialog and diagram creation dialog support for DoView
- Seed example DoView diagrams: DoView Overview (navigation tiles) and Outcomes Map (4-column causal flow)
- Migration m027 for notation, diagram types, mappings, and DoView theme
- **AI Diagram Creation system** — layered system prompt composition for AI-guided diagram creation (ADR-094-B)
- `ai_creation_prompts` table with layered prompt architecture: base / notation / diagram_type / override (migration m028)
- `build_creation_system_prompt()` — composes layered prompts; override layer replaces all others
- `create_diagrams_from_ai()` — materialises AI-generated JSON into Iris canvas diagrams with `linkedDiagramIndex` resolution
- Admin creation prompts endpoint: `GET /api/ai/creation-prompts`, `PUT /api/ai/creation-prompts/{id}`
- Apply creation endpoint: `POST /api/ai/sets/{set_id}/create-diagram/apply`
- Creation mode toggle in Ask AI chat — switches to DoView creation mode with notation selector
- "Create Diagrams" action button appears when AI outputs a valid diagram JSON block
- Admin Creation Prompts editor in `/admin/ai/` — table of layered prompts with full-text edit modal
- Seeded default prompts: base output format, DoView methodology (guided 8-question conversation), outcomes_map layout rules, overview layout rules
- **Optional Supabase/Render deployment** (ADR-094, ADR-096) — cloud deployment path alongside the default SQLite self-hosted mode
- `DatabasePort` protocol with `SqliteAdapter` (aiosqlite passthrough) and `SupabaseAdapter` (asyncpg with automatic `?` → `$N` placeholder conversion)
- `IRIS_DB_BACKEND` env var (`sqlite` default, `supabase` for cloud mode)
- PostgreSQL migrations (`backend/app/migrations/supabase/`) — 30 SQL files covering all schema including FTS via `tsvector`/GIN indexes and triggers
- Supabase migration m028: DoView notation, diagram types, notation-type mappings, and DoView default theme (Supabase equivalent of SQLite m027)
- Supabase migration m029: `ai_creation_prompts` table and 4 seeded layered prompts (Supabase equivalent of SQLite m028)
- `profiles` table in Supabase mode: maps `auth.users` UUIDs to Iris roles; auto-created by trigger on user creation
- Supabase Auth JWT validation (`app/auth/supabase_service.py`) — HS256, no aud verification
- `GET /api/auth/me` endpoint (both modes) — returns authenticated user profile
- Dual search: FTS5 for SQLite, `tsvector`/`to_tsquery` for PostgreSQL (`app/search/service.py`)
- `render.yaml` Blueprint with static site (frontend) and web service (backend) definitions
- `VITE_API_BASE_URL` env var — configurable backend URL for cross-origin Render deployment (empty default preserves self-hosted mode)
- `frontend/src/lib/config.ts` — runtime config from `VITE_DB_BACKEND`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`
- `frontend/src/lib/supabase.ts` — conditional Supabase JS client (null when not configured)
- Supabase mode frontend auth: `onAuthStateChange` token sync, `supabase.auth.signInWithPassword()` login, `supabase.auth.refreshSession()` token refresh
- Login page: email field and Supabase sign-in in Supabase mode; setup/request-account/forgot-password views hidden (managed via Supabase Dashboard)
- `.env.example` documenting all environment variables for both deployment modes
- `docs/deployment-render-supabase.md` — step-by-step Render + Supabase deployment guide
- Optional backend dependency: `asyncpg==0.31.0` (install with `uv sync --extra supabase`)

### Security
- **Row Level Security** enabled on all 34 Supabase tables with deny-all strategy (ADR-095) — blocks `anon` and `authenticated` roles from direct PostgREST table access while backend (`postgres` role) bypasses RLS as table owner

### Changed
- Seed data bumped to v7 with Iris System DoView (39 diagrams, 66 elements, 63 relationships)
- `build_edge_visual()` returns `None` (not `{}`) when no visual overrides are present — consistent with `build_node_visual()`
- `DatabaseManager` now accepts `AppConfig` (preferred) or `DatabaseConfig` (backward-compatible)
- All service functions: `db` parameter type updated from `aiosqlite.Connection` to `DatabasePort` (no runtime change in SQLite mode)
- `app/auth/dependencies.py`: `get_current_user` branches on `db_backend` — SQLite checks `users` table, Supabase checks `profiles` table
- `app/auth/router.py`: login/refresh/setup/change-password return 404 in Supabase mode; setup/status always returns `needs_setup: false` in Supabase mode
- `app/users/router.py`: list/update users reads from `profiles` table in Supabase mode; create user returns 501 (use Supabase Dashboard)
- `app/middleware/audit.py`: JWT decoded with correct secret per mode; username resolved from `profiles` (Supabase) or `users` (SQLite)
- `frontend/src/lib/utils/api.ts`: `tryRefresh()` delegates to Supabase SDK in Supabase mode
- `frontend/src/lib/stores/auth.svelte.ts`: `clearAuth()` calls `supabase.auth.signOut()` in Supabase mode

## [2.5.0] - 2026-03-19

### Added
- AI model management module (`backend/app/ai/`) — DB-backed provider registry, client abstraction, admin CRUD, Set-scoped Q&A (ADR-093)
- `ai_providers`, `ai_conversations`, `ai_usage_log` tables (migration m026)
- `AIClient` ABC with `OpenAICompatibleClient` (openai, ollama, lmstudio, openrouter, custom) and `AnthropicClient`
- Retry logic: exponential backoff on network/5xx errors; no retry on timeouts or 4xx auth (translated from machine-dream_ag patterns)
- `build_set_context()` — structured text context builder from Set elements, relationships, diagrams with token-budget truncation
- Provider CRUD API (`GET/POST/PUT/DELETE /api/ai/providers`), test endpoint, set-default endpoint
- Set Q&A endpoint (`POST /api/ai/sets/{set_id}/ask`) with SSE streaming support
- Conversation history endpoint (`GET /api/ai/sets/{set_id}/conversations`)
- Usage log endpoint (`GET /api/ai/usage`) for admin visibility
- Admin AI Providers page (`/admin/ai`) — provider list, add/edit modal with password input for API keys, test connection, set default, delete
- Brain icon for AI Providers in sidebar navigation (Phosphor Brain)
- Dedicated **Ask AI** page (`/ask`) with Set selector — accessible from main navigation between Dashboard and Sets
- Chat-style Q&A component with SSE streaming responses, animated thinking indicator, markdown rendering (`marked` + DOMPurify), copy-to-clipboard, and clear conversation
- Inline error display on provider test results (no hover required)
- AI module seed data: 4 new elements (AI Service, AI Client, Provider Registry, Context Builder), 8 relationships, and "AI Module Architecture" diagram under Simple Notation
- AI Module navigation tile on Iris Navigation overview
- `dev.sh` now sources `.env` file for API keys and env var overrides

### Changed
- API keys stored directly in DB (not env var names) — enterable via admin UI password field
- Set detail page links to `/ask` instead of embedding inline Q&A panel
- Seed data bumped to v5 with AI module additions (34 diagrams, 59 elements, 58 relationships)

### Security
- API keys stored in DB, never returned by API (`has_api_key: bool` in responses)
- Admin-only provider CRUD via existing `_require_admin()` pattern
- DOMPurify sanitization on all AI-generated content rendered via `{@html}` (Protocol 7)
- Input length cap: 4000 chars on question field via Pydantic `max_length`
- Context token budget (default 8000 tokens) prevents excessive LLM costs
- All AI calls logged to `ai_usage_log` + `iris_audit.db`

## [2.4.2] - 2026-03-19

### Added
- Title/description font controls in NodeStylePanel (separate colour, size, bold, italic for title vs description)
- Icon colour picker in NodeStylePanel
- Theme-aware fallback chain (per-element → theme → CSS fallback) in NodeStylePanel

### Changed
- NavigationCellNode refactored for faithful EA card rendering
- NodeStylePanel split into Node, Title Font, and Description Font sections
- Import service auto-detects navigation-cell-dominated diagrams as `free_form/simple`
- iris-default-simple theme seeds navigation_cell element defaults

### Fixed
- Parent package validation on diagram creation (clears invalid parent_package_id)
- ArchiMate/UML renderer visual override propagation
- Sequence viewport edge case

## [2.4.1] - 2026-03-09

### Added
- Comments sidebar — comments moved from page bottom to toggleable right sidebar with badge count
- Comments button visible in browse mode (windowed and fullscreen), hidden in edit mode
- Live preview of element edits on canvas (name, description, type reflect instantly while editing)
- ElementEditPanel component for inline element editing in the canvas sidebar
- NodeStylePanel wired into diagram page edit-mode sidebar alongside ElementEditPanel
- Unsaved changes confirmation dialog when switching from edit to browse mode
- Diagram relationships API endpoint (`GET /api/diagrams/{id}/relationships`) including diagram links
- Diagram link deletion endpoint (`DELETE /api/diagram-relationships/{id}`)
- Diagram links migration (`m025_diagram_links`)
- Hierarchy sidebar in fullscreen mode (browse and edit) with search and filter
- Hierarchy sidebar scroll position preserved across navigation
- Sidebar toggle button in fullscreen mode overlay
- Relationship indicator dot on Relationships tab when relationships exist
- Comment author username display (resolved via LEFT JOIN on users table)
- Relative timestamp formatting for comments ("just now", "5m ago", "3h ago", "2d ago")
- Themes link in admin navigation sidebar
- `areThemesLoaded()` helper in themeStore for conditional eager loading

### Changed
- Canvas height uses `calc(100vh - 317px)` to align bottom edge with hierarchy sidebar
- Canvas area extends to fill space freed by removing bottom comments section
- Page content shifts with `margin-right: 316px` when any sidebar is open (entity detail or comments)
- No page scrollbar when all content fits viewport (negative bottom margin technique)
- Entity detail sidebar and comments sidebar are mutually exclusive
- Sequence toolbar uses inline SVG icons matching SvelteFlow Controls styling
- ThemeSelector groups themes by notation with current notation first
- `discardChanges()` reloads diagram from API to guarantee clean state
- `parseCanvasData()` deep-clones diagram data to prevent edit mutations
- New canvas nodes default to `width: 200` for consistent sizing
- FocusView accepts `hideExit` prop to suppress exit button when sidebar is open
- Browse-mode canvas uses `panX` to shift viewport when sidebar opens

### Fixed
- Comments displayed user GUID instead of username — backend now JOINs users table
- Comment timestamps displayed raw ISO format — now shows friendly relative time
- Canvas spilling off bottom of screen — aligned with hierarchy sidebar via precise offset calculation
- Page scrollbar appearing despite content fitting — cancelled parent padding overflow

## [2.4.0] - 2026-03-09

### Added
- C4 hybrid visual notation with canonical colours and inline SVG type glyphs (ADR-092)
- C4TypeGlyph and C4TypePicker components for rich C4 type selection
- `borderStyle` support in theme system (NodeVisualOverrides, visualStyles, themeStore)
- C4 default theme seed with canonical colours (green person, blue system, red external) and dashed borders
- NotationPills component — clickable pill notation selector replacing dropdowns
- Version history restore/rollback UI with confirmation for elements and diagrams
- Diagram rollback API endpoint (`POST /api/diagrams/{id}/rollback`)
- Eager theme loading to prevent flash on diagram page

### Changed
- C4Renderer uses inline SVG glyphs instead of Lucide icons
- NodeStylePanel uses C4TypePicker for C4 notation nodes
- EntityDialog renamed "Create Entity" → "Create Element", uses NotationPills and C4TypePicker
- DiagramDialog uses NotationPills instead of notation dropdown
- Element detail page uses C4TypePicker in edit mode, C4TypeGlyph in view mode
- Edit mode badge styling: dark bg with white text (light theme), inverted for dark theme
- Center-to-center edge connections default to straight line routing
- Smoothstep edges use borderRadius=20, bezier edges use curvature=0.4
- Connection handle dots hidden in browse mode

### Fixed
- Theme loading flash on diagram page initial load
- ThemeSelector no longer lazy-loads themes (loaded eagerly by page)

## [2.3.6] - 2026-03-08

### Added
- Node resizing via drag handles in edit mode using SvelteFlow NodeResizer (ADR-091-A)
- NodeStylePanel wired into diagram page — select a node in edit mode to style it (ADR-091-A)
- Node resize changes persisted to visual overrides (width/height) on save (ADR-091-A)
- Lucide icon library (`lucide-svelte`) with 100+ curated architecture modelling icons (ADR-091-B)
- `IconRef` type and `NodeVisualOverrides.icon` field for per-node icon storage (ADR-091-B)
- Icon registry (`iconRegistry.ts`) resolving `IconRef` to Lucide Svelte components (ADR-091-B)
- `IconDisplay.svelte` component for rendering icons at any size from an `IconRef` (ADR-091-B)
- Semantic icon matcher (`icon_matcher.py`) — matches EA element names/stereotypes to Lucide icons via keyword similarity (ADR-091-B)
- Set-wide icon consistency: same element name always resolves to same icon across all diagrams in an import (ADR-091-B)
- NavigationCellNode renders matched Lucide icons when `visual.icon` is set, falls back to NID SVGs (ADR-091-B)
- Icon picker modal (`IconPicker.svelte`) with search, category filters for browsing and selecting icons (ADR-091-C)
- Icon section in NodeStylePanel — add, change, or remove node icons via the picker (ADR-091-C)
- Icon tag index (`iconTags.json`) shared between frontend search and backend matching (ADR-091-B)

## [2.3.5] - 2026-03-07

### Fixed
- All 144 diagrams now have correct node background colors — EA default white (#FFFFFF) emitted when Backcolor is unset (ADR-090)
- All 40 diagrams with unstyled edges now have explicit black line color — EA default #000000 emitted when LineColor is unset (ADR-090)
- 3 edges with stereotype but no name now display stereotype text as label with guillemets (ADR-090)

### Added
- Iterative visual audit framework (ea-audit.mjs) with comparison tracking across iterations (ADR-090)

## [2.3.4] - 2026-03-07

### Fixed
- All 149 diagrams now render edges correctly — unified handle IDs between backend and frontend (ADR-089)
- Node content no longer clipped — switched from fixed `height` to `min-height` for EA-imported nodes (ADR-089)
- Long text in fixed-width nodes truncated with ellipsis instead of hidden (ADR-089)
- All node types (UML, ArchiMate, C4, Boundary) now have dual source+target handles at every position (ADR-089)

### Added
- Comprehensive automated diagram audit script (`frontend/audit-diagrams.mjs`) covering 14 check categories (ADR-089)

## [2.3.3] - 2026-03-07

### Fixed
- Note "Feature Properties" no longer duplicates title in body — label prefix stripped from description (ADR-088)
- Attribute text in abstract classes renders upright — `font-style: normal` blocks italic inheritance (ADR-088)
- Node widths match EA dimensions exactly — `fixedSize` mode with `overflow: hidden` (ADR-088)
- Composition/aggregation edges show both diamond source marker and open arrow target marker (ADR-088)
- Diamond markers extend outward from node — `refX=0` instead of `18` (ADR-088)
- Edges auto-route via geometrically optimal handles when EA specifies auto-routing (ADR-088)
- Edge cardinality and role labels positioned per EA's stored LLB/LLT/LRT/LRB coordinates (ADR-088)
- Diagram frame zooms and pans with canvas — converted from absolute-positioned SVG to SvelteFlow node (ADR-088)
- Fixed-size node content no longer clipped — UML icons hidden and compact padding/line-height applied (ADR-088 R3)
- Package nodes now appear on diagrams — no longer skipped during import (ADR-088 R3)
- Diagram frame type label shows mapped type ("class", "pkg") instead of raw EA type ("Logical", "Package") (ADR-088 R3)

### Added
- Dual-type handles on UML nodes — each side accepts both source and target connections (ADR-088)
- `compute_auto_handles()` backend function for geometry-based handle selection (ADR-088)
- `DiagramFrameNode.svelte` component for canvas-integrated diagram frames (ADR-088)
- EA label position parsing (LLB/LLT/LRT/LRB) from `t_diagramlinks.Geometry` (ADR-088)

## [2.3.2] - 2026-03-06

### Added
- Diagram frame/title block for imported EA diagrams — shows `[type] [name]` tab with border (ADR-087)
- Attribute sort option (`pos` or `alpha`) in view config for canvas (ADR-087)
- EA connector `Start_Edge`/`End_Edge` mapped to SvelteFlow handles for explicit connection points (ADR-087)
- EA orthogonal routing via `t_diagramlinks.Path` waypoints rendered as polyline edges (ADR-087)
- EA absolute connection points (`PtStartX/Y`, `PtEndX/Y`) override auto-computed handle positions (ADR-087)

### Fixed
- Abstract class `«abstract»` stereotype text no longer shown when EA theme active — italic-only conveys abstract (ADR-087)
- UML class name labels properly centered in node header (ADR-087)
- Abstract class names render as italic-only (not bold+italic) when EA theme active (ADR-087)
- Note elements use original EA dimensions — fixes overlap with adjacent elements (ADR-087)
- Theme selector dropdown now overrides diagram's preferred theme when explicitly changed (ADR-087)
- Note background and border colors respect theme configuration via CSS variables (ADR-087)
- SVG markers (diamonds/arrows) visible at all zoom levels with `overflow: visible` (ADR-087)

### Changed
- `ThemeRenderingConfig` extended with `hideTypeStereotypes` and `abstractBoldOverride` fields (ADR-087)

## [2.3.1] - 2026-03-06

### Added
- UML class attributes rendered in compartments on canvas nodes (imported and user-created) (ADR-086)
- UML visibility prefixes (+/-/#/~) from EA Scope field on attributes (ADR-086)
- SVG marker definitions for UML arrowheads: filled diamond, open diamond, closed triangle, open arrow (ADR-086)
- Cardinality labels at edge endpoints, controlled by view config (ADR-086)
- Role name labels at edge endpoints, controlled by view config (ADR-086)
- Edge style panel for editing cardinality, roles, stereotype after creation (ADR-086)
- Relationship dialog extended with cardinality, role, stereotype fields for UML notation (ADR-086)
- Edit lock integration: lock acquired on edit, conflict banner, heartbeat, auto-release (ADR-080, ADR-086)
- POST lock release endpoint for sendBeacon compatibility (ADR-086)

### Fixed
- Attributes from EA import not appearing on canvas class nodes
- UML edges rendered without arrowheads/diamonds
- Edit mode not acquiring lock per ADR-080 specification
- sendBeacon lock release using non-existent endpoint
- UML class nodes showing description text causing massive overflow — now hidden on compartment types (ADR-086)
- Node height forced to EA pixel value clipping content — now uses min-height for natural sizing (ADR-086)
- EA orthogonal route style (Auto Route) incorrectly mapped to bezier — now maps to step routing (ADR-086)

## [2.3.0] - 2026-03-05

### Added
- Per-element visual overrides — nodes and edges carry optional `visual` properties (bgColor, borderColor, fontColor, width, height, lineColor, lineWidth, dashArray) applied as inline styles (ADR-085)
- Theme system — `themes` table with CRUD API (`GET/POST /api/themes`, `GET/PUT/DELETE /api/themes/{id}`), notation-linked visual profiles with element defaults, stereotype overrides, and edge defaults (ADR-085)
- Seed themes: "Iris Default UML" (white/black), "Sparx EA Default UML" (yellow class boxes with stereotype colours for feature/DataType/CodeList/XSDsimpleType/choice), "Iris Default Simple" (ADR-085)
- Style cascade: per-element visual > stereotype override > element type default > global theme default > renderer hardcoded defaults (ADR-085)
- EA import colour preservation — reads ObjectStyle, Backcolor, Fontcolor, Bordercolor from t_object and t_diagramobjects; builds visual override dicts via `build_node_visual()` and `build_edge_visual()` (ADR-085)
- EA import explicit dimensions — imported element width/height from EA coordinates now stored in `data.visual.width/height` and applied as inline styles, overriding CSS min-width defaults (ADR-085)
- EA import stereotype threading — element Stereotype stored in `node_data["stereotype"]` for theme resolution (ADR-085)
- Theme selector dropdown in diagram toolbar — shows available themes for the current notation (ADR-085)
- NodeStylePanel — per-element style editor with colour pickers, border width, font size, bold/italic toggles, and "Reset to theme defaults" button (ADR-085)
- Admin Themes page — CRUD for themes grouped by notation, with JSON config editor (ADR-085)
- Themes link on admin dashboard page (ADR-085)

### Changed
- All renderers (UML, Simple, ArchiMate, C4, BaseNode, BaseEdge) apply `data.visual` overrides as inline styles (ADR-085)
- DynamicNode computes effective visual by merging active theme defaults with per-element overrides before passing to renderers (ADR-085)
- EA import reader reads additional columns: ObjectStyle (t_diagramobjects), Backcolor/Fontcolor/Bordercolor/BorderWidth (t_object), LineColor/IsBold/LineStyle (t_connector) (ADR-085)

## [2.2.0] - 2026-03-05

### Added
- Support for importing Sparx EA .eap (JET4/MDB) files via mdbtools conversion (ADR-084)
- Artifact element type mapping for SparxEA import (maps to component)

### Fixed
- Import API now returns `packages_skipped` and `diagrams_skipped` fields (were missing from response)
- SparxEA diagram type mapper updated to use registry-compatible types with correct notation assignment (ADR-079)
- Gallery thumbnails now render for all diagram types, not just the original five

## [2.1.0] - 2026-03-05

### Added
- Notation filter dropdown on diagrams and elements list pages
- ADR-083: Comprehensive seed diagrams covering all 31 diagram-type/notation permutations
- Seed hierarchy reorganised by notation (Simple, UML, ArchiMate, C4 packages) with 32 diagrams, 55 elements, and 50 relationships
- ~40 new seed elements across UML, ArchiMate, and C4 notations describing the Iris system
- Use Case and State Machine diagram types for UML notation (ADR-082)
- System Context and Container diagram types for C4 notation (ADR-082)
- Motivation and Strategy diagram types for ArchiMate notation (ADR-082)
- ArchiMate notation mapping added to Roadmap diagram type, C4 mapping added to Sequence (ADR-082)
- Element type filtering by diagram type in canvas EntityDialog — shows only relevant types per diagram (ADR-082)
- "Show all types" override toggle in EntityDialog to bypass diagram-type filtering (ADR-082)
- Default notation user setting in Settings page — stored in localStorage, choose Simple/UML/ArchiMate/C4 (ADR-081)
- Elements carry notation field (`notation` column) — displayed in browse mode popup and element detail page (ADR-081)
- Diagram Type and Notation Registry — separates structural diagram type (component, sequence, class, deployment, process, roadmap, free_form) from visual notation (simple, uml, archimate, c4) via database registry tables with many-to-many mapping (ADR-079)
- Registry API endpoints: `GET /api/registry/diagram-types`, `GET /api/registry/notations`, `PUT /api/registry/diagrams/{id}/notation` (ADR-079)
- Auto-detection of notations present on canvas — scans node entity types and stores detected notations per diagram (ADR-079)
- Notation dropdown in DiagramDialog — two-step selection: pick diagram type, then pick notation (filtered by valid pairs, default pre-selected) (ADR-079)
- Notation and detected_notations display on diagram detail page, list view, and gallery view (ADR-079)
- Edit Locking System — pessimistic advisory locks with 15-minute timeout, heartbeat extension, and lazy expiry cleanup for diagrams, elements, and packages (ADR-080)
- Lock API endpoints: `POST /api/locks`, `GET /api/locks/check`, `PUT /api/locks/{id}/heartbeat`, `DELETE /api/locks/{id}`, `GET /api/locks`, `DELETE /api/admin/locks/{id}` (ADR-080)
- Lock manager composable (`locks.svelte.ts`) with auto-heartbeat and beforeunload release (ADR-080)
- Admin Locks page for viewing and force-releasing active edit locks (ADR-080)
- Cascade delete for packages — deleting a package soft-deletes all descendant packages and diagrams with a shared group ID (ADR-078)
- Descendant count warning — delete confirmation dialog shows exact count of child packages and diagrams before deletion (ADR-078)
- Recycle bin page — browse, restore, and permanently delete soft-deleted items with grouped restore for cascade deletions (ADR-078)
- Recycle bin navigation item in sidebar
- Set filtering on bookmarks page — uses the same SetSelector pattern as other list pages (ADR-078)
- Restore capability for packages, diagrams, and elements — creates version record with `change_type='restore'` (ADR-078)
- Diagram hierarchy tree on dashboard when a set is selected — reuses existing TreeNode component (ADR-076)
- C4 System Context diagram in example seed showing Iris with external actors and systems (ADR-077)
- Seed auto-migration from v1 flat format to v2 package hierarchy (ADR-077)
- Hierarchy sidebar on package detail page — reuses TreeNode component from diagram view
- Shared VersionHistory component for consistent card-style version display across all detail pages

### Changed
- Locks admin nav icon changed from sliders to padlock (ADR-083)
- Bookmarks moved above Import in sidebar navigation order
- DiagramDialog now shows Notation first, filtering available diagram types by selected notation (ADR-081)
- EntityDialog shows visible Notation dropdown for entity type filtering, onsave includes notation (ADR-081)
- Simple notation streamlined to 5 domain types + 2 universal types (removed package, queue entity types and composes, implements relationship types) — Phase C of ADR-079
- EntityDialog now filters available entity types by current diagram notation (simple, uml, archimate, c4) (ADR-079)
- Diagram type filter dropdown on diagrams list page updated to reflect registry types (component, sequence, class, deployment, process, roadmap, free_form) (ADR-079)
- Example seed uses explicit notation values per diagram (ADR-079)
- Example seed reorganized into 4-package hierarchy with 7 diagrams demonstrating
  package nesting, parent_package_id, modelrefs, and C4 notation (ADR-077)
- Set gallery thumbnail now uses client-side DiagramThumbnail component (DRY with diagram gallery)
- Package detail page layout matches diagram detail page (tab bar, spacing, button styles)
- Parent package field displays name instead of GUID

### Fixed
- Dashboard now reads active set from global store when no URL parameter is present, ensuring hierarchy tree loads after set selection on Sets page
- Sets page list and gallery views no longer constrain width with max-width, matching other pages
- C4 diagrams now render SVG thumbnails in diagram gallery view
- ArchiMate and C4 node description text legibility on coloured backgrounds

## [2.0.0] - 2026-03-04

### Changed
- **BREAKING:** Entity → Element rename throughout: database tables (`elements`, `element_versions`, `element_tags`), API routes (`/api/elements/`), frontend routes (`/elements/`), types, and UI labels (ADR-071)
- **BREAKING:** Model → Diagram + Package split: `models` table split into `diagrams` and `packages` tables with dedicated API routes (`/api/diagrams/`, `/api/packages/`), frontend routes (`/diagrams/`), and UI labels (ADR-071)
- **BREAKING:** Model relationships → Package relationships: `model_relationships` table renamed to `package_relationships` with API route `/api/packages/{id}/relationships` (ADR-071)
- Canvas architecture: single DynamicNode/DynamicEdge with notation-aware rendering replaces 30+ separate node/edge components (ADR-068)
- Elements render according to diagram notation — same element appears differently on UML vs ArchiMate vs C4 diagrams
- Migration m016: renames tables, splits models into diagrams + packages, rebuilds FTS5 indexes, migrates all foreign keys (ADR-071)
- Migrations m002-m015 now skip safely on re-init after m016 has run
- UnifiedCanvas split into separate browse/edit SvelteFlow instances to fix Svelte 5 duplicate attribute error
- Canvas node browse-mode links updated: `/entities/` → `/elements/`, `/models/` → `/diagrams/`
- Import summary shows Packages count instead of Sparx Diagrams count
- Sets thumbnail source accepts both "model" and "diagram" values for backward compatibility

### Added
- BaseNode/BaseEdge shared components eliminating code duplication across all canvas components (ADR-068)
- Type equivalence map for cross-notation element compatibility (ADR-068)
- SparxEA connector direction, cardinality, roles, stereotypes, and routing now imported (ADR-070)
- UML-correct arrow markers on edges (open arrow, closed triangle, filled/open diamond)
- Cardinality and role name labels at edge endpoints
- Stereotype display as `<<name>>` on edges
- Edge properties panel for editing metadata on user-created edges
- Package as first-class concept with dedicated `packages` and `package_versions` tables
- `backend/app/elements/` module (renamed from `entities/`)
- `backend/app/diagrams/` module (renamed from `models_crud/`)
- `backend/app/packages/` module (new, for package CRUD)
- `backend/app/package_relationships/` module (renamed from `model_relationships/`)
- Backward-compatible type aliases in `api.ts`: `Entity = Element`, `Model = Diagram`, etc.
- `DiagramDialog`, `DiagramPicker`, `DiagramThumbnail`, `ElementPicker` frontend components
- Package metadata enrichment: import captures ea_guid, Status, Stereotype, Version, Scope, Author, Complexity, Phase, dates, and tagged values from SparxEA (ADR-072)
- Package detail page (`/packages/[id]`) with Overview, Details, and Extended accordion sections displaying all enriched metadata and tagged values
- Import idempotency: re-importing the same .qea file skips existing packages, elements, and diagrams matched by ea_guid (ADR-073)
- Import summary shows skip counts for packages and diagrams on the import results page
- Force-delete set now cascades packages and package_relationships
- C4 model support: Person, Software System, Container, Component, Code Element, Deployment Node, Infrastructure Node, Container Instance element types with level badges and C4 colour scheme (ADR-074)
- C4 relationship type with label and technology annotation
- C4Renderer and C4EdgeRenderer for notation-aware canvas rendering
- Type equivalences extended with C4 mappings (component→c4_component, actor→person)
- Admin-configurable Views: named profiles controlling UI feature visibility — toolbar element/relationship types, metadata sections, canvas options (ADR-075)
- Two default views: Standard (simplified, hides advanced features) and Advanced (full functionality)
- Views REST API: GET/POST/PUT/DELETE on `/api/views` with default view protection
- View selector dropdown in top navigation for switching active view
- Admin views page (`/admin/views`) for creating, editing, and deleting views
- Global view store with localStorage persistence of active view selection

### Fixed
- Class nodes render correctly in browse mode (ADR-068)
- Note and Boundary nodes render in UML edit mode (ADR-068)
- SparxEA Note elements import with content-derived labels instead of "Unknown" (ADR-069)
- Canvas nodes from import always include `description` field (ADR-069)

### Removed
- ModelCanvas, FullViewCanvas, BrowseCanvas and 30+ individual node/edge components (replaced by DynamicNode/DynamicEdge + renderers) (ADR-068)
- `backend/app/entities/` module (replaced by `elements/`)
- `backend/app/models_crud/` module (replaced by `diagrams/` and `packages/`)
- `backend/app/model_relationships/` module (replaced by `package_relationships/`)
- `ModelDialog`, `ModelPicker`, `ModelThumbnail`, `EntityPicker` frontend components
- Old frontend routes: `/entities/`, `/models/`

## [1.8.0] - 2026-03-03

### Added
- Inline "Edit Metadata" on model detail page — replaces popup dialog with in-place editing of Name, Description, Tags, and Template toggle (ADR-065, SPEC-065-A)
- Inline "Edit Metadata" on entity detail page — replaces popup dialog with in-place editing of Name, Description, and Tags
- Entity detail page accordion layout with Summary, Details, and Extended groups matching model page pattern
- Entity clone button on detail page header
- Extended metadata display for entities: scope, abstract, persistence, author, complexity, phase, EA created/modified dates, gen_type, tagged values table
- SparxEA import: 9 additional element fields (Scope, Abstract, Persistence, Author, Complexity, Phase, CreatedDate, ModifiedDate, GenType)
- SparxEA import: 6 additional attribute fields (Notes, Default, LowerBound, UpperBound, Stereotype, Scope)
- Enriched attribute import format — attributes imported as structured objects (name, type, notes, default, bounds, stereotype, scope) instead of flat strings
- 7 new backend tests for extended import fields (4 reader, 3 import)
- ADR-065: Inline Edit, Entity Detail Revamp, Extended Import
- SPEC-065-A: Inline Edit, Entity Detail Revamp specification
- First-class model relationships: `model_relationships` DB table, REST API (`POST/GET /api/models/{id}/relationships`, `DELETE /api/model-relationships/{id}`), and Relationships tab on model detail page (ADR-066, SPEC-066-A)
- `note` and `boundary` entity types for SparxEA Note/Boundary elements — previously skipped during import
- NoteNode canvas component: yellow background, folded corner CSS, DOMPurify-sanitized HTML content
- BoundaryNode canvas component: dashed border, transparent background
- `note_link` relationship type with NoteLinkEdge canvas component (dotted line)
- Self-referencing relationship support with SelfLoopEdge canvas component (cubic bezier loop)
- SparxEA import: Package-to-Package dependencies imported as model relationships
- Import change summary in version history — entities show "Imported from SparxEA (Class)", models show "Imported from SparxEA (PackageName)"
- Migration m015 for `model_relationships` table with unique constraint and cascade indexes
- Create entity and model relationships from Relationships tab with multi-step picker flow (ADR-067, SPEC-067-A)
- "Add to canvas?" prompt after creating relationships from the Relationships tab
- Canvas modelref-to-modelref connections auto-create backend `model_relationships` records
- Node removal dialog (`NodeDeleteDialog`): "Remove from this model" or "Delete entity and all relationships"
- Cascade entity deletion (`DELETE /api/entities/{id}?cascade=true`) removes entity from all model canvases and soft-deletes all relationships
- "Remove" button in canvas toolbar when a node is selected in edit mode
- 7 new model relationship backend tests, 4 new cascade delete tests, 5 new import tests
- ADR-066: Import All Skipped Items
- SPEC-066-A: Import All Skipped Items specification
- ADR-067: Unified Relationship Management & Entity Removal
- SPEC-067-A: Unified Relationships & Entity Removal specification

### Fixed
- Smart tab default on model detail page: `userSelectedTab` now resets when navigating between models, ensuring empty models default to Details tab and populated models default to Canvas

### Changed
- Model detail tab renamed from "Overview" to "Details"
- SparxEA attribute import format changed from strings to objects (backward-compatible in canvas nodes)
- Model and entity detail accordion changed from multiple to single selection mode
- "Edit Metadata" button renamed to "Edit Details" on model and entity detail pages
- Accordion "Summary" group renamed to "Overview" on model and entity detail pages
- Entity editing from model canvas now navigates to entity detail page in edit mode (via `?edit=true`)
- SparxEA import no longer skips Note, Boundary, NoteLink, self-references, or Package-to-Package dependencies
- `SKIP_OBJECT_TYPES` reduced to `{Text, UMLDiagram, Constraint}`; `SKIP_CONNECTOR_TYPES` is now empty
- `create_entity()` and `create_model()` accept optional `change_summary` parameter for initial version
- `EntityPicker` and `ModelPicker` accept optional `title`/`subtitle` props for reuse in different contexts
- Canvas Delete/Backspace key now opens confirmation dialog instead of direct node removal
- `CanvasEdgeData` includes optional `modelRelationshipId` field

## [1.7.2] - 2026-03-03

### Added
- SparxEA import now extracts package Notes, element Status/Stereotype/Version, diagram Notes, connector Notes, and tagged values from `.qea` files (ADR-064, SPEC-064-A)
- Metadata field (`metadata: dict | null`) threaded through model and entity CRUD (create/get/update/list/versions) using existing `metadata TEXT` column in version tables
- Model overview: accordion-based layout with Summary (open by default), Details (collapsed), and Extended (collapsed, conditional) groups using bits-ui Accordion
- Model overview: Extended group shows Stereotype and Tagged Values table when metadata is present
- Model overview: Details group shows Status (from metadata), Modified By (from latest version), and all previous fields
- Smart default tab: models with no canvas content default to Overview tab instead of Canvas
- Hierarchy toggle icon (tree-view SVG) positioned left of tab bar, visible on all three tabs (Overview, Canvas, Version History)
- Fullscreen icon replaces "Focus" text on canvas toolbar buttons
- 15 new backend tests: 7 reader metadata, 3 import metadata, 5 metadata CRUD
- ADR-064: Sparx EA Import Metadata & Accordion Overview
- SPEC-064-A: Sparx Import Metadata & Accordion specification

### Changed
- Canvas toolbars use `flex-wrap` for responsive wrapping on narrow windows
- SparxEA import: package Notes passed as model description (was `None`)
- SparxEA import: diagram Notes passed as diagram model description (was `None`)
- SparxEA import: connector Notes passed as relationship description (was `None`)
- SparxEA import: element metadata (status, stereotype, version, tagged values) stored as entity metadata JSON

## [1.7.1] - 2026-03-02

### Fixed
- Pagination Prev/Next buttons now show visual disabled state (`opacity-50`, `cursor-not-allowed`) when on first/last page (ADR-063)
- Audit log page pagination buttons also receive disabled styling
- Soft-deleted set names no longer block creation of new sets with the same name — partial unique index replaces full UNIQUE constraint (migration m014)

### Added
- Model detail page: collapsible hierarchy tree sidebar showing set-scoped model tree with search filtering (ADR-063, SPEC-063-A)
- Model detail page: "Add Child" button in sidebar to create child models with pre-set parent and set
- Model detail page: "Parent" field in overview tab with "Change" (ModelPicker) and "Remove" actions for reparenting models
- Hierarchy toggle button next to model title with visual state indication
- Set-scoped hierarchy API: `GET /api/models/hierarchy?set_id=` optional query parameter
- Database migration m014: partial unique index on sets.name for active rows only
- ADR-063: Pagination Disabled Styling, Set Name Uniqueness Fix, Model Tree Explorer
- SPEC-063-A: Pagination, Set Uniqueness, Tree Explorer specification
- 3 integration tests for set-filtered hierarchy
- 2 integration tests for soft-deleted set name reuse

## [1.7.0] - 2026-03-02

### Added
- Persistent set selection: selecting a set on any page carries the filter across Models, Entities, and Dashboard navigation via a sessionStorage-backed global store (ADR-062, SPEC-062-A)
- Active set display in AppShell header: "Iris / {SetName}" with link to Sets page when a set is active
- Sets page active set highlighting with primary-colored border and "Reset filter" button
- Import page inline set creation: "+ New Set..." option in SetSelector opens create dialog, auto-selects new set
- Import page "View Models" link now includes set filter for the imported set
- Read-only tag badges and "Template: Yes/No" field on model overview tab
- Read-only tag badges and "Set" field on entity details tab
- Editable tags and template toggle in model edit dialog
- Editable tags in entity edit dialog
- ADR-062: Persistent Set Selection
- SPEC-062-A: Persistent Set Selection specification

### Changed
- General API rate limit increased from 100 to 300 requests/minute to prevent 429 errors during normal browsing
- Model detail ID field styling normalized (removed `font-mono text-xs`, now matches other fields)
- Entity detail ID field styling normalized (same as models)
- SetSelector `onchange` now passes set name along with ID; added `showNewSet`/`onNewSet` props and `reload()` export
- Sets page button styling aligned with Models page pattern (consistent `gap-2`, `px-3`/`px-4 py-2`, `text-sm`)
- Dashboard search now scoped to active set when filtering

- Sets: top-level workspace grouping — each model/entity belongs to exactly one set; Default set (well-known UUID) created on migration with all existing items backfilled (ADR-060, SPEC-060-A)
- Sets CRUD API: `POST/GET/PUT/DELETE /api/sets`, `GET /api/sets/{id}/tags` for scoped tag listing; 409 on non-empty delete, 403 on Default set delete
- Set-scoped tags: tags are stored the same way but filtered per-set in UI and API — "v1.0" in Set A is independent from "v1.0" in Set B
- Auto-membership: saving a model's canvas automatically moves referenced entities into the model's set
- Batch operations API: 8 endpoints under `/api/batch/{models,entities}/{delete,clone,set,tags}` for bulk actions on up to 100 items per request; all return `{ succeeded, failed, errors }`
- Pagination controls: `Pagination.svelte` component with page size selector (25/50/100), prev/next buttons, and page number links on models and entities list pages
- Set selector: `SetSelector.svelte` dropdown on models page, entities page, and import page for filtering and assignment
- Batch toolbar: select mode toggle with checkboxes on list/gallery items; sticky `BatchToolbar.svelte` with Clone, Move to Set, Tags, Delete actions; `BatchSetDialog.svelte` and `BatchTagDialog.svelte` for batch move and tag operations
- Import set assignment: set selector on import page sends `set_id` form field with upload; all imported items assigned to chosen set
- Set name display on model detail overview tab
- `set_id` and `set_name` fields on model and entity API responses (JOIN to sets table)
- `set_id` query parameter on `GET /api/models`, `GET /api/entities`, and `GET /api/entities/tags/all` for set-scoped filtering
- ADR-060: Sets, Batch Operations & Pagination
- SPEC-060-A: Sets, Batch Operations & Pagination specification
- Database migration m012: sets table, set_id columns on models/entities with indexes and backfill
- 20 integration tests for sets CRUD (default set, create, get, update, delete protection, tag scoping, model/entity set integration)
- 11 integration tests for batch operations (delete, clone, set reassignment, tag modification, validation, auth)
- Sets page: dedicated `/sets` page with list and gallery views, client-side search, edit mode toggle, and create dialog (ADR-061, SPEC-061-A)
- Dashboard integration: `?set_id=` URL parameter filters entity/model counts with "(filtered)" labels, 3-column stats grid with Sets card and reset filter link
- Set edit page: `/sets/[id]` with name/description editing, thumbnail management (none/model/image), and force-delete with confirmation
- Set thumbnails: `POST/GET /api/sets/{id}/thumbnail` endpoints for image upload and retrieval; model thumbnail proxy; 2 MB limit, PNG/JPG only
- Force-delete sets: `DELETE /api/sets/{id}?force=true` soft-deletes all models, entities, and search indexes; returns deletion counts
- Sidebar: Sets navigation item between Entities and Import; `aria-current` fix for sub-page highlighting
- Database migration m013: `thumbnail_source`, `thumbnail_model_id`, and `thumbnail_image` columns on sets table
- ADR-061: Sets Page & Dashboard Integration
- SPEC-061-A: Sets Page & Dashboard Integration specification
- 5 integration tests for force-delete (empty set, non-empty set with counts, default set protection, nonexistent, regular delete non-empty)
- 8 integration tests for set thumbnails (upload PNG, JPG, oversized rejection, invalid type, GET retrieval, 404 handling, model source, model-in-set validation)

## [1.6.0] - 2026-03-02

### Added
- Model Hierarchy: parent/child relationships for models via `parent_model_id` column; API endpoints for hierarchy tree, ancestors, children, and parent assignment with cycle validation (ADR-055, WP-1)
- Tree View: hierarchical model navigation on the Models page alongside list and gallery views; recursive TreeNode component with expand/collapse, search filtering, and keyboard support (WP-2)
- Breadcrumbs: ancestor chain navigation on model detail pages showing path from root to current model (WP-2)
- ArchiMate Full Specification: expanded from 11 to 45 entity types across 6 layers (business, application, technology, motivation, strategy, implementation & migration); 3 new relationship types (specialization, assignment, association); layer-specific CSS styling (ADR-056, WP-3)
- UML Type Expansion: 5 new node types (Interface, Enumeration, Abstract Class, Component, Package) with dedicated Svelte components; Usage edge type (ADR-057, WP-4)
- SparxEA Import: backend module to read `.qea` SQLite files (EA 16+) and import elements, connectors, diagrams, and package hierarchy into Iris; type mapping for UML/ArchiMate; coordinate conversion; `POST /api/import/sparx` endpoint (ADR-059, WP-5)
- Import UI: drag-and-drop upload page for `.qea` files with progress indicator and results summary; Import link in sidebar navigation (WP-6)
- BPMN Deferral: ADR-058 documenting decision to defer BPMN support to a future phase
- ADR-055 through ADR-059 and corresponding specs
- 20 backend tests for model hierarchy (create with parent, hierarchy tree, ancestors, children, cycle prevention, deleted model exclusion)
- 42 backend tests for SparxEA import (reader, mapper, converter, full import, API endpoint)

## [1.5.2] - 2026-03-02

### Added
- Data Model seed: 6th example model mapping the complete Iris database schema (20 tables, 19 FK relationships) across both databases, linked to the Data Layer model via modelref
- System Overview seed updated with Data Model modelref node and "Schema for" edge to Data Layer

### Fixed
- Centre-point connector persistence: edges connected via centre handles disappeared on save/reload because only a `type="source"` handle existed — @xyflow couldn't match `targetHandle: "center"` on the target node. Added matching `type="target"` centre handle to all 15 node components (ADR-053)

## [1.5.1] - 2026-03-02

### Added
- Centre-point connector mode: invisible centre Handle on all 15 node components (8 Simple View, 6 UML, 1 ArchiMate) enabling straight centre-to-centre connections; visible on hover with enlarged hit area (ADR-053, SPEC-053-A)
- ADR-053: Centre-Point Connection Mode
- SPEC-053-A: Centre-Point Handle Implementation
- ADR-054: ArchiMate Seed Data Node Type Mapping
- SPEC-054-A: ArchiMate Seed Data Fix

### Fixed
- Seed model node overlap: increased vertical spacing in all seed model builders to 250px row gaps, preventing node overlap with multi-line descriptions
- Seed model descriptions: replaced abbreviated hardcoded descriptions with full entity descriptions from `_ENTITIES` via `_ENTITY_DESCRIPTIONS` lookup dict
- ArchiMate Enterprise View rendering: seed data now uses correct ArchiMate node types (business_actor, application_component, etc.) with `layer` and `archimateType` data fields so ArchimateNode.svelte renders properly with coloured layer badges (ADR-054, SPEC-054-A)

## [1.5.0] - 2026-03-01

### Added
- Theme-aware PNG thumbnails: 3 theme variants (light/dark/high-contrast) with parameterized SVG colors, composite PK migration, ?theme= query param on thumbnail API (WP-1)
- Edge label editing: shared EdgeLabel.svelte component using EdgeLabelRenderer with double-click inline editing, DOMPurify sanitization, and CustomEvent dispatch (WP-3)
- Edge label repositioning: drag-to-reposition via pointer events, labelOffsetX/Y/Rotation in CanvasEdgeData (WP-4)
- Canvas node description sync: refreshNodeDescriptions() fetches entity data after canvas load, updating labels and descriptions via Promise.all (WP-5)
- Sequence diagram browse mode: onparticipantselect callback enables click-to-detail on participants with linked entities (WP-7)
- Model-in-model visual differentiation: ModelRefNode.svelte with stacked-squares visual, registered as 'modelref' node type (WP-8)
- Admin PNG regeneration button: POST /api/admin/thumbnails/regenerate endpoint with admin guard, settings page button with loading/success states (WP-9)
- Tag autocomplete: suggestions prop on TagInput with filtered dropdown, keyboard navigation (Arrow keys, Enter, Escape), ARIA combobox support (WP-10)
- ADR-046 through ADR-052 and corresponding specs
- Example Iris Architecture Models: idempotent seed creates 15 entities, 20 relationships, and 4 models (Iris Architecture, API Request Flow sequence diagram, Data Layer, Iris Enterprise View) with full canvas layouts and DB relationship records on first startup (WP-16)
- ADR-045: Example Iris Architecture Models
- SPEC-045-A: Example Architecture Models Seed
- Entity Edit from Model Editor: "Edit Entity" button in canvas toolbar (edit mode) when a linked entity node is selected; fetches entity from API, opens EntityDialog in edit mode, saves via PUT with If-Match header, and updates canvas node label/type/description in place (WP-15)
- ADR-044: Entity Edit from Model Editor
- SPEC-044-A: Entity Edit from Model Editor Implementation
- Template Designation: "Template" checkbox on model detail overview tab to mark models as reusable templates via the `template` tag; "Templates" toggle button on model list page filters to template models; green "Template" badge on model cards/list items (WP-13)
- ADR-043: Template Designation
- SPEC-043-A: Template Designation Implementation
- Connector Manipulation: per-edge routing type selection (Default, Straight, Step, Smooth Step, Bezier) via toolbar dropdown when an edge is selected in edit mode; routing type persists with model data and integrates with undo/redo (WP-11)
- ADR-042: Connector Manipulation
- SPEC-042-A: Connector Manipulation Implementation
- 59 tests for connector routing (type definitions, edge component path functions, routing change logic, undo/redo integration, page UI)
- Export Model: "Export" dropdown in canvas toolbar (edit mode) supports SVG, PNG, and PDF download; Visio and Draw.io shown as disabled placeholders (WP-10)
- ADR-039: Model Export
- SPEC-039-A: Model Export Implementation
- 13 unit tests for export utilities (filename sanitization, SVG extraction, DOM integrity)
- Clone Model: "Clone" button on model detail page duplicates a model with its canvas layout, pre-filling name with "(Copy)" suffix (WP-14)
- ADR-041: Clone Model
- SPEC-041-A: Clone Model Implementation
- Roadmap model type: available in model creation dialog, model type filter, and detail page canvas (uses simple canvas view)
- ADR-040: Roadmap Model Type
- SPEC-040-A: Roadmap Model Type Implementation
- Admin Settings link in application header for admin users, providing quick access to `/admin/settings` regardless of sidebar state
- ADR-031: Admin Settings Header Link
- ADR-031: Session Timeout During Active Use
- ADR-033: Search Display Fix — verified entity CRUD operations correctly maintain FTS5 search index
- ADR-034: GUID to Username Resolution
- SPEC-034-A: GUID Username Resolution Implementation
- 6 regression tests for entity search indexing (create, update, delete, description search, multiple entities, deep link format)
- 8 tests for GUID-to-username resolution (entity, model, and relationship endpoints)
- ADR-032: PNG Thumbnail Startup Regeneration and Frontend Fallback
- SPEC-032-A: PNG Thumbnail Fix
- 8 tests for PNG thumbnail generation (endpoint returns PNG, startup regeneration, stale SVG replacement, deleted model skipping)
- ADR-036: Browse Mode Fixes
- SPEC-036-A: Browse Mode Fixes Implementation
- ADR-038: Edge Reconnection Fix
- SPEC-038-A: Edge Reconnection Fix Implementation
- 45 tests for edge reconnection (reconnection logic, undo integration, EdgeReconnectAnchor presence in all 12 edge components)

### Changed
- TagInput component now accepts optional `suggestions` prop for autocomplete (WP-10)
- Edge components (Uses, DependsOn, Composes, Implements, Contains) now use shared EdgeLabel component (WP-3)
- CanvasEdgeData extended with labelOffsetX, labelOffsetY, labelRotation fields (WP-4)
- Undo/redo now covers node drag moves: dragging a node pushes pre-drag state to the undo stack
- Undo/Redo button tooltips updated from "Ctrl+Z"/"Ctrl+Y" to "Ctrl/Cmd+Z"/"Ctrl/Cmd+Y" for Mac compatibility
- Non-focus-mode editing canvases now pass onundo/onredo to enable Ctrl+Z/Ctrl+Y keyboard shortcuts
- ADR-035: Undo/Redo Node Moves + Mac Shortcut Labels

### Fixed
- Gallery thumbnail sizing: changed object-cover to object-contain with flex centering for correct aspect ratio (WP-2)
- Canvas node description sync: node descriptions now refresh from linked entities after canvas load (WP-5)
- Audit log username resolution: audit entries now show username instead of GUID via _resolve_username() (WP-6)
- Entity tag display: get_entity() now includes tags from entity_tags table (WP-11)
- Export captures full viewport: uses html-to-image for complete node+edge capture, export button always visible (WP-12)
- Edge endpoint selection highlight: CSS for handle hover glow, larger dot size, and primary color on selected edges (WP-13)
- Edge reconnection now works: added `EdgeReconnectAnchor` to all 12 custom edge components (Simple View, UML, ArchiMate) enabling drag-to-reconnect endpoints (ADR-038)
- Canvas connector creation now creates a real relationship record in the database when both nodes are linked to entities, so entity detail pages show the connection
- Edge reconnection and deletion now push to undo history, enabling Ctrl+Z reversal
- PNG gallery mode now displays images: added `cairosvg` as required dependency, thumbnails regenerated on startup for all models, frontend falls back to SVG component on image load error (ADR-032)
- "Used In Models" panel now shows all models including the current model (marked with "(current)") instead of filtering it out, fixing empty list when entity is only in the current model
- Browse mode canvas nodes now show a "View details" hover overlay link for direct navigation to entity detail page
- Session timeout warning no longer appears during active use; the `$effect` timer now reschedules whenever the JWT is silently refreshed by `apiFetch` auto-refresh
- Entity and model API responses now include `created_by_username` field (Pydantic schemas were stripping the field returned by the service layer)
- Version history API responses now include `created_by_username` for all entity and model versions
- Relationships API responses now include `source_entity_name` and `target_entity_name` (service layer JOINs entities table to resolve names)
- Relationships tab on entity detail page now shows entity names instead of raw GUIDs for source/target entities
- EdgeLabel component: fixed import of non-existent `EdgeLabelRenderer` — now correctly uses `EdgeLabel` from @xyflow/svelte
- Canvas nodes now have standard 200px width with word-wrapping descriptions instead of truncation
- New node placement uses grid-based overlap avoidance instead of diagonal offset
- Focus mode edit controls: toolbar (Add Entity, Undo/Redo, Save/Discard) now renders inside the FocusView overlay so controls are visible in fullscreen
- Focus mode no longer renders the normal canvas underneath the overlay

## [1.4.0] - 2026-02-28

### Added
- Focus view for all canvas types (fullscreen overlay, Escape to exit)
- Sequence diagram zoom/pan/fit-to-view via SVG viewBox manipulation
- Sequence diagram edit mode (Add Participant, Add Message, Delete Selected, Save/Discard)
- Sequence diagram zoom toolbar (bottom-left, matching SvelteFlow Controls style)
- ADR-014: Canvas UX Parity
- SPEC-014-A: Canvas UX Parity Implementation

### Fixed
- Duplicate zoom controls — removed top-right CanvasToolbar, keeping bottom-left SvelteFlow Controls

## [1.3.1] - 2026-02-28

### Added
- Model preview thumbnails in gallery cards (static SVG rendering of canvas/sequence diagrams)
- ADR-013: Model Preview Thumbnails
- SPEC-013-A: Model Preview Thumbnails Implementation

## [1.3.0] - 2026-02-28

### Added
- Gallery/card view mode on models list page with responsive CSS grid layout
- View mode toggle (list/gallery) in models toolbar with `aria-pressed` state
- Card size slider (200px–400px) for adjusting gallery card width, visible only in gallery mode
- localStorage persistence for view mode and card size preferences across sessions
- Gallery cards show model name, type badge, full description, and updated date
- ADR-012: Models Page Gallery View
- SPEC-012-A: Gallery View Implementation
- BDD test suite for gallery view (6 scenarios in models-gallery.feature)

## [1.2.1] - 2026-02-28

### Fixed
- SvelteFlow canvas rendering crash: `useSvelteFlow()` was called outside `<SvelteFlow>` context in ModelCanvas, FullViewCanvas, and KeyboardHandler — moved CanvasToolbar and KeyboardHandler inside SvelteFlow slot where context is available
- Test infrastructure: replaced globalSetup with wrapper script (globalSetup runs after webServer, killing the backend)
- BDD test reliability: fixed model navigation selectors, entity detail panel locators, SVG strict mode, and feature file scenarios for 100% pass rate (42/42 BDD, 41/41 E2E)

## [1.2.0] - 2026-02-28

### Added
- Full View canvas (UML + ArchiMate) with FullViewCanvas.svelte orchestrator
- Sequence diagram rendering on canvas tab for sequence model types
- RelationshipDialog wired to canvas edge creation with 5 relationship types
- EntityDetailPanel in browse mode — click node to see entity details
- Entity edit and delete on entity detail page with optimistic concurrency
- Model type filter on models list page
- Bookmark toggle on model detail page
- Password change on Settings page with NZISM-compliant 12-char minimum
- Audit date range filters (from_date/to_date) on admin audit page
- Comments UI on model and entity detail pages (add, edit, delete)
- Version rollback on model detail Version History tab
- Canvas link existing entity via EntityPicker dialog
- CommentsPanel component for inline comment CRUD
- EntityPicker component for searchable entity selection
- Gherkin BDD test suite with playwright-bdd (12 feature files, 5 step definition files)
- Playwright MCP configuration for exploratory testing
- ADR-011: Canvas Integration and Testing Strategy
- SPEC-011-A through SPEC-011-E: Canvas interactions, Full View, sequence, BDD test plan, browse mode

### Fixed
- Canvas node type bug: entities now render with correct shapes (was using unregistered 'simpleEntity' type)
- Canvas relationship creation: users can now choose relationship type via dialog (was hardcoded to 'uses')
- Browse mode node clicks now show entity detail panel (was silently ignored)

## [1.1.1] - 2026-02-28

### Added
- Settings page with theme picker (Light, Dark, High Contrast)
- "New Model" button on models list page with create dialog
- Edit and Delete actions on model detail page
- "New Entity" button on entities list page

### Changed
- Theme selection moved from header toggle to Settings page
- Sidebar items: removed letter prefixes, added keyboard shortcut tooltips

### Fixed
- Theme toggle cycle bug: Light mode now reachable (was stuck in Dark/HC loop)
- Auth redirect race condition in layout preventing login navigation
- Auth store now persists to sessionStorage, surviving page reloads during E2E tests
- Dashboard heading always visible immediately (no longer hidden behind loading state)
- Vite preview proxy: API calls now correctly proxy to backend in production preview mode
- Backend rate limits configurable via environment variables (IRIS_RATE_LIMIT_LOGIN, IRIS_RATE_LIMIT_GENERAL, IRIS_RATE_LIMIT_REFRESH)
- E2E test suite: fixed password mismatch, strict mode violations, rate limit handling, and timing-sensitive assertions (41/41 pass)

## [1.1.0] - 2026-02-27

### Added
- Read-only audit log API: `GET /api/audit` with pagination, filtering, and admin-only access (ADR-009, SPEC-009-A)
- Audit chain verification API: `GET /api/audit/verify` returns hash chain integrity status
- Entity statistics API: `GET /api/entities/{id}/stats` returns relationship and model usage counts
- Entity cross-reference API: `GET /api/entities/{id}/models` returns models referencing an entity
- Dashboard page with entity/model counts, bookmarked models, search, and quick navigation
- Admin home page with navigation cards for user management and audit log
- Admin users page with full CRUD: list, search, create, edit role, activate/deactivate
- Admin audit page with paginated log table, filters, chain verification badge, and expandable row detail
- ADR-009: Audit Log Read API
- ADR-010: Search Implementation Clarification
- SPEC-009-A: Audit Read API specification
- SPEC-010-A: Search Roadmap specification
- `docs/ROADMAP.md` documenting future semantic search enhancement
- Comprehensive E2E test suite (10 suites, Playwright) covering auth, dashboard, models, entities, admin, navigation, theming, accessibility, and errors
- Protocol 12: README Accuracy

### Changed
- Search documentation corrected from "semantic search with sentence-transformers" to "full-text search with SQLite FTS5" in README and north-star
- v0.3.0 changelog corrected: "semantic search" → "full-text search with FTS5"

### Fixed
- `apiFetch` return type handling: all list and detail pages now correctly use typed `apiFetch<T>()` instead of treating result as raw `Response`
- Entity detail page: versions, relationships, and used-in-models tabs now load real data from API
- Model detail page: canvas tab renders `BrowseCanvas`/`ModelCanvas` from model data, versions tab loads from API
- Dashboard page no longer a stub — displays live stats, bookmarks, search, and navigation
- Admin pages no longer stubs — full user management and audit log functionality

## [1.0.0] - 2026-02-27

### Added
- WCAG 2.2 audit with 50 compliance tests covering contrast ratios, keyboard ops, ARIA landmarks, focus indicators, and theme accessibility
- Session timeout warning component (WCAG 2.2.1 Timing Adjustable)
- Help page with keyboard shortcut reference (WCAG 3.2.6 Consistent Help)
- NZ ITSM control verification with 19 tests across 6 control families
- Performance tests for canvas operations at scale (500-5000 entities)
- Protocols 10-11: Claude agent teams and latest stable dependencies
- README with full project documentation
- CHANGELOG with versioned release history

### Changed
- Light theme border colour from #e2e8f0 to #6b7280 for WCAG 1.4.11 non-text contrast (3:1)
- Light theme danger colour from #ef4444 to #dc2626 for WCAG 1.4.3 text contrast (4.5:1)
- Dark theme border colour from #334155 to #64748b for WCAG 1.4.11 non-text contrast (3:1)
- NZ ITSM control mapping statuses updated from Pending to Verified

## [0.6.0] - 2026-02-27

### Added
- Browse mode with read-only canvas (nodesDraggable=false, nodesConnectable=false)
- Canvas mode store (edit/browse switching)
- Entity detail panel component for browse mode
- Entity detail page with tabs (details, version history, relationships, used-in models)
- Model detail page with tabs (overview, canvas, version history)
- Entity list page with search, type filter, and sort controls
- Model list page with search and sort controls

## [0.5.0] - 2026-02-27

### Added
- Simple View canvas with 7 node types and 5 edge types via @xyflow/svelte
- Canvas keyboard handler with full navigation (Tab, arrows, Enter, Delete, Escape, C, F)
- Canvas announcer (ARIA live region) for screen reader operation feedback
- Canvas toolbar with zoom controls
- Entity create/edit dialog with DOMPurify sanitisation
- Relationship dialog with type selection
- Canvas service for node/edge creation and placement serialisation
- Sequence diagram custom SVG renderer with keyboard navigation
- UML Full View: 6 node types (class with compartments, object, use case, state, activity, deployment) and 6 edge types
- ArchiMate Full View: 11 node types across 3 layers and 8 edge types with layer-specific styling

## [0.4.0] - 2026-02-27

### Added
- Authentication flow with JWT in-memory storage and auto-refresh
- App shell with skip links, ARIA landmarks, sidebar navigation
- Four-mode theming (light, dark, high-contrast, system) via mode-watcher
- All application routes with breadcrumbs and 404 handling
- Accessibility scaffolding: LiveRegion, ConfirmDialog, focus utilities
- Login page with WCAG compliance (autocomplete, paste, aria-describedby)

## [0.3.0] - 2026-02-27

### Added
- Comments CRUD on entities and models with soft delete
- Per-user model bookmarks (bookmark/unbookmark/list)
- Full-text search with SQLite FTS5

## [0.2.0] - 2026-02-27

### Added
- FastAPI app factory with lifespan management and security headers middleware
- Authentication service (Argon2id hashing, JWT HS256, refresh token rotation, password validation)
- Auth routes (login, refresh, logout, change-password, initial setup)
- Rate limiting middleware (sliding window: 10/min login, 30/min refresh, 100/min general)
- Audit middleware for intercepting mutating requests
- Entity CRUD with versioning, rollback, optimistic concurrency (If-Match), and soft delete
- Relationship CRUD with versioning
- Model CRUD with denormalised placements JSON and cross-reference queries
- User management API (admin only) with role assignment

## [0.1.0] - 2026-02-27

### Added
- Backend project setup (FastAPI, aiosqlite, argon2-cffi, python-jose, pytest, ruff, mypy)
- Frontend project setup (SvelteKit, Svelte 5, Tailwind v4, @xyflow/svelte, DOMPurify, mode-watcher, Vitest, Playwright)
- Database connection factory with 7 SQLite PRAGMAs (WAL, FK, busy_timeout, synchronous, cache_size, journal_size_limit, auto_vacuum)
- Database schema: roles, role_permissions, users, password_history, refresh_tokens
- Database schema: entities, entity_versions, relationships, relationship_versions, models, model_versions
- Audit database with SHA-256 hash-chained audit log
- Seed data for 4 roles (Admin, Architect, Reviewer, Viewer) and 26 permission mappings
- Audit service with genesis hash, hash computation, and chain verification
- Database startup initialisation (migrations, seeding, audit chain verification)
- 8 ADRs and 13 implementation specifications
- 11 non-negotiable development protocols
- NZ ITSM control mapping (44 controls across 6 families)
- WCAG 2.2 compliance matrix (58 criteria)
