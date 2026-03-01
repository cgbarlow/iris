# ADR-042: Connector Manipulation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-042 |
| **Initiative** | Connector Manipulation (WP-11) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas editor where all edge types (Simple View, UML, ArchiMate) currently render using a single fixed path algorithm (Bezier curves via `getBezierPath`), limiting users to one visual routing style regardless of diagram layout or readability needs,

**facing** the requirement to let users choose how connectors are routed between nodes — straight lines for direct relationships, stepped paths for orthogonal layouts, smooth steps for rounded corners, and bezier curves for organic flows — so that diagrams can be tailored for clarity and aesthetic preference,

**we decided for** adding a `routingType` property to `CanvasEdgeData` that accepts `'default' | 'straight' | 'step' | 'smoothstep' | 'bezier'`, exposing a routing type dropdown in the model detail page toolbar when an edge is selected in edit mode, and having each Simple View edge component read `data.routingType` to select the appropriate path function (`getStraightPath`, `getSmoothStepPath` with `borderRadius: 0`, `getSmoothStepPath`, or `getBezierPath`) from `@xyflow/svelte`,

**and neglected** implementing routing type as a per-edge-type default (would remove user choice), adding a global routing preference in admin settings (too coarse-grained — users need per-edge control), and using custom SVG path algorithms instead of the library's built-in path functions (unnecessary complexity when the library already provides all needed routing algorithms),

**to achieve** per-edge routing type selection that persists with the model data, integrates with undo/redo, and renders correctly across all five Simple View edge types without affecting UML or ArchiMate edges,

**accepting that** this feature is scoped to Simple View edges only in this iteration, and that the routing type dropdown is only visible in edit mode when an edge is selected.

---

## Options Considered

### Option 1: Per-Edge Routing Type with Toolbar Dropdown (Selected)

**Pros:**
- Users can set routing type individually per edge
- Integrates naturally with existing edge selection and toolbar patterns
- Uses @xyflow/svelte's built-in path functions (no custom code needed)
- Persists with model data via existing save mechanism
- Works with undo/redo via existing history system

**Cons:**
- Requires updating all 5 Simple View edge components
- Adds a new toolbar control that is contextually visible

**Why selected:** Provides the most flexible user experience with minimal implementation complexity, leveraging existing library capabilities.

### Option 2: Global Routing Preference in Admin Settings (Rejected)

**Pros:**
- Single configuration point
- Consistent routing across all edges

**Cons:**
- Too coarse-grained — different edges in the same diagram may benefit from different routing
- Requires admin access to change
- Does not support per-diagram customization

**Why rejected:** Diagrams often benefit from mixed routing styles; a global setting is too restrictive.

### Option 3: Per-Edge-Type Default Routing (Rejected)

**Pros:**
- Consistent routing per relationship type
- Fewer choices for users

**Cons:**
- Removes user agency — a "uses" edge might need straight routing in one diagram and bezier in another
- Does not account for layout context

**Why rejected:** The same relationship type may need different routing depending on node positions and diagram layout.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add routing type to edge data and toolbar | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-027 | Edge Selection, Deletion, and Reconnection | Routing type change requires edge selection |
| Depends On | ADR-028 | Canvas Undo/Redo | Routing type changes are undoable |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-042-A | Connector Manipulation | Technical Specification | [specs/SPEC-042-A-Connector-Manipulation.md](specs/SPEC-042-A-Connector-Manipulation.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
