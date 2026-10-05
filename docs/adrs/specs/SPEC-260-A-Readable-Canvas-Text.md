# SPEC-260-A: Readable Canvas Text

Implements **[ADR-260](../ADR-260-Readable-Canvas-Text.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `frontend/src/lib/canvas/nodes/NoteNode.svelte` | Body `font-size: 0.75rem` (was 8px). Header `1.125em` (was 9px). The header label wraps in full, with no three-line clamp. |
| `frontend/src/app.css` | `.canvas-node__label` wraps to three lines (`-webkit-line-clamp: 3`) instead of `white-space: nowrap`. |
| `frontend/src/lib/canvas/BaseNode.svelte`, `nodes/*.svelte`, `renderers/UmlRenderer.svelte`, `renderers/ArchimateRenderer.svelte` | Title elements carry `title={data.label}`. |
| `frontend/src/lib/canvas/renderers/DoviewRenderer.svelte` | The `wrapLabels` rule turns the clamp off, so DoView titles still wrap in full. |
| `frontend/src/lib/canvas/storedCanvasNodes.ts` (new) | `storedNodesToCanvas`: the stored-node mapping from the view page. A boundary keeps its stored `height`. |
| `frontend/src/routes/views/[id]/+page.svelte` | Calls `storedNodesToCanvas`. |
| `frontend/src/lib/canvas/elementToNodeData.ts` | Returns only the member keys the element defines. Falls back to `element.data.compartments`. |
| `backend/app/diagrams/canvas_normalize.py` | Lifts `data.compartments` into `data.attributes` / `data.operations` / `data.literals`. `flat_node_to_canvas` keeps the flat node's own `data` keys. A node with a top-level `label` and no `data.label` counts as flat. |
| `backend/app/seed/creation_prompts.py` | `UML_NOTATION_PROMPT` and `UML_CLASS_PROMPT` name `data.attributes` and `data.operations`. |
| `mcp/src/iris_mcp/tools.py` | `CANVAS_LAYOUT_KEYS`, added to `create_diagram`, `update_diagram` and `patch_diagram`. |
| `frontend/src/lib/guide/canvas-editing.md` | New section on how text shows on the canvas. |

## 2. Rules

### Class members

`normalize_canvas_data` applies this to every node's `data`:

- For each of `attributes`, `operations` and `literals`: if `data` does not
  have the key and `data.compartments` has it as a list, the list moves to
  `data`.
- `data.compartments` is removed once it is empty. Keys it has that are not
  one of the three stay where they are.
- A node with no `compartments` object is returned as the same object.

Hydration (`hydrateCanvasNodes`) spreads `elementToNodeData(element)` over the
node. A member key the element does not define is absent from that payload,
so the node's own value stays.

| Element defines the key | Node has the key | Canvas shows |
|-------------------------|------------------|--------------|
| yes (including `[]`) | either | the element's value |
| no | yes | the node's value |
| no | no | nothing |

### Node size on load

| Node | `width` | `height` |
|------|---------|----------|
| boundary | stored, else `visual.width`, else measured, else 200 | stored, if present |
| any other | the same | dropped (measured from content) |

### Edge layout keys documented in MCP

`data.label` (`""` hides the label), `data.labelOffsetX`, `data.labelOffsetY`
(pixels from the middle of the line), `data.waypoints` (a list of `{x, y}`
canvas points; `null` in a `patch_diagram` `update_edge` removes it).

## 3. Tests (TDD)

- `frontend/tests/unit/canvasTextReadable.test.ts`: the title rule wraps and
  clamps to three lines; every title element has the tooltip; the note body
  is `0.75rem` and the header is sized in `em`.
- `frontend/tests/unit/storedCanvasNodes.test.ts`: width fallbacks, height
  dropped for ordinary nodes and kept for a boundary.
- `frontend/tests/unit/elementToNodeData.test.ts` and
  `diagramElementHydration.test.ts`: member keys the element does not define
  are left on the node; the element wins for the keys it defines; the
  `compartments` fallback.
- `frontend/tests/e2e/canvas-text-readable.spec.ts`: rendered note font
  sizes, a wrapped title with its tooltip, a boundary at 520 by 300, and
  class members shown for both member shapes after hydration.
- `backend/tests/test_diagrams/test_canvas_normalize.py::TestClassMembers`
  and `test_shape_normalization.py::TestClassMembersNormalized`: the lift, on
  create, on read of an existing diagram, and through `patch_diagram`.
- `backend/tests/test_seed/test_creation_prompts_uml_members.py`: the prompts
  name the keys the canvas reads.
- `mcp/tests/test_canvas_layout_keys_docs.py`: the three tools carry the
  shared guidance.

## 4. Acceptance criteria

- A note's text is readable at 100% zoom (12px or larger).
- A long element name wraps on the canvas and shows in full on hover.
- A class created by following the UML creation prompt shows its attributes
  and operations, and keeps them after hydration.
- A boundary with a node `width` and `height` renders at that size.
- The MCP tool descriptions list the edge layout keys.
