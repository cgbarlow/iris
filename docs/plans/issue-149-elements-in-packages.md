# Plan: Elements can belong to a package (issue #149)

## Context

Issue #149 (title corrected mid-conversation):

> Enhancement: Optionally allow **elements** to belong to a package, not
> just a set.

Body:

> allow elements to belong to a packages. this must be exposed in all
> surfaces, gui, api, cli, mcp. Following existing patterns under /view
> page, display element → package relationships beneath a new
> 'Relationships' tab.

User clarifications (plan-time AskUserQuestion):

- **Cardinality**: one package per element. Simple nullable `package_id` column on `elements`. Not a many-to-many; not a row in the `relationships` table.
- **Scope confirmation**: title typo was the only ambiguity. Package-in-package nesting on the schema/API side already works (m016 introduced `parent_package_id`; CLI / MCP / API parity for `move_package` already ships). This issue is strictly about **element → package membership**. Knowledge-graph nesting visuals are *not* in scope.

Recon findings that shape the plan:

| Area | Today |
|---|---|
| Elements table | `entities` renamed to `elements` in m016. Today carries `set_id` (nullable, FK to `sets.id`). No `package_id` column. |
| Packages table | Has `parent_package_id` and `set_id` (m016). `PUT /packages/{id}/parent` accepts `parent_package_id` only. |
| Element CRUD models | `backend/app/elements/models.py` — `ElementCreate` includes `set_id` (line 15) but no `package_id`. `ElementResponse` exposes `set_id` + `set_name` (lines 53–54). `ElementUpdate` (lines 20–27) is currently identity/metadata only — no parent-change. |
| ADR-178 invariant | `move_element` doesn't exist because "elements travel with their parent diagram". Documented asymmetry in `scripts/check_surface_parity.py` (line 38–40). **Caveat**: that invariant was about *diagram* parentage. Adding an *optional, orthogonal* `package_id` on an element is additive — it does not move the element between diagrams. We need to be explicit in the ADR that #149 does not violate ADR-178, and update the parity exception list to record the new write verb. |
| /view page tabs | `frontend/src/routes/views/[id]/+page.svelte:66` — `activeTab` is one of `'details' \| 'canvas' \| 'relationships' \| 'versions'`. **A 'relationships' tab already exists** (lines 2126–2147 + 3180+). It currently shows `diagramRelationships` (package↔package, lines 70–95) and `elementRelationships` (element↔element). Backed by `GET /api/diagrams/{id}/relationships` (line 795). |
| Issue wording vs. reality | The issue says "a new 'Relationships' tab" but the tab already exists. Interpretation: augment the existing tab with a new section showing element→package memberships of elements drawn on the diagram. This mirrors the existing pattern (one tab, two sections: diagram-level rels + element-level rels). |
| Surface parity reference | `scripts/check_surface_parity.py` (lines 33–47) — `_KNOWN_ENTITIES` includes `element`; `DOCUMENTED_ASYMMETRIES` includes `("design_invariant", "move_element", "ADR-178 invariant — elements travel with their parent diagram")`. The new write verb is **not** a `move_element` — it's an `update_element` enrichment (settable `package_id`). So the parity check stays satisfied without a new exception. |
| CLI element ops | `cli/src/iris_cli/main.py` — `create_element` (line 651), `update_element` (line 834, comment line 841: "elements cannot be moved between [diagrams]"). Both lack `package_id`. |
| MCP element tools | `mcp/src/iris_mcp/tools.py` — `create_element` handler at line 364, `update_element` at line 576. Both pass through a fixed allow-list of keys; `package_id` is not in either today. |

The user's framing — "Optionally allow elements to belong to a package, not just a set" — means the new column is **additive and orthogonal** to `set_id`. An element can have neither, just a `set_id`, just a `package_id`, or both. Validation: if `package_id` is set and the package has a `set_id`, the element's `set_id` (if also set) must match. This keeps the data model from drifting into inconsistency.

## Decisions

