# ADR-253: Canvases Zoom Out to 5%

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-253 |
| **Initiative** | Let large diagrams be seen whole on the canvas |
| **Proposed By** | Engineering (request from the product owner, 2026-09-24) |
| **Date** | 2026-09-24 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Svelte Flow canvases (`UnifiedCanvas` in browse and
edit mode, `FullViewCanvas`, `ModelCanvas`, `BrowseCanvas`), none of which set
`minZoom`, so all of them used Svelte Flow's default of 0.5. That limit also
caps `fitView`, so a large diagram, such as the 274-node Barlow family tree,
opened at 50% with most of it off screen, and the zoom-out control stopped
there,

**facing** the product owner's request to "zoom out much further … to see more
of my family tree",

**we decided to** add one shared constant, `CANVAS_MIN_ZOOM = 0.05` in
`frontend/src/lib/canvas/zoom.ts`, and pass it as `minZoom` to every
`<SvelteFlow>`. Because `fitView` falls back to the flow's `minZoom`, fit-to-view
(on load, from the Controls button and from the keyboard shortcut) now fits
diagrams up to about 20 viewports across. `maxZoom` stays at the default of 2,

**and neglected** (a) a smaller limit such as 0.01. Rejected: at 5% a node is
already a few pixels across, and going further only adds empty space to lose
the diagram in; (b) setting the limit per diagram or per notation. Rejected: no
diagram type needs a lower limit than another, and a single constant keeps the
canvases consistent; (c) a minimap. Deferred: it would help with navigation, but
it does not replace seeing the whole diagram at once, which is what was asked
for,

**to achieve** an overview of any diagram Iris is likely to hold, from one
fit-to-view click,

**accepting that** node text can't be read below roughly 30% zoom. That is the
expected trade-off for an overview, and zooming back in is unchanged.

---

## Consequences

- Frontend-only; no API, MCP or CLI change (surface parity is unaffected).
- Large diagrams now open fitted to the viewport instead of at 50%.
- The sequence canvas has its own viewport (`useSequenceViewport`) and is
  unchanged.

## Dependencies

- ADR-218 (canvas `fitViewOptions`).

## References

- Implementation spec: [SPEC-253-A](./specs/SPEC-253-A-Canvas-Minimum-Zoom.md)
