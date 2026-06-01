# ADR-236: Grouped count aggregation for `list_sets`, and mobile-safe picker/control sizing

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-236 |
| **Initiative** | Make the set dropdown populate fast and fix mobile picker/input sizing in the AI chat and import screens |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the import screen's set picker and the AI-chat selectors,
which all read `GET /api/sets`, and of several mobile-layout reports (provider
picker, set picker, view-type selector, and the chat input),

**facing** that (a) `list_sets` took "ages" to populate because it issued **four
`COUNT(*)` queries per set** in a Python loop — O(4N) round-trips, pathological
on Supabase where every `await` is a network hop; and (b) several controls broke
the mobile viewport — the provider dropdown opened off-screen left, the import
set picker overflowed, the view-type selector ran off the right after a notation
was picked, and tapping the chat input triggered iOS Safari's focus auto-zoom,

**we decided to** (1) compute the diagram/element/package/root-package counts in
**four grouped `GROUP BY set_id` queries run once**, mapped to each set by id in
Python (`backend/app/sets/service.py::list_sets` via a `_grouped_counts` helper),
giving byte-for-byte identical output with ~4N → 4 round-trips; and (2) apply
CSS/copy fixes: clamp the provider dropdown to `calc(100vw - 32px)` and re-anchor
it on small screens; make `SetSelector` stack and width-cap on mobile; add
`flex-wrap` + `min-w-0/max-w-full` to the chat creation controls; and add a
single global guard `@media (max-width: 640px){ input,select,textarea{ font-size:16px } }`
in `app.css` so no focused control sits below iOS's 16px zoom threshold (the
viewport meta is left untouched so pinch-zoom still works). The chat "Create
Diagram" button and the view detail "Loading diagram…" text are renamed to
"Create View" / "Loading view…" as part of the ongoing diagram→view wording shift.

**because** the per-set loop was the dominant cost and grouped aggregates are the
standard fix that benefits every `/api/sets` consumer; and a single shared
font-size guard plus localized layout caps fix the mobile breakage at the source
rather than per-component, keeping the change small and DRY.

## Consequences
- The set dropdown (and the sets list page) populate near-instantly on populated
  databases, especially on Supabase. Output is unchanged; counts are mapped per
  set with no cross-set leakage (regression-guarded by
  `tests/test_sets/test_list_sets_counts.py`).
- Mobile: the provider picker, import set picker, and view-type selector stay
  on-screen; focusing the chat input no longer zooms the page.
- The 16px guard slightly enlarges small controls' text on ≤640px screens — an
  intended touch-usability improvement.

## Alternatives considered
- **Restrict the grouped queries with `WHERE set_id IN (…)`**: rejected — dynamic
  placeholder lists complicate the SQLite↔asyncpg adapter; a single global
  `GROUP BY` is simpler and still 4 queries total.
- **Add a lightweight `?counts=false` mode** for the picker: rejected — the
  dropdown shows counts, and the grouped fix removes the cost for everyone.
- **`maximum-scale=1` in the viewport meta** to stop the zoom: rejected — it
  disables pinch-zoom, an accessibility regression. Font-size ≥16px is the
  recommended fix.

## Surface parity (§14) / §15
No endpoints added (parity unaffected). No schema change, so no migration pair;
`GROUP BY` runs on both SQLite and asyncpg, and `list_sets` keeps positional row
access (§15).

## Dependencies
Builds on ADR-158 (set package counts). Touches `backend/app/sets/service.py`,
`frontend/src/lib/components/SetQA.svelte`, `SetSelector.svelte`,
`frontend/src/routes/views/[id]/+page.svelte`, and `frontend/src/app.css`.
