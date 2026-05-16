# Plan: Dynamic List notation/diagram type (issue #147)

## Context

Issue #147 asks for a new diagram type called **dynamic list**, modelled
on the existing `text` diagram type (the markdown-content surface added in
m044). It auto-renders a bullet-point list and is *not* editable in the
content-canvas sense — the content is computed from other Iris data on
every view. Export produces a normal markdown file.

The latest comment on #147 (2026-05-16) links it to issue #149 and
clarifies two modes:

1. **Default mode** — list every relationship whose **source and target
   elements both belong to the current diagram** ("intra-diagram"
   relationships only). Confirmed via plan-time question.
2. **Alternative (package) mode** — list every element that belongs to a
   given package. Depends on issue #149, which introduces a first-class
   `element.package_id` column. Plans are independent but #147's
   package-mode rendering is gated on #149 being shipped first.

Recon findings that shape the plan:

| Area | Today |
|---|---|
| Notation registry | `notations` and `diagram_types` tables seeded by m020 + m027 + m043 + m044 (text). Each row carries `name`, `display_name`, `description`, `display_order`. Mapping table joins `notations` ↔ `diagram_types` with an `is_default` flag (m044). |
| Text-type rendering | `frontend/src/lib/canvas/text/TextCanvas.svelte` — single textarea in edit mode, `<MarkdownView>` in browse mode. Mode toggled by an `editing` prop owned by the parent (`/views/[id]/+page.svelte`). |
| Element relationships | `relationships` table (m002, columns renamed in m016 to `source_element_id` / `target_element_id`). Endpoints both reference `elements(id)`; no `diagram_id` on the row, no list-by-diagram service method. |
| Diagram-scoped relationship query | Already partially built: `GET /api/diagrams/{id}/relationships` returns `{diagram_relationships, element_relationships}` (used by the `/view` Relationships tab, line 795 of `/views/[id]/+page.svelte`). `element_relationships` are computed as "relationships where both endpoints are elements drawn on this diagram" — exactly the intra-diagram scope we need. **Reuse this endpoint; do not invent a new one.** |
| Element → package | Does not exist today. Issue #149 introduces `element.package_id`. #147 package-mode reads it. |
| Export pipeline | `backend/app/export/router.py::_diagram_to_markdown` (lines 217–233) special-cases `notation == "markdown"` and returns `data.content` verbatim. For dynamic list this won't work — content must be computed at export time from the data sources, not stored. |
| Read-only / auto-generated precedent | None today. We need a small mechanism to suppress textarea editing in the canvas while still allowing the standard "edit" button to expose a source-config dialog. |
| Diagram creation UI | `frontend/src/lib/components/DiagramDialog.svelte` — hardcoded fallback notation/diagram-type list (lines 53–101), registry-driven primary path via `/api/registry/diagram-types`. |

The user's chosen UX for mode-switching (plan-time AskUserQuestion answer):
> use the standard 'edit' button, however we can't change the canvas
> content like other diagram types, but we do have a button in edit mode
> that allows us to change [...] default to package mode, and then to
> navigate iris (within the current set) to find and select the package.

So the canvas itself is read-only, but the existing edit-mode chrome
hosts a small "Source" panel with two controls: mode (default / package)
and, when package mode is selected, a package picker scoped to the
current set.

## Decisions