| # | Decision |
|---|---|
| 1 | **Schema**: add a single nullable column `package_id TEXT REFERENCES packages(id)` to `elements`. New migration `m067_element_package_membership.py` adds the column + index `idx_elements_package ON elements(package_id)`. Pick nullable over a join table because user confirmed one-package-per-element cardinality. |
| 2 | **Cross-field invariant**: if `element.package_id IS NOT NULL` AND `element.set_id IS NOT NULL`, then the referenced package's `set_id` must equal the element's `set_id` (or the package's `set_id` must be NULL — package belongs to no set). Enforced in service layer (`create_element` / `update_element`) and surfaced as HTTP 422 with a clear error message. No DB-level CHECK constraint — keeps the migration backwards-compatible and SQLite-portable. |
| 3 | **Update verb, not a move verb**: extending `ElementUpdate` to accept `package_id: str \| None` is the cleanest path — it's the existing PATCH-like surface, and the parity exception list already documents `move_element` as forbidden (and stays forbidden). No new endpoint. Backend allow-listed field; setting to literal `null` clears the membership. |
| 4 | **Read response**: `ElementResponse` gains `package_id: str \| None` and `package_name: str \| None` (mirrors the existing `set_id` / `set_name` pair). Service join in `list_elements` / `get_element` extended once. |
| 5 | **Listing filter**: `list_elements` gains an optional `package_id` query parameter, with the same three-valued semantics as `list_diagrams.parent_package_id` (omitted = no filter; literal `"null"` string = `package_id IS NULL`; any other string = exact match). Per protocols §13, the parameter-parsing logic is extracted into a shared helper `app/common/nullable_filter.py` and reused by `list_diagrams` (which today inlines this). |
| 6 | **List a package's elements**: new endpoint `GET /api/packages/{id}/elements` (paginated; same shape as `GET /api/packages/{id}/diagrams`) for the use case "show me everything attached to this package". Service helper `list_package_elements(db, package_id, page, page_size)` exported and reused by #147's package-mode path. |
| 7 | **Frontend — element form**: when editing an element from the set page or the element-detail dialog, expose a "Package" picker (PackagePicker, scoped to the element's set if set_id is non-null, otherwise to all packages). Setting reflects in real time. Mirrors the existing set picker UX. |
| 8 | **Frontend — Relationships tab augmentation** (the issue's GUI requirement): add a new section *Element → Package memberships* to the existing Relationships tab on `/view/[id]`. For each element drawn on the current diagram that has a non-null `package_id`, render a row `{element.name} → {package.name}` with a link to `/packages/{package_id}`. Loader extends `loadDiagramRelationships` to also fetch element memberships (single round-trip via the existing `/api/diagrams/{id}/relationships` endpoint, augmented server-side to include an `element_package_memberships` array — see Decision 9). The tab's pill counter (line 2135) sums all three categories. |
| 9 | **API extension instead of a new endpoint** for the Relationships tab data: extend `GET /api/diagrams/{id}/relationships` response to `{diagram_relationships, element_relationships, element_package_memberships}`. Avoids an extra round-trip and keeps the tab's data fetch single-shot. The frontend's existing TS interface gains a third array; missing-key tolerance preserved for old clients. |
| 10 | **CLI parity (protocols §14 + ADR-180)**: `iris elements update <id> --package-id <pkg>` (and `--package-id null` to clear). `iris elements list --package-id <pkg>` for filtering. `iris packages list-elements <pkg>` mirrors `iris packages list-diagrams`. No `iris elements move` — design invariant preserved. |
| 11 | **MCP parity (protocols §14 + ADR-178)**: `update_element` MCP tool's allow-list extended to include `package_id`. `list_elements` tool gains an optional `package_id` arg. New tool `list_package_elements(package_id, limit, page)`. No `move_element` tool. |
| 12 | **TDD ordering (protocols §3)**: pytest for the new column + invariant first; then service update; then API; then CLI / MCP; then frontend Playwright. |
| 13 | **Surface-parity script update**: `scripts/check_surface_parity.py` — add `list_package_elements` to whichever surface inventory needs it (likely just verifies CLI ↔ MCP ↔ backend equivalence on the new tool). Verify no exception needed — this is a `GET`, not a write verb, so the parity rule (writes only) doesn't apply. **Confirmation pending implementation**: re-read the script before changing it. |
| 14 | **Versioning**: v6.7.0 (single minor bump). If shipped after #147's v6.7.0, this becomes v6.8.0. Coordinated at merge time. GH release per `feedback_release_workflow`. CHANGELOG `[Unreleased]` → versioned section + README diagram-feature line. |
| 15 | **Backfill**: no backfill needed — new column defaults NULL. Existing element semantics unchanged. Migration is online-safe (ADD COLUMN nullable). |
| 16 | **Knowledge-graph nesting**: out of scope per user clarification. If the user later wants the KG to render element→package edges, it goes in a separate ADR. |

## ADRs to create

| ADR | Title |
|-----|-------|
| ADR-186 | Element → package optional membership |
| ADR-187 | Nullable-filter three-valued query convention (extracted from m6.6.4 diagrams pattern) |

ADR-187 is split out because the three-valued query semantics (`omitted` / `"null"` literal / exact match) is now reused by `list_elements`, was already used by `list_diagrams`, and likely shows up in future list endpoints. Worth a standalone decision record so the convention is canonical.

## Specs to create

- `SPEC-186-A-Element-Package-Membership.md` — schema delta, invariant, API surface, CLI/MCP surface, GUI behaviour, Relationships-tab section, acceptance criteria.
- `SPEC-187-A-Nullable-Filter-Convention.md` — semantics of three-valued query parameters, the shared helper signature, and which endpoints currently use it.

## Files

### Create

- `docs/adrs/ADR-186-Element-Package-Membership.md`
- `docs/adrs/ADR-187-Nullable-Filter-Convention.md`
- `docs/adrs/specs/SPEC-186-A-Element-Package-Membership.md`
- `docs/adrs/specs/SPEC-187-A-Nullable-Filter-Convention.md`
- `backend/app/migrations/m067_element_package_membership.py` — `ALTER TABLE elements ADD COLUMN package_id TEXT REFERENCES packages(id);` + index.
- `backend/app/common/nullable_filter.py` — `parse_nullable_id(value)` returning a tagged union `("none",) | ("is_null",) | ("eq", id_str)`.
- `backend/tests/test_element_package_membership.py` — coverage for: column added, invariant blocks mismatched set, update clears via null, list filter, package-elements endpoint.
- `backend/tests/test_nullable_filter.py` — unit tests for the shared helper.
- `cli/tests/test_elements_package.py` — CLI `--package-id` set / unset / list-filter.
- `mcp/tests/test_update_element_package.py` — MCP tool accepts package_id; list_package_elements works.
- `frontend/tests/e2e/element-package-membership.spec.ts` — create element with package via UI, assert it appears under the package; assert the /view Relationships tab third section renders.

### Modify

- `backend/app/elements/models.py` — `ElementCreate` + `ElementUpdate` gain `package_id`; `ElementResponse` gains `package_id` and `package_name`.
- `backend/app/elements/router.py` — pass `package_id` through create/update; add `?package_id=` filter on list; reuse shared helper.
- `backend/app/elements/service.py` — enforce cross-field invariant; join packages for `package_name`; extend list query.
- `backend/app/packages/router.py` — `GET /api/packages/{id}/elements` (paginated).
- `backend/app/packages/service.py` — `list_package_elements(db, package_id, page, page_size)`.
- `backend/app/diagrams/router.py` (or `service.py`) — extend `GET /api/diagrams/{id}/relationships` response with `element_package_memberships`.
- `backend/app/diagrams/service.py` — refactor `list_diagrams.parent_package_id` to use the new shared helper (protocols §13 DRY).
- `cli/src/iris_cli/main.py` — `--package-id` option on `elements update`, `elements list`; new `packages list-elements` subcommand.
- `mcp/src/iris_mcp/tools.py` — extend `update_element` allow-list; extend `list_elements` arg schema; new `list_package_elements` tool.
- `frontend/src/lib/components/ElementForm.svelte` (or wherever the element edit form lives — confirm during implementation) — `PackagePicker` integration.
- `frontend/src/routes/views/[id]/+page.svelte` — extend `loadDiagramRelationships` to read the new `element_package_memberships` array; add a third section under the Relationships tab; update `hasRelationships`/pill counter logic.
- `frontend/src/lib/types/*.ts` — extend the relationships response type.
- `scripts/check_surface_parity.py` — verify nothing needs change (write parity already satisfied via `update_element`); add a comment if appropriate.
- `CHANGELOG.md` — `[Unreleased]` → Added: element → package membership across all surfaces; new Relationships-tab section.
- `README.md` — note the new element-membership capability.
- `mcp/README.md` + `cli/README.md` — document the new flags / args.

### Delete

None.

## Verification

1. **Migration** — m067 applies cleanly against a fresh DB and against the v6.6.5 production schema snapshot. New column nullable, index created.
2. **Backend unit** — invariant rejects mismatched `(element.set_id, package.set_id)`; allows match; allows `set_id=NULL`. Update with `package_id=null` clears membership. `list_elements?package_id=null` returns only orphan elements.
3. **API integration** — create element with `package_id`, GET it back, assert `package_id` + `package_name` present. `GET /api/packages/{id}/elements` paginates correctly.
4. **CLI** — `iris elements update <id> --package-id <pkg>` round-trips; `iris elements list --package-id null` lists unmembered.
5. **MCP** — same round-trip via `update_element` tool; `list_package_elements` returns expected rows.
6. **Frontend Playwright** — element form's package picker writes through; element-detail page shows package badge; Relationships tab on a diagram containing the element shows the third section with the correct row.
7. **Surface parity** — `scripts/check_surface_parity.py` passes; CI workflow green.
8. **Protocols §12** — README and CHANGELOG updated in the same PR.
9. **#147 dependency unlocks** — the package-mode branch of dynamic_list can now activate. Run #147's gated test (`pytest.mark.skipif` removed) to confirm.

## Risks / open items

- **Frontend element-form location**: my recon didn't pin the exact file for "element edit". Likely `frontend/src/lib/components/ElementForm.svelte` or the inline editor in the set page. Pin during implementation, not at plan time.
- **PackagePicker scoping**: today the picker accepts `initialSetId`. Need to confirm it honours that scope; otherwise the element-form integration needs a small picker enhancement to constrain to one set.
- **Backfill skipped intentionally** — every existing element will have `package_id=NULL`. Acceptable because the feature is *additive*.
- **Cross-set move semantics**: if a user later changes an element's `set_id` to a set that does not contain the element's existing `package_id`, the invariant fails. Decision: in that case, also null the `package_id` in the same update. Documented in the spec to keep the UX from blocking valid set-moves.
- **Relationships tab name collision**: the issue says "new Relationships tab" but the tab exists. We're augmenting, not creating. If the user wanted a *literal* new tab (e.g. `'package-memberships'`), I'll redirect at PR review — current plan is the lower-friction interpretation.

## Sequencing

Single-phase issue, suggested commit order on the feature branch:

1. ADR-186 + ADR-187 + SPEC-186-A + SPEC-187-A.
2. Failing pytest for column + invariant.
3. Migration m067 + service invariant.
4. Models + API + list filter + endpoint.
5. Shared nullable-filter helper + refactor `list_diagrams` to use it.
6. CLI commands + tests.
7. MCP tools + tests.
8. Frontend element form + Relationships-tab section.
9. Playwright e2e.
10. CHANGELOG + READMEs + version bump (v6.7.0 or v6.8.0 depending on #147 timing).
11. GH release.

Branch: `feature/issue-149-element-package-membership` (per protocols §4).
