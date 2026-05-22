# Plan — Issue #211 comment follow-ups (2026-05-22)

**Status:** Plan + execute
**Source:** [Issue #211 comment of 2026-05-22T20:34Z](https://github.com/cgbarlow/iris/issues/211)
**Companion docs:**
- [`docs/plans/issue-211-shopping-list-implementation.md`](./issue-211-shopping-list-implementation.md)
- [`docs/plans/issue-211-followups-implementation.md`](./issue-211-followups-implementation.md)

The user surfaced six observations after exercising the v6.18.0–v6.26.0 release stack. This plan classifies each, picks a fix, and groups them into three PRs following [`docs/protocols.md`](../protocols.md).

---

## 1. Observations

| # | Observation | Classification | PR |
|---|---|---|---|
| **O1** | "Is there supposed to be a section in admin settings based on the 10 PRs?" | Discoverability / info — **no code change** | n/a |
| **O2** | "Picker shows 'Sized story' stamp for a 'sausages' element — too broad" | **Real bug**: scope filter is `element_type` only, which is `class` for everything → all stamps match | PR 11 |
| **O3** | "Which stamp do I pick for pork mince?" | Symptom of O2 + missing UI affordance. Resolved by O2's fix (only Quantified item will remain for grocery items). | covered by PR 11 |
| **O4** | "Renamed 'meal plan' set to 'recipes', created a 'weekly meal plan' set" | Context, not a request | n/a |
| **O5** | "Creating a new set from a collection-filtered view should auto-attach to that collection" | **Real UX gap** | PR 12 |
| **O6** | "Set-edit aggregation profiles help text mentions ADRs — make it friendlier" | **Copy fix** | PR 13 |
| **O7** | "Should be a picker to clone from an existing seeded profile when creating set-scoped" | **Missing UX affordance** | PR 13 |

---

## 2. O1 answer (information, no PR)

For Chris when he reads this plan:

- **Admin home (`/admin`)** has the "Aggregation profiles" card (v6.25.0). Same page as Users / Audit / Settings.
- **Per-set aggregation profiles** appear at the **bottom of the set edit page** (`/sets/{id}`), above the Danger zone (v6.25.0).
- **Element-template stamps** appear on each **element template detail page** (`/element-templates/{id}`) under a "Markdown stamp" section (v6.24.0).
- **Smart-markdown picker stamps** show up when you press `/` in a smart_markdown editor → drill into an element → top of the drill menu (v6.23.0).
- **Aggregation list diagrams** are created via the existing **New Diagram** dialog → notation `markdown` → "Aggregation list" type (v6.26.0).

No global "Issue #211 hub" page is planned — the workflow is deliberately threaded through existing screens so the primitives feel native rather than ghettoised into a separate area.

---

## 3. PR 11 — Stamp scope filter: attribute-presence match (v6.27.0)

**Type:** Architectural — adds an ADR.

### Problem

`GET /api/element-templates/stamps?element_id=<id>` filters by:
1. Scope (global or matching set).
2. **`template_data.element_type` matches element's `element_type`.**

(2) is too coarse: all groceries are `class`-typed, all story elements would be `class`-typed too, and the five seeded stamps all target `element_type=class`. Result: every grocery element gets all five stamps in the picker, including the "Sized story" one that makes no sense for a sausage.

### Decision (ADR-215)

Add a second filter that matches stamps to elements by **attribute presence**: a stamp is in-scope for an element when *every* attribute the stamp's body references (via `{{self:attr:attributes/<NAME>/…}}`) is present on the element's `data.attributes` array.

The seeded blueprints already declare the attributes each stamp needs (`Quantified item` → Quantity + Unit; `Sized story` → Points; etc.). The filter compares the stamp's `template_data.data.attributes` blueprint to the element's actual attributes; if any required attribute isn't on the element, the stamp is hidden.

After the fix:
- Sausages (has Quantity + Unit + Products) → **Quantified item** shown; Sized story / Logged work / Line item / Read entry hidden.
- A story element with Points → **Sized story** shown; others hidden.
- The element type still has to match (`class`), but attribute presence is the discriminator.

### Why not "any-of" or tag-based

- **Any-of** (stamp shown if at least one of its attributes is on the element) — admits noise: a generic element with one of many attributes would get unrelated stamps. We want precision.
- **Tag-based** matching (manual user tags) — new authoring burden; harder to seed; doesn't reuse existing data. Rejected.

### Spec (SPEC-211-d)

- Backend `list_stamps_for_element` adds the attribute-presence check.
- Endpoint shape unchanged; only the filter logic changes.
- Element-type filter stays (it's still the cheap first pass).
- Tests: stamp with Points hidden from an element that has only Quantity/Unit; stamp with Quantity+Unit shown when both present; stamp with no attribute-blueprint shown for any element (the wildcard case from SPEC-211-a §3 still applies).

### Risk

- Existing five seeded stamps each declare specific attribute blueprints, so they each become element-specific in the picker. The user's 178 grocery items (with Quantity + Unit thanks to v6.22.0 backfill) will only see Quantified item — the intended behaviour.
- User-authored stamps that reference attributes outside their blueprint would surface a mismatch. Documented in the spec; the in-browser stamp editor (v6.24.0) doesn't strictly enforce the blueprint, but the filter is honest about what the stamp would render.

### Genericness (ADR-214)

Adds a *generic* logic change (attribute-presence intersection) — no domain terminology. Clean.

---

## 4. PR 12 — Set creation inherits current collection (v6.28.0)

**Type:** Architectural — adds a small ADR.

### Problem

From `/collections/{id}` (or `/sets?collection_id=<id>`) the user clicks "Create new set". The new set is created globally with no collection. The user has to go re-attach it. Friction.

### Decision (ADR-216)

When the user is viewing the sets list filtered by a collection (or browsing inside a collection), the **"Create new set"** action carries the active collection_id through into the create payload. Backend already supports `set_id → collection_id` association; the frontend just needs to read the active filter and pass it.

### Spec (SPEC-216-a)

- Frontend `/sets/+page.svelte` (and `/collections/[id]/+page.svelte` if it has a create-set affordance) reads the `?collection_id` query param OR the in-page filter state, and passes it as `collection_id` in the `POST /api/sets` body.
- Backend behaviour unchanged.
- Test: create-set on a collection-filtered view → resulting set has the expected `collection_id`.

### Risk

- Low. The behaviour is opt-in based on the URL/state; sets created from the unfiltered list remain collection-less (current behaviour).

---

## 5. PR 13 — Aggregation profile editor polish (v6.29.0)

**Type:** Spec extension — no new ADR.

### O6 — Friendly UI strings

Replace the help text in `AggregationProfileEditor.svelte`:

> "Profiles drive the aggregation engine (ADR-212). Edit as JSON; schema is documented in SPEC-212-a. Seeded global profiles are good clone templates — duplicate one and edit the fields you need."

with something friendlier and ADR-free:

> "Aggregation profiles describe how to roll up data across a group of documents. They drive features like the shopping list (sum quantities across a meal plan), sprint points (sum story points across a backlog), or expense reports (sum amounts across receipts). Pick a seeded profile as a starting point and duplicate-and-edit it for your use case."

Same on the admin home page card.

### O7 — Clone-from-existing affordance

Currently the editor has **+ New profile** which gives an empty template. Add a parallel **+ Clone from existing** action: opens a small list of in-scope profiles (globals + same-set), pick one, prefills the editor with its values + appends "(copy)" to the name. The user then customises and saves as a new profile (always set-scoped when invoked from the set page; always global when invoked from the admin page — matches the editor's existing scope rules).

### Spec (SPEC-212-e)

- Extends [SPEC-212-d](../adrs/specs/SPEC-212-d-Aggregation-Profile-Editor.md) §1.
- New "Clone from…" button on the editor that opens an inline selector.
- The default `+ New profile` action retains current behaviour (default-template clone).
- Pulls the source profile via the existing list endpoint, no new backend call.

### Tests

- Frontend unit test: cloning a profile copies `profile_data` and prefills name with `<original> (copy)`.

### Risk

- Trivial; new optional affordance.

---

## 6. Protocol checklist (per PR)

Per [`docs/protocols.md`](../protocols.md):

| Protocol | PR 11 | PR 12 | PR 13 |
|---|---|---|---|
| §1 ADR | ADR-215 | ADR-216 | _(spec extension)_ |
| §2 SPEC | SPEC-211-d (stamp filter) | SPEC-216-a (set-create) | SPEC-212-e (profile editor polish) |
| §3 TDD | backend + frontend unit tests | frontend unit test | frontend unit test |
| §4 Feature branch | `feature/stamp-filter-by-attribute` | `feature/set-create-inherits-collection` | `feature/profile-editor-polish` |
| §5 CHANGELOG | entry | entry | entry |
| §6 Release | tag + GH Release | tag + GH Release | tag + GH Release |
| §7 `{@html}` | none | none | none |
| §8 Context7 | not needed (existing libs) | not needed | not needed |
| §9 Production code | yes | yes | yes |
| §11 Latest deps | no new deps | no new deps | no new deps |
| §12 README | no change needed | no change needed | no change needed |
| §13 DRY | no duplication | no duplication | clone path reuses existing list endpoint |
| §14 Surface parity | no new writes (filter change) | no new writes (frontend-only) | no new writes |
| §15 SQLite ↔ Supabase | no DB changes | no DB changes | no DB changes |
| ADR-214 genericness | clean | clean | clean (friendly copy still domain-free) |

---

## 7. Release sequencing

Three feature PRs, each on its own branch, each tagging a minor:

| Version | What |
|---|---|
| **v6.27.0** | PR 11 — attribute-presence stamp filter (ADR-215, SPEC-211-d) |
| **v6.28.0** | PR 12 — set creation inherits current collection (ADR-216, SPEC-216-a) |
| **v6.29.0** | PR 13 — profile-editor friendly copy + clone-from-existing (SPEC-212-e) |

No DB migrations. No Supabase migration gates. Render auto-deploys on merge to main.