| # | Decision |
|---|---|
| 1 | **Notation + diagram_type registration**: introduce a new diagram_type `dynamic_list` under the existing `markdown` notation (created in m044). Reuse that notation — it already groups "markdown-backed read surfaces" (`text` lives there). New diagram_type display_name `"Dynamic List"`, display_order 16 (text is 15). Seeded in a new migration `m066_dynamic_list_diagram_type.py` (next free migration number — verify at write time). |
| 2 | **Source-of-truth lives in `data` JSON, not new columns.** Two keys: `data.dynamic_source.mode` (`"diagram_relationships"` \| `"package_elements"`) and `data.dynamic_source.package_id` (string, optional, set only when mode is `package_elements`). Default at creation: `{mode: "diagram_relationships"}`. No schema change to `diagrams` or `elements`. Picked over a new column because the source config is type-specific to dynamic_list and the existing `data` JSON is the established home for type-specific config (per ADR-076 / existing diagram patterns). |
| 3 | **Canvas component is a thin subclass of TextCanvas.** New file `frontend/src/lib/canvas/text/DynamicListCanvas.svelte`. Browse mode renders `<MarkdownView>` of the computed bullet-list (received as a `content` prop, exactly like TextCanvas). Edit mode renders a non-editable preview (no textarea) plus a "Source" panel with the mode toggle + package picker. DRY: the bullet-rendering and TOC paths in TextCanvas are reused unchanged by extracting the shared markdown-render block into `TextMarkdownView.svelte` (today inlined in TextCanvas). |
| 4 | **Computation lives on the backend, not the frontend.** A new service method `compute_dynamic_list_content(db, diagram_id) -> str` in `backend/app/diagrams/dynamic_list.py` reads `data.dynamic_source` and: for `diagram_relationships`, calls the existing intra-diagram list code in `app/diagrams/service.py` that backs `GET /api/diagrams/{id}/relationships` (refactor into a shared helper if it's currently inlined); for `package_elements`, calls `app/packages/service.py::list_package_elements()` (a new helper added by #149 — gated). Backend is chosen over frontend so export and MCP `render_diagram` get the same content as the browser without duplicating logic — protocols §13 (DRY). |
| 5 | **Two integration paths return the same content.** (a) `GET /api/diagrams/{id}` returns `data.content` populated at read-time for `diagram_type == "dynamic_list"` (set in the existing diagram-read service hook). The on-disk row never stores content — the response synthesises it. (b) Export pipeline (`_diagram_to_markdown`) sees the synthesised `data.content` already on the bundle (because the bundle reader runs through the same service path) and returns it verbatim — zero changes to export router. Verified path: m044's text export already takes `data.content`; we just need to ensure the bundle reader populates it for `dynamic_list` like it does for `markdown`. |
| 6 | **Markdown shape**. Default mode: each bullet is `- **{source.name}** *{relationship_type}* **{target.name}**` followed by an optional `> {label}` blockquote line if `label` is set. Package mode: each bullet is `- **{element.name}**` followed by `: {element.description}` on the same line if a description exists. Stable ordering: relationships sorted by `(source.name, target.name, relationship_type)`; package elements by `(name)`. Top-of-file H1 `# {diagram.name}` + a one-line H6 footer noting `(Dynamic list — auto-generated)`. |
| 7 | **Edit mode UX**. The /view page's existing edit chrome (toolbar with Save / Cancel) appears but the textarea is replaced by (a) a non-editable rendered preview, (b) a "Source" `<details>` panel below the preview with: a `<select>` for mode and, when `package_elements`, a `PackagePicker` constrained to the current diagram's set. "Save" persists `data.dynamic_source` only; canvas content is never saved. "Cancel" discards source changes. Reuses `PackagePicker.svelte` (already in `frontend/src/lib/components/` per #149 recon). |
| 8 | **Read-only canvas mechanism**: a new boolean `data.is_content_locked: true` (synthesised in the response, not stored) emitted by the backend on read for any dynamic_list diagram. The /view page's "Edit" / "Save" wiring already exists; `is_content_locked` only hides the textarea and shows the Source panel instead. No new diagram-level read-only column — keeps the model additive and avoids cross-cutting schema changes. |
| 9 | **MCP / CLI surface**. No new MCP tool, no new CLI subcommand — the diagram type uses the existing `create_diagram` / `update_diagram` machinery (mode + package_id set via the `data` payload). MCP's `render_diagram` path already returns markdown for `markdown`-notation diagrams via the export service; once decision #5 ships, dynamic_list "just works". `scripts/check_surface_parity.py` requires no exception — there's no new write verb. |
| 10 | **TDD ordering (protocols §3)**: SPEC's acceptance criteria → pytest fixture (seed a diagram with two elements + one relationship, compute, assert markdown) → service implementation. Then a separate test for package mode (seed a package with two elements via the #149 path — skipped until #149 lands). Frontend: Playwright e2e creating a dynamic_list diagram in browse mode, asserting bullets render. |
| 11 | **Dependency on #149**: package mode is feature-gated behind a single check — if `element.package_id` column does not exist (DB inspector), the Source panel's "Package" option is disabled with a tooltip "Requires Iris ≥ vX.Y.Z (issue #149)". Plan #147 ships *first* with only default mode active, then a follow-up commit enables the package-mode branch after #149 merges. Order chosen so #147 isn't blocked by #149 review. |
| 12 | **Versioning**: ship as v6.7.0 (minor bump — new diagram type is user-visible). Per `feedback_release_workflow`, publish a GitHub release on the version bump. Update CHANGELOG `[Unreleased]` → `[6.7.0]`, README diagram-types section, and the `mcp/README.md` note if any. |
| 13 | **DRY check (protocols §13)**: extract the intra-diagram relationship query in `backend/app/diagrams/service.py` (currently inlined inside the `GET /diagrams/{id}/relationships` handler) into a service helper `list_intra_diagram_relationships(db, diagram_id)` reused by both the existing endpoint and the new dynamic-list computer. |
| 14 | **No `auto_generated` flag in the registry** — diagram_type-level metadata stays as it is. The "auto-generated" behaviour is purely a property of the *diagram_type's compute path*, not a column users can flip on arbitrary diagrams. Avoids a meta-column that would need policy decisions across every other diagram_type. |

## ADRs to create

| ADR | Title | Phase |
|-----|-------|-------|
| ADR-184 | Dynamic List diagram type — auto-generated markdown surface | single-phase |
| ADR-185 | Synthesised `data.content` for compute-on-read diagram types | single-phase |

(ADR-185 is split out because the "synthesise content at read-time and let export pick it up unchanged" pattern is reusable for future computed types and deserves its own decision record.)

## Specs to create

- `SPEC-184-A-Dynamic-List-Diagram-Type.md` — registry seed, `data.dynamic_source` schema, markdown shape rules, ordering, edit-mode UX, TDD acceptance criteria, dependency on #149.
- `SPEC-185-A-Synthesised-Content-On-Read.md` — service-layer hook signature, response shape (`data.content`, `data.is_content_locked`), and the export pipeline contract (export must not duplicate the compute path).

## Files

### Create

- `docs/adrs/ADR-184-Dynamic-List-Diagram-Type.md`
- `docs/adrs/ADR-185-Synthesised-Content-On-Read.md`
- `docs/adrs/specs/SPEC-184-A-Dynamic-List-Diagram-Type.md`
- `docs/adrs/specs/SPEC-185-A-Synthesised-Content-On-Read.md`
- `backend/app/migrations/m066_dynamic_list_diagram_type.py` — seed the new `dynamic_list` diagram_type row + (markdown, dynamic_list) mapping with `is_default=0`.
- `backend/app/diagrams/dynamic_list.py` — `compute_dynamic_list_content(db, diagram_id) -> str` plus the two source-mode helpers. Imports the new `list_intra_diagram_relationships` helper.
- `backend/tests/test_dynamic_list_compute.py` — fixture-driven tests for both modes (package mode marked `pytest.mark.skipif` until #149 lands).
- `frontend/src/lib/canvas/text/DynamicListCanvas.svelte` — thin wrapper around `<TextMarkdownView>` plus the Source panel.
- `frontend/src/lib/canvas/text/TextMarkdownView.svelte` — extracted from `TextCanvas.svelte` (DRY).
- `frontend/tests/e2e/dynamic-list-diagram.spec.ts` — Playwright: create dynamic_list, add two elements + one relationship via fixtures, assert bullet rendering.

### Modify

- `backend/app/diagrams/service.py` — (a) extract intra-diagram relationships helper, (b) on diagram read, if `diagram_type == "dynamic_list"`, populate `data.content` and `data.is_content_locked` from `compute_dynamic_list_content`.
- `backend/app/diagrams/router.py` — no signature change; verify the GET path runs through the service hook (likely already does).
- `backend/app/export/service.py` — verify the bundle reader uses the same service path; no behavioural change expected, but a test asserts dynamic_list export markdown matches the synthesised content.
- `frontend/src/routes/views/[id]/+page.svelte` — branch in edit mode: if `diagram.data.is_content_locked`, render `<DynamicListCanvas>` instead of `<TextCanvas>`. Wire Save → `update_diagram` with the new `data.dynamic_source` only.
- `frontend/src/lib/components/DiagramDialog.svelte` — add `{ value: 'dynamic_list', label: 'Dynamic List' }` to the `markdown` notation fallback list (still primarily registry-driven).
- `frontend/src/lib/canvas/text/TextCanvas.svelte` — replace its inline markdown-render block with `<TextMarkdownView>`.
- `CHANGELOG.md` — `[Unreleased]` → Added: dynamic list diagram type.
- `README.md` — add dynamic_list to the diagram-types list.
- `mcp/README.md` — note that `render_diagram` works on dynamic_list with no new tool (export-via-existing-path).

### Delete

None.

## Verification

1. **Unit (backend)** — `compute_dynamic_list_content` against a fixture diagram with 2 elements and 1 intra-diagram relationship returns the exact expected markdown (case `diagram_relationships`). Package case asserts after #149 lands.
2. **API** — `GET /api/diagrams/{id}` on a `dynamic_list` diagram returns populated `data.content` and `data.is_content_locked=true`; raw DB row's `data` does *not* contain those keys.
3. **Export** — `GET /api/export/diagram/{id}?format=md` returns identical markdown to the `data.content` from the API read; the docx and pdf renderers round-trip without error (re-uses the renderer module from ADR-179).
4. **MCP** — calling `render_diagram(diagram_id)` via the MCP server (manual test against the dev server) returns the same markdown.
5. **Frontend (Playwright)** — create dynamic_list diagram, seed two elements + one relationship via the API, load `/views/[id]`, assert the rendered list contains both bullets in the expected order; assert no textarea is present; click Edit, assert Source panel is visible and textarea is *still* absent.
6. **Parity** — `scripts/check_surface_parity.py` passes without modification (no new write verb introduced).
7. **TDD discipline** — every commit's diff includes the test that drove it; CI green on the feature branch before merge.
8. **README accuracy (protocols §12)** — README diagram-types section updated in the same PR.

## Risks / open items

- **Ordering risk**: if many elements / many relationships, the auto-rendered list can be long. v1 has no pagination — accept it for now. Decision deferred to a later ADR if user feedback requires it.
- **Edit-mode confusion**: the "Edit" button on a read-only canvas is unusual. The Source panel's heading ("Source for this list") and the disabled-textarea visual should make it obvious. Watch UAT feedback.
- **Cache coherence**: `data.content` is computed on every read. If a relationship is added/removed elsewhere, the list updates on next view — no cache invalidation needed because there's no cache. If a downstream user *exports* a dynamic_list and the relationships change later, the export reflects the snapshot at export time, which matches the user's intent ("when exported... a normal markdown file with the text as displayed in browse mode").
- **#149 timing**: if #149 slips, #147 ships with package-mode disabled and a small follow-up enables it. Plan does not gate v6.7.0 on #149.

## Sequencing

This is a single-phase issue — no inter-phase coordination needed. Suggested commit order on the feature branch:

1. ADR-184 + ADR-185 + SPEC-184-A + SPEC-185-A.
2. Failing pytest for `compute_dynamic_list_content` (default mode).
3. Migration m066 + service helper + `dynamic_list.py` (test passes).
4. Diagram-read service hook (synthesise `data.content` + `data.is_content_locked`).
5. Frontend: `TextMarkdownView` extract + `DynamicListCanvas` + DiagramDialog entry.
6. Playwright e2e.
7. CHANGELOG + README updates.
8. v6.7.0 bump + GH release.
9. Follow-up commit (after #149): enable package-mode branch + its pytest.

Branch: `feature/issue-147-dynamic-list-notation` (per protocols §4).
