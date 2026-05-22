# SPEC-212-e: Aggregation profile editor polish

Implements: extension of [SPEC-212-d](./SPEC-212-d-Aggregation-Profile-Editor.md). Addresses observations O6 + O7 from the [2026-05-22 issue #211 comment](https://github.com/cgbarlow/iris/issues/211).

## 1. Friendly copy (O6)

Replace the help text in `AggregationProfileEditor.svelte` and the admin home card description. Both currently mention ADR-212 / SPEC-212-a directly in the UX — fine in spec docs, jarring in product copy.

**Before** (`AggregationProfileEditor.svelte`):

> "Profiles drive the aggregation engine (ADR-212). Edit as JSON; schema is documented in SPEC-212-a. Seeded global profiles are good clone templates — duplicate one and edit the fields you need."

**After**:

> "Aggregation profiles describe how to roll up data across a group of documents — deduplicated lists with summed quantities, points totals, time-tracking rollups, and so on. Pick a seeded profile as a starting point with **Clone from existing** and duplicate-and-edit it for your use case, or start blank with **New profile**."

**Admin home card before**:

> "Manage global aggregation profiles (ADR-212) — rulesets that drive cross-document rollups (sum / count by attribute, optionally scaled by a multiplier)."

**After**:

> "Manage global aggregation profiles — rulesets that roll up data across many documents (summed quantities, points totals, time-tracking, expenses, and so on)."

Neither mentions ADR/SPEC IDs. Genericness invariant (`ingredient` etc.) still clean — the copy uses generic concepts ("documents", "groups", "totals").

## 2. Clone-from-existing (O7)

A parallel **+ Clone from existing** button alongside **+ New profile**:

- Clicking opens an inline picker listing in-scope profiles (set-scoped + globals).
- Selecting a row prefills the editor with `name + " (copy)"`, `description`, and `profile_data`.
- `is_default_for_set` resets to `false` on the copy.
- User customises and saves → POST `/api/aggregation/profiles` with the appropriate scope (set-scoped when invoked from the set page; global when invoked from admin).

The editor's existing scope rules apply unchanged — a clone is always created in the parent's scope, never inheriting the source's scope. (A user cloning the global "Shopping list" while on the Recipes set edit page gets a set-scoped copy in Recipes.)

### State additions to `AggregationProfileEditor.svelte`

```ts
let cloning = $state(false);
let cloneCandidates = $state<AggregationProfile[]>([]);

async function startClone() { ... fetch candidates ... }
function cancelClone() { ... }
function commitClone(source: AggregationProfile) {
  creating = true;
  draftName = `${source.name} (copy)`;
  draftDescription = source.description ?? '';
  draftJson = JSON.stringify(source.profile_data, null, 2);
  draftIsDefault = false;
  draftError = null;
}
```

When the editor is in set-mode, `startClone` re-fetches with `include_global=true` so the user can clone from a seeded global (the typical use case: "give me a recipe-set copy of the Shopping list profile to customise").

## 3. Tests

`frontend/tests/unit/aggregationProfileEditor.test.ts` extended with:

- Clone state transitions: `startClone` → `cloning=true`, candidate list populated; `commitClone` → editor open in create mode with prefilled name/description/json.
- Default-for-set is reset on a clone (never inherits).
- The cloned name suffix is `" (copy)"`.
