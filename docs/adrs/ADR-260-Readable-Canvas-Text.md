# ADR-260: Canvas Text Is Readable, and the MCP Tools Say What the Canvas Reads

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-260 |
| **Initiative** | Canvases built through MCP render the text that was stored (issue #315) |
| **Proposed By** | Product owner (2026-10-05) |
| **Date** | 2026-10-05 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** canvases that are built through the MCP tools, where the
model writes node and edge JSON and never sees the rendered result,

**facing** five rendering rules that hid or shrank text while the stored JSON
looked correct:

1. A note's header rendered at 9px (and bare note text at 8px).
2. A node title was held to one line and cut off with an ellipsis. There was
   no tooltip, so a long element name could not be read on the canvas.
3. The UML creation prompts told models to write class members under
   `data.compartments`. The canvas reads `data.attributes` and
   `data.operations`, so those classes showed a header only. Hydration also
   wrote `undefined` over node-level members whenever the element had none.
4. The view page dropped every node's stored height on load, so a boundary
   with a node `width` and `height` collapsed to its header.
5. Edge labels sit on the middle of the line and can cover a node. The keys
   that move a label or bend a line work, but no tool description named them,

**we decided to**:

1. **Notes.** Note text is 12px (`0.75rem`). The header is sized in `em`, so
   a `visual.fontSize` override scales header and body together.
2. **Titles.** `.canvas-node__label` wraps to three lines, then clips with an
   ellipsis. Every title element carries the full name in its `title`
   attribute. That includes UML and ArchiMate titles, which stay on one line
   only inside a fixed-size (imported) node.
3. **Class members.**
   - The UML prompts name `data.attributes` and `data.operations`.
   - `normalize_canvas_data` (ADR-218), which already runs on save, on read
     and inside `patch_diagram`, lifts `data.compartments.{attributes,
     operations, literals}` into the flat keys. A flat key that already exists
     wins. Existing diagrams are fixed on read with no data migration.
   - A node with a top-level `label` and a `data` object that has no label is
     treated as a flat node, and its `data` keys are kept. That is the shape
     the prompt produces.
   - `elementToNodeData` returns only the member keys the element defines, so
     hydration no longer wipes node-level members. It reads
     `element.data.compartments` as a fallback.
4. **Boundaries.** A boundary keeps its stored `height` on load. Every other
   node still drops it and is measured from its content.
5. **Edge layout keys.** One shared text block, `CANVAS_LAYOUT_KEYS`, is part
   of `create_diagram`, `update_diagram` and `patch_diagram`. It names the
   node size rules, the class member keys, and the edge keys `data.label`,
   `data.labelOffsetX`, `data.labelOffsetY` and `data.waypoints`,

**and neglected** (a) keeping notes at 8px for parity with Sparx EA (ADR-087).
Rejected: imported notes show their text through the description, which was
already 12px, so only the header changes; (b) wrapping titles without a limit.
Rejected: a very long name would push a node over its neighbours; (c) letting
the element always overwrite node members, and copying node members to the
element on save instead. Rejected: a diagram save would write new element
versions as a side effect; (d) keeping the stored height for every node.
Rejected: a node shorter than its text would clip its description, which is
why the height was dropped in the first place; (e) moving an edge label
automatically when it overlaps a node. Not done here: it needs a
collision-avoidance design of its own, and the offset and waypoint keys
already let the author place the label,

**to achieve** canvases where the text an MCP client stores is the text a
person can read,

**accepting that** (a) a node with a long title is now taller, so a dense
existing diagram may need its nodes spaced out; (b) when an element stops
defining a member key (for example its last attribute is removed), a copy
stored on a canvas node keeps showing until that diagram is edited. An empty
list on the element clears it.

---

## Consequences

- No schema change and no migration. The creation prompts are re-seeded on
  every startup in both database modes (ADR-132), so protocol §15 is not
  engaged.
- No new endpoint, tool or command, so surface parity (protocol §14) is
  unchanged.
- The stored-node mapping moved out of the view page into
  `storedCanvasNodes.ts`, where it is unit tested.

## Dependencies

- ADR-218 (canvas shape normalisation), ADR-192 (element to node data),
  ADR-248 (hydration from one request), ADR-234 (fixed-size nodes), ADR-048
  (edge labels), ADR-252 (`patch_diagram`).

## References

- Implementation spec: [SPEC-260-A](./specs/SPEC-260-A-Readable-Canvas-Text.md)
- Issue #315
