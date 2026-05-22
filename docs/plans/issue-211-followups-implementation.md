# Implementation plan — Issue #211 follow-ups

**Status:** Draft + execute
**Date:** 2026-05-22
**Companion docs:**
- [`docs/plans/issue-211-shopping-list-implementation.md`](./issue-211-shopping-list-implementation.md)
- [`docs/analysis/issue-211-shopping-list-research.md`](../analysis/issue-211-shopping-list-research.md)

The six PRs that shipped v6.18.0 → v6.22.0 deliberately deferred four frontend-UX items so the backend, MCP, CLI, and demo workflow could land first. The MCP / CLI surfaces meet the `/goal` definition of done (Claude Desktop and the Chrome extension can drive the workflow without any of the deferred UX). This plan completes the remaining UX so the same workflows are accessible from the browser UI too.

---

## 1. Follow-ups in scope

| # | Title | Release | Primary surface |
|---|---|---|---|
| **F1** | Smart-markdown picker — "Stamps" section | v6.19.1 | `SmartMarkdownSlashPicker.svelte` |
| **F2** | Element-template stamp editor in self-mode | v6.19.2 | element-template editor screen |
| **F3** | Form-based aggregation-profile editor | v6.21.2 | new `AggregationProfileEditor.svelte` + admin + set-edit |
| **F4** | Aggregation_list source/profile pickers | v6.21.3 | `DiagramDialog.svelte` (create flow) |

All four ship as their own feature branch and minor version. No schema changes; no Supabase migrations. Genericness invariant (ADR-214) continues to apply.

## 2. ADRs / specs (per protocol §1, §2)

Each follow-up is a UX completion of an already-shipped ADR — not a new architectural decision. Per ADR-001 (Enhanced ADR Format), UX detail belongs in the **spec**, not a new ADR. So:

- **No new top-level ADRs.** F1–F4 are spec extensions on top of existing ADRs.
- **New specs**: SPEC-211-b (stamp picker UI), SPEC-211-c (stamp editor UI), SPEC-212-d (profile editor UI), SPEC-213-b (aggregation_list create-dialog pickers).
- Each spec references its parent ADR and supersedes the relevant "Out of scope (v6.19.x follow-up)" section.

## 3. Per-PR plan

### PR 7 — `feature/picker-stamps-section` → v6.19.1

**Spec:** [`SPEC-211-b-Picker-Stamps-Section.md`](../adrs/specs/SPEC-211-b-Picker-Stamps-Section.md)

- After entity selection in `SmartMarkdownSlashPicker.svelte`, fetch in-scope stamps via `GET /api/element-templates/stamps?element_id=<id>`.
- Render a "Stamps" section above the existing field-step list. Each stamp is a one-pick row that emits the resolved stamp body (with `{{self:…}}` already substituted by the backend) at the picker's caret.
- Keyboard: Tab/Enter on a focused stamp inserts it; Escape closes the picker as today.
- Empty / no-stamps response → no Stamps section shown (no chrome change).
- Frontend unit test in `frontend/tests/unit/pickerStampsSection.test.ts`: covers fetch → state → emit token-body.
- No backend changes (endpoint shipped in v6.19.0).

### PR 8 — `feature/stamp-editor-self-mode` → v6.19.2

**Spec:** [`SPEC-211-c-Stamp-Editor-Self-Mode.md`](../adrs/specs/SPEC-211-c-Stamp-Editor-Self-Mode.md)

- New "Stamp" tab in the element-template detail/edit screen.
- Reuses `SmartMarkdownCanvas.svelte` with a new `selfMode: true` prop:
  - The picker (also gets `selfMode`) skips the entity-browse step and assumes `self`.
  - Picker emits `{{self:<field-spec>}}` tokens instead of `{{element:UUID:<field-spec>}}`.
  - Live preview pane renders the stamp body against the template's `source_element_id` (when set) so authors see realistic output.
- Submit posts the new body to `PUT /api/element-templates/{id}` with `markdown_stamp` set.
- Frontend unit test in `frontend/tests/unit/stampEditorSelfMode.test.ts`: covers picker self-mode token emission + preview substitution.

### PR 9 — `feature/aggregation-profile-editor` → v6.21.2

**Spec:** [`SPEC-212-d-Aggregation-Profile-Editor.md`](../adrs/specs/SPEC-212-d-Aggregation-Profile-Editor.md)

