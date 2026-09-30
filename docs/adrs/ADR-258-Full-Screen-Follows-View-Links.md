# ADR-258: Full Screen Carries Over When Following a Link to Another View

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-258 |
| **Initiative** | Stay in full screen while navigating between linked diagrams |
| **Proposed By** | Product owner (2026-09-30) |
| **Date** | 2026-09-30 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** full screen (focus view) on `/views/[id]`, whose state
has been kept in the URL as `?focus=1` since v6.37.2,

**facing** links to another view that drop that parameter. Linked-diagram
nodes navigate with `goto('/views/<id>')`, and model-ref and markdown
(`iris://diagram/…`) links are plain `<a href="/views/<id>">`. So every hop
from one diagram to another went back to the normal layout,

**we decided to** add a `beforeNavigate` hook on the view page. When focus mode
is on and a `link` or `goto` navigation targets a *different* `/views/<id>`
without `focus=1`, the hook cancels it and calls `goto` again with `focus=1`
added. The rule lives in `focusCarryOverTarget`
(`frontend/src/lib/utils/focusCarryOver.ts`),

**and neglected** (a) appending `?focus=1` at every link site. Rejected: there
are at least four sites spread across several components (canvas nodes,
MarkdownView, the browse handler), and a new site added later would miss it
(protocol §13); (b) keeping focus mode in a global store instead of the URL.
Rejected: it would break the shareable `?focus=1` links that v6.37.2 added,
and it would leak into pages that aren't views,

**to achieve** uninterrupted full-screen browsing across linked diagrams,

**accepting that** the navigation is started twice (cancel, then `goto`). The
existing lock-release `beforeNavigate` hook runs on both attempts. Releasing
the lock twice is harmless. Back/forward (`popstate`) is left alone, so
history entries keep whatever focus state they had.

---

## Consequences

- Frontend only. Leaving full screen still goes through FocusView's exit, which
  rewrites the URL for the same view, and the hook ignores same-view
  navigations.
- Links to non-view pages (elements, packages) are not affected.

## Dependencies

- v6.37.2 / v6.37.3 focus ↔ URL sync.

## References

- Implementation spec: [SPEC-258-A](./specs/SPEC-258-A-Full-Screen-Follows-View-Links.md)
