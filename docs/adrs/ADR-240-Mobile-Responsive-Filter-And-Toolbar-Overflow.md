# ADR-240: Mobile-responsive fixes for bookmark filters and the view toolbar

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-240 |
| **Initiative** | Stop the Bookmarks filter dropdowns and the Markdown/Smart Markdown view toolbar from spilling off the right edge on mobile |
| **Proposed By** | Engineering |
| **Date** | 2026-06-08 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the mobile-responsive rollout (ADR-229) whose invariant is
"no page scrolls horizontally at the Pixel 5 viewport (393px)", two surfaces still
leak a desktop layout through:

1. The **Bookmarks** header (`routes/bookmarks/+page.svelte`) is a
   `flex items-center justify-between` row holding the title plus the **Collection**
   and **Set** filter dropdowns. `CollectionSelector` — unlike its sibling
   `SetSelector` — carries **no responsive width constraints**, so its `<select>`
   expands to its content and pushes the row past the viewport.
2. The Markdown/Smart Markdown **view toolbar** (`routes/views/[id]/+page.svelte`)
   gained a **Checklist** button in ADR-239. Its "View group"
   (`ml-auto flex items-center gap-2`) has **no `flex-wrap`**, so with Comments +
   Checklist + Full-screen all present the group overflows the right edge,

**facing** the user report that both surfaces spill horizontally on a phone,

**we decided to** fix both with **layout-only Tailwind changes, no new components or
JS**: (a) bring `CollectionSelector` to byte-for-byte parity with the already-correct
`SetSelector` responsive pattern (`min-w-0 flex-col … sm:flex-row` wrapper;
`w-full min-w-0 max-w-full truncate … sm:w-auto sm:max-w-xs` select); (b) stack the
Bookmarks header on mobile (`flex-col gap-3 sm:flex-row sm:items-center
sm:justify-between`) with a full-width, column filter group that becomes a row at
`sm`; and (c) add `flex-wrap justify-end` to **both** copies of the view-toolbar
"View group" (the sequence and non-sequence toolbars) so the buttons reflow instead
of overflowing,

**and neglected** (1) capping the `<select>` width with a fixed `max-w` only —
rejected because the real fix is letting the row stack/wrap, and `SetSelector`
already encodes the agreed pattern (DRY §13 says reuse it, not invent a second one);
(2) refactoring the two duplicated "View group" blocks into a shared snippet —
deferred as out-of-scope for a layout bug fix; this ADR touches both copies
identically and flags the duplication for a later cleanup; (3) a global CSS
`overflow-x: hidden` guard — rejected because it hides the symptom while leaving the
content clipped/unreachable, violating the WCAG 1.4.10 reflow intent ADR-229 is built
around,

**to achieve** the ADR-229 no-horizontal-overflow invariant on the Bookmarks and
Markdown-view surfaces, with the filter dropdowns stacking under the title and the
toolbar buttons wrapping, all at ≤393px,

**accepting that** the two view-toolbar edits stay duplicated until the snippet
extraction is done, and that the fix is verified by a viewport-overflow assertion
(scrollWidth ≤ clientWidth) rather than pixel-perfect visual diffing.

---

## Consequences

- **No schema, endpoint, MCP, or CLI change.** Pure frontend layout. Surface parity
  (§14) and SQLite↔Supabase parity (§15) are N/A.
- **No `{@html}` change (§7).** No new HTML rendering.
- **DRY (§13).** `CollectionSelector` now shares the `SetSelector` responsive idiom;
  the duplicated view-toolbar block is documented as a known follow-up, not widened.
- **Regression guard.** Two new cases in `no-overflow.mobile.spec.ts` (the ADR-229
  suite) cover `/bookmarks` and a checklist-eligible view, so a future desktop-only
  layout edit re-failing either surface is caught in CI.

## Alternatives considered

See the **and neglected** clause: select-only max-width, snippet extraction, and a
global `overflow-x` guard — each rejected/deferred with rationale.

## Dependencies

- ADR-229 (mobile-responsive rollout; the no-horizontal-overflow invariant and the
  Pixel 5 `mobile` Playwright project).
- ADR-239 (added the Checklist button that tipped the view-toolbar group over).

## References

- Implementation spec: [SPEC-240-A](./specs/SPEC-240-A-Mobile-Responsive-Filter-And-Toolbar-Overflow.md)