- New component `frontend/src/lib/components/AggregationProfileEditor.svelte` — tabs:
  - **General**: name, description, scope (locked to whatever the entry-point set).
  - **Traversal**: outer (collapsible, optional) + inner step. Each has a token-type dropdown, attribute-path text inputs, skip-blank toggle. Multiplier sub-form when outer enabled.
  - **Output**: group_by, sort_groups, sort_items_within_group, aggregation_fn, line_format, breakdown_format. Format-string inputs show available placeholder hints.
  - **Preview**: source-diagram picker → renders engine output against the current draft via `POST /api/aggregation/run` with `inline_profile_override`. (NOTE: backend `inline_profile_override` is *not* yet shipped — the editor's preview uses save-then-run for v6.21.2 and a "preview anonymous" path is a v6.21.3+ idea. For v6.21.2 the Preview tab is read-only "Save first to preview".)
- Used in two parents:
  - Admin → new "Aggregation profiles" tab → list + edit + create global profiles.
  - Set edit page → new "Aggregation profiles for this set" section → list + edit + create set-scoped profiles.
- Frontend unit tests for the form's serialisation: profile JSON round-trips through the editor's form state without loss.

**Out of scope for this PR:**
- Inline preview (deferred — needs a backend tweak to accept `inline_profile_override` on `/run`; small change, future PR).
- Profile-JSON raw editor toggle (deferred).

### PR 10 — `feature/aggregation-list-pickers` → v6.21.3

**Spec:** [`SPEC-213-b-Aggregation-List-Pickers.md`](../adrs/specs/SPEC-213-b-Aggregation-List-Pickers.md)

- `DiagramDialog.svelte` create flow for `diagram_type === "aggregation_list"`:
  - Replace the raw `source_diagram_id` UUID text input with a diagram autocomplete (typeahead against `/api/diagrams?name~=...`). Scope to the same set the diagram is being created in (and globals).
  - Replace the raw `profile_id` UUID input with a profile dropdown (in-scope profiles via `/api/aggregation/profiles?set_id=...&include_global=true`).
- Read-mode unchanged (the canvas just renders `data.content`).
- Frontend unit test for the autocomplete logic and the profile-dropdown wiring.

## 4. Protocol checklist (per PR)

| Protocol | Action |
|---|---|
| §1 ADR | No new ADRs (spec extensions only). |
| §2 SPEC | One new spec per PR. |
| §3 TDD | Frontend unit tests written alongside code (existing posture: data-shape + business-rule level). |
| §4 Feature branch | Each PR on `feature/*`. |
| §5 CHANGELOG | Entry per PR. |
| §6 Releases | Tag + GitHub Release each minor. |
| §7 `{@html}` | No new `{@html}` paths — all rendering goes through `MarkdownView` (DOMPurify) or plain Svelte text bindings. |
| §8 Context7 | Svelte 5 runes / @xyflow/svelte are well-known; no new libraries. |
| §9 Production code | No mocks/stubs in app code. |
| §11 Latest deps | No new deps added. |
| §12 README | No README change (features in admin + set-edit are linked from existing surfaces). |
| §13 DRY | F2 + F1 share the same picker component (different `selfMode` flag). F3 component reused in two parents. |
| §14 Surface parity | No new write endpoints; existing parity continues. |
| §15 SQLite ↔ Supabase | No DB changes. |

## 5. Frontend testing approach

Per the project's existing convention (see comment in `frontend/tests/unit/namedPrompts.test.ts`):

> "Light-touch unit tests aligned with this repo's frontend testing posture (data shape + business rules, not Svelte component rendering)."

Each follow-up's tests cover the data-flow logic (request shaping, response parsing, token emission, profile-JSON round-trip) rather than full component renders. Visual / e2e behaviour is verified by the user in-browser post-deploy.

## 6. Release sequencing

Same pattern as v6.18.0–v6.22.0: feature branch → PR → squash-merge → tag → GitHub Release. No Supabase migrations (no DB changes). Render auto-deploys on push to `main`.

## 7. Definition of done

After all four PRs:

- The smart-markdown picker offers stamps as one-pick rows (F1).
- Element templates can be authored — including their markdown_stamp — entirely in the browser (F2).
- Admin and set editors can create / edit aggregation profiles without touching JSON (F3).
- Aggregation_list diagrams can be created without typing UUIDs (F4).

The genericness invariant remains clean. The MCP / CLI / REST surfaces remain unchanged. The shopping-list demo workflow is reachable from both the agent path (already complete) and the human-driven UI path (closed by these follow-ups).
