# Plan — Issue #211 comment follow-ups (2026-05-22)

**Status:** Draft, awaiting review (do not start implementation)
**Source:** [Issue #211 comment of 2026-05-22T20:34Z](https://github.com/cgbarlow/iris/issues/211) + clarifying exchange that followed
**Companion docs:**
- [`docs/plans/issue-211-shopping-list-implementation.md`](./issue-211-shopping-list-implementation.md)
- [`docs/plans/issue-211-followups-implementation.md`](./issue-211-followups-implementation.md)

The user surfaced six observations after exercising the v6.18.0–v6.26.1 release stack, plus two clarifying questions that refined PR 11's algorithm and added a seed-rename. This plan consolidates everything into three feature PRs, each on its own branch, following [`docs/protocols.md`](../protocols.md).

---

## 1. Observations & clarifications

| # | Observation / question | Classification | PR |
|---|---|---|---|
| **O1** | "Is there a section in admin settings based on the 10 PRs?" | Discoverability / info — **no code change** | n/a |
| **O2** | "Picker shows 'Sized story' stamp for a 'sausages' element — too broad" | **Real bug**: scope filter is `element_type` only, which is `class` for everything → all stamps match | PR 11 |
| **O3** | "Which stamp do I pick for pork mince?" | Symptom of O2 + missing UI affordance. Resolved by O2's fix. | covered by PR 11 |
| **O4** | "Renamed Meal Plan → Recipes, created Weekly Meal Plan set" | Context, not a request | n/a |
| **O5** | "Creating a new set from a collection-filtered view should auto-attach to that collection" | **Real UX gap** | PR 12 |
| **O6** | "Set-edit aggregation profiles help text mentions ADRs — make it friendlier" | **Copy fix** | PR 13 |
| **O7** | "Should be a picker to clone from an existing seeded profile when creating set-scoped" | **Missing UX affordance** | PR 13 |
| **C1** | Clarifying Q: how does PR 11 know which attributes a stamp expects? | **Algorithm refinement** → use stamp **body parsing**, not the source-element snapshot's blueprint | PR 11 §3 |
| **C2** | Clarifying Q: how do users create stamps & edit aggregation profiles? | Answered inline (existing flows + planned improvements) | n/a |
| **C3** | Rename seeded **"Quantified item"** → **"Ingredient"** | **Seed rename** | PR 13 |
| **C4** | "Add Clone-from-existing for element templates too (parallel UX)" | **Missing UX affordance** | PR 13 |

---

## 2. O1 answer (information, no PR)

For the record — where the issue-#211 surfaces live today:

- **Admin home (`/admin`)** has the "Aggregation profiles" card (v6.25.0). Same page as Users / Audit / Settings.
- **Per-set aggregation profiles** appear at the **bottom of the set edit page** (`/sets/{id}`), above the Danger zone (v6.25.0).
- **Element-template stamps** appear on each **element template detail page** (`/element-templates/{id}`) under a "Markdown stamp" section (v6.24.0).
- **Smart-markdown picker stamps** show up when you press `/` in a smart_markdown editor → drill into an element → top of the drill menu (v6.23.0).
- **Aggregation list diagrams** are created via the existing **New Diagram** dialog → notation `markdown` → "Aggregation list" type (v6.26.0).
- **Element creation from a template** is on the **elements list page (`/elements`)** → "Templates" button (v6.8.0, pre-dates issue #211).

No global "Issue #211 hub" page — the workflow is deliberately threaded through existing screens so the primitives feel native rather than ghettoised. If discoverability becomes a real complaint, we'd revisit; for now we lean on the natural placements.

---

## 3. PR 11 — Stamp scope filter: body-parsing attribute match (v6.27.0)

**Type:** Architectural change — adds an ADR.

### 3.1 Problem

`GET /api/element-templates/stamps?element_id=<id>` filters by:
1. Scope (global or matching set).
2. **`template_data.element_type` matches element's `element_type`.**

All groceries are `class`-typed; the five seeded stamps all target `element_type=class`. Result: every grocery element gets all five stamps in the picker, including the "Sized story" one that makes no sense for a sausage.

### 3.2 Decision (ADR-215)

Add a third filter step that matches stamps to elements by **attribute presence** — but the source of "which attributes does this stamp need?" is **the stamp body itself**, not the source element's snapshot.

```
required = { ATTR_NAME for every {{self:attr:attributes/ATTR_NAME/<...>}}
             token in stamp.markdown_stamp }
element_attrs = { a.name for a in element.data.attributes }
stamp_in_scope = required ⊆ element_attrs
```

Why **body-parsing** and not **template_data blueprint**:

- The template's `template_data.data.attributes` is a snapshot of *every* attribute the source element had at template-creation time (e.g. a sausage element has Unit, Products, Preferred product, Quantity, …).
- The stamp body usually references only a subset (e.g. just Quantity + Unit + name).
- Using the blueprint would over-constrain: a stamp captured from a sausage would only show on elements that also have Products and Preferred product — way too narrow.
- The body is the **authoritative** statement of which attributes the stamp will render. Anything not referenced doesn't matter.

After the fix:
- Sausages (Quantity + Unit + Products + Preferred product) → seeded **Ingredient** stamp shown; Sized story / Logged work / Line item / Read entry hidden.
- A story element with Points → **Sized story** shown.
- Stamps whose body references no attributes (just `{{self:name}}` etc.) match any element (current behaviour preserved).

### 3.3 Spec (SPEC-211-d)

Backend `list_stamps_for_element` (in `backend/app/element_templates/service.py`):

```python
import re
_BODY_ATTR_RE = re.compile(r"\{\{self:attr:attributes/([^/}]+)/[^}]+\}\}")

def _required_attrs(stamp_body: str) -> set[str]:
    return set(_BODY_ATTR_RE.findall(stamp_body or ""))

# Inside the existing filter loop:
required = _required_attrs(stamp.markdown_stamp)
element_attrs = {a["name"] for a in element_data.get("attributes", [])
                 if isinstance(a, dict) and "name" in a}
if required and not required.issubset(element_attrs):
    continue   # stamp doesn't apply
```

- Endpoint shape unchanged; only the filter logic changes.
- `element_type` filter stays (still the cheap first pass).
- A stamp body that references no attribute paths (e.g. just `{{self:name}}`) keeps the previous behaviour — applicable to any matching-element_type element.

### 3.4 Tests

`backend/tests/test_element_templates/test_stamps.py` extended:

- Stamp body with `{{self:attr:attributes/Points/type=}}` hidden from an element with only Quantity + Unit.
- Stamp body with Quantity + Unit shown when both present on the element.
- Stamp body with no `attr:` tokens shown for any element (regression of existing behaviour).
- Stamp body referencing an attribute the user added by hand (no `template_data` blueprint mention) is correctly detected.

### 3.5 Genericness (ADR-214)

Pure logic change — no new domain terminology in code. Clean.

---

## 4. PR 12 — Set creation inherits current collection (v6.28.0)

**Type:** UX behaviour change — adds a small ADR.

### 4.1 Problem

From `/collections/{id}` (or `/sets?collection_id=<id>`) the user clicks "Create new set". The new set is created globally with no collection. Friction.

### 4.2 Decision (ADR-216)

When the user is viewing the sets list filtered by a collection (or browsing inside a collection), the **"Create new set"** action carries the active collection_id through into the create payload. Backend already supports `collection_id` association; the frontend just reads the current filter state.

### 4.3 Spec (SPEC-216-a)

- Frontend `/sets/+page.svelte` (and `/collections/[id]/+page.svelte` if it has a create-set affordance) reads the `?collection_id` query param OR the in-page filter state, and passes it as `collection_id` in the `POST /api/sets` body.
- Backend behaviour unchanged.
- Test: create-set on a collection-filtered view → resulting set has the expected `collection_id`.

### 4.4 Risk

- Low. The behaviour is opt-in based on the URL/state; sets created from the unfiltered list remain collection-less (current behaviour).

---

## 5. PR 13 — UX consistency pass (v6.29.0)

**Type:** Spec extensions + a data migration for the seed rename. No new ADR.

### 5.1 Friendly copy in the aggregation-profile editor (O6)

Replace the help text in `AggregationProfileEditor.svelte`:

> "Profiles drive the aggregation engine (ADR-212). Edit as JSON; schema is documented in SPEC-212-a. Seeded global profiles are good clone templates — duplicate one and edit the fields you need."

with:

> "Aggregation profiles describe how to roll up data across a group of documents. They drive features like deduplicated lists with summed quantities, sprint-points totals, time tracker rollups, expense reports. Pick a seeded profile as a starting point and duplicate-and-edit it for your use case."

Same on the admin home page card description.

### 5.2 Clone-from-existing in the aggregation-profile editor (O7)

Add a parallel **+ Clone from existing** action next to **+ New profile** in `AggregationProfileEditor.svelte`:

- Click → small inline picker lists in-scope profiles (globals + same-set).
- Selecting one prefills the editor with that profile's name (+ " (copy)"), description, and `profile_data`.
- User edits → Save creates a new row (set-scoped if invoked from set page; global if from admin page — matches the editor's existing scope rules).

### 5.3 Clone-from-existing for element templates (C4)

Add the parallel UX on the **elements list** page:

- Today the `/elements` page has a **Templates** button → `TemplatesListDialog` lists templates with a **"Use"** action that creates a *new element* from the template.
- Extend `TemplatesListDialog` with a second action **"Clone template"** next to **Use** on each row.
- "Clone template" → opens the existing `CreateTemplateDialog` (the "Save as template" flow) prefilled with the source template's name (+ " (copy)") and `markdown_stamp`, ready to edit and save as a new template.

This gives users a symmetric clone affordance for both stampable artefacts — aggregation profiles and element templates.

### 5.4 Rename seeded "Quantified item" → "Ingredient" (C3)

The user has named the workflow domain (Groceries / Recipes / Weekly Meal Plan) and the seeded template should match.

- **Renames the seed name only.** Doesn't change anything in code paths (which never reference the name).
- New idempotent data migration **SQLite m079** / **Supabase m084**: `UPDATE element_templates SET name = 'Ingredient' WHERE id = '<deterministic-quantified-item-uuid>' AND name = 'Quantified item'` (guard on the original name so re-running is a no-op once renamed).
- m075 (SQLite) / m080 (Supabase) seed migrations are **not edited** — they're already applied to live; touching them would not affect existing rows and would inflate the diff. The new m079/m084 covers both pre-existing rows and fresh installs (because the seed m075/m080 runs first creating "Quantified item", then m079/m084 renames it).
- Backend constants in `seed/example_models.py::SEEDED_STAMPS` updated to use "Ingredient" so fresh code paths and any future re-seeds use the new name. (The actual rename comes from the new migration, not from re-running the seed.)
- The stamp body is unchanged — still `{{self:attr:attributes/Quantity/type=}} {{self:attr:attributes/Unit/type}} {{self:name}}`.

### 5.5 Genericness invariant note (ADR-214)

The banned-string list (`scripts/check_aggregation_genericness.py`) **already** has `ingredient` and `ingredients` listed — but the script excludes `backend/app/migrations/` and `backend/app/seed/` AND any `*.md` file. So:

- Seed migration **m079** with literal `'Ingredient'` → allowed (in `migrations/`).
- Constant in `seed/example_models.py` named `"Ingredient"` → allowed (in `seed/`).
- CHANGELOG, ADR, spec mentions → allowed (`.md` files).
- The friendly-copy help text in the editor component must avoid the word — it lives in `frontend/src/lib/components/` which IS scanned. Current planned copy doesn't mention ingredients. ✓

### 5.6 Tests

`frontend/tests/unit/aggregationProfileEditor.test.ts` extended with clone-prefill round-trip.

`frontend/tests/unit/templatesListDialog.test.ts` new — clone-prefill round-trip for element templates.

`backend/tests/test_migrations/test_seed_rename_quantified_to_ingredient.py` new — m079 schema test: row exists with name="Ingredient" after migration; re-running migration is a no-op.

`backend/tests/test_seed/test_example_models.py` updated for the rename if any assertion still expects "Quantified item".

### 5.7 Migration parity (§15)

- **SQLite m079** + **Supabase m084** ship in the same PR.
- Both idempotent: SQLite `UPDATE ... WHERE name = 'Quantified item'`; Supabase same. Re-running after rename has zero affected rows.
- Schema test asserts both halves.

---

## 6. Protocol checklist (per PR)

Per [`docs/protocols.md`](../protocols.md):

| Protocol | PR 11 | PR 12 | PR 13 |
|---|---|---|---|
| §1 ADR | **ADR-215** (stamp body-parsing filter) | **ADR-216** (set-create inherits collection) | _(spec extensions; no new ADR)_ |
| §2 SPEC | SPEC-211-d (stamp filter) | SPEC-216-a (set-create) | SPEC-212-e (profile editor) + SPEC-211-e (template clone) |
| §3 TDD | backend tests | frontend test | frontend + backend tests |
| §4 Feature branch | `feature/stamp-filter-by-attribute` | `feature/set-create-inherits-collection` | `feature/ux-consistency-pass` |
| §5 CHANGELOG | entry | entry | entry |
| §6 Release | tag + GH Release | tag + GH Release | tag + GH Release |
| §7 `{@html}` | none | none | none |
| §8 Context7 | not needed | not needed | not needed |
| §9 Production code | yes | yes | yes |
| §11 Latest deps | no new deps | no new deps | no new deps |
| §12 README | no change | no change | no change |
| §13 DRY | clone-helpers extracted if used by both profile + template clones | no duplication | yes — shared clone logic |
| §14 Surface parity | no new writes | no new writes (frontend-only) | no new writes |
| §15 SQLite ↔ Supabase | no DB changes | no DB changes | **m079 + m084 pair** for the rename |
| ADR-214 genericness | clean | clean | clean (Ingredient in allow-listed paths only) |

---

## 7. Release sequencing

Three feature PRs, each on its own branch, each tagging a minor:

| Version | What |
|---|---|
| **v6.27.0** | PR 11 — stamp body-parsing filter (ADR-215, SPEC-211-d) |
| **v6.28.0** | PR 12 — set creation inherits current collection (ADR-216, SPEC-216-a) |
| **v6.29.0** | PR 13 — UX consistency pass: friendly copy + clone for profiles & templates + Ingredient rename (SPEC-212-e + SPEC-211-e + m079/m084) |

**v6.29.0 is the only one with a DB change** (the m079/m084 rename pair). Supabase ordering per memory `feedback_render_supabase_ordering`:

1. Merge PR 13 (includes both code + migration files).
2. Run `scripts/supabase-migrate.sh "$SUPABASE_DB_URL_DIRECT"` against the live DB. (Or apply m084 directly via `psql -f` as we've done for prior PRs.)
3. The merged code uses the new name in seed constants; existing data is renamed by m084.

Render auto-deploys on merge to main for all three.

---

## 8. Definition of done

After all three PRs ship and the user's live DB has m084 applied:

- The smart-markdown picker only offers stamps whose body-referenced attributes the target element actually has. Sausages → Ingredient stamp only.
- "Create new set" from a collection-filtered view → new set is in the right collection.
- "Aggregation profiles for this set" section has a Clone-from-existing button alongside + New, with friendly help copy.
- Elements list "Templates" dialog has a Clone-template button alongside Use.
- The seeded "Quantified item" stamp is now named "Ingredient" everywhere — pickers, listings, MCP responses, CLI output.
- Genericness invariant still clean; no new `{@html}` paths; SQLite ↔ Supabase parity preserved.
- All issue #211 observations from the 2026-05-22 comment are closed.
