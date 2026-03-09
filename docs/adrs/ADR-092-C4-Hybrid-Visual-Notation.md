# ADR-092: C4 Hybrid Visual Notation + Canvas & UX Polish

**Status:** Accepted
**Date:** 2026-03-09
**Depends on:** ADR-074, ADR-079, ADR-085, ADR-091

## Context

Current C4 rendering uses Lucide icons combined with Structurizr-style solid filled boxes. The
canonical c4model.com notation uses shape-based type indicators (person silhouette, cylinder for
database, etc.) with colour-coded borders rather than filled backgrounds. Several UX issues have
accumulated: element-type selectors use dropdowns instead of pills, the UI inconsistently uses
"Entity" vs "Element" naming, theme loading causes a visual flash on diagram open, connection
handles are hard to see against coloured nodes, edge routing produces unnecessary bends, and
version history shows past versions without a rollback action.

## Decision

Adopt **Option E: Hybrid** — canonical C4 colours with inline SVG shape glyphs and subtle tinted
fills. Deliver in four parts:

### Part A: C4 Visuals

Replace the current Structurizr solid-fill rendering with canonical C4 hybrid notation:
- **Colour palette:** Use the canonical c4model.com colours — Person (#08427B), Software System
  (#1168BD), Container (#438DD5), Component (#85BBF0) — as border and header colours.
- **Shape glyphs:** Render inline SVG shape indicators inside each node (person silhouette for
  Person, box for Software System, hexagon for Container, circle-dot for Component) instead of
  relying on Lucide icons.
- **Tinted fills:** Apply a subtle 10% opacity tint of the border colour as the node background
  to preserve readability while maintaining visual distinction.
- **Technology label:** Display the `technology` field below the element name in a smaller,
  muted font when present.

### Part B: UX Polish

- **NotationPills:** Replace dropdown selectors for element/relationship types with horizontally
  scrollable pill buttons that show the type name and icon, improving discoverability.
- **"Element" naming:** Standardise all user-facing labels from "Entity" to "Element" for
  consistency with architecture modelling terminology.
- **Theme loading flash:** Defer diagram render until theme data has loaded, showing a skeleton
  placeholder instead of unstyled nodes that snap into place.

### Part C: Canvas Polish

- **Handle visibility:** Increase connection handle size and add a contrasting border so they
  remain visible against dark or coloured node backgrounds.
- **Edge routing:** Switch default edge type from `smoothstep` to `default` (bezier) for C4
  diagrams to reduce unnecessary right-angle bends, while keeping `smoothstep` for UML.
- **Edit mode label:** Show a persistent "Editing" badge in the canvas toolbar when edit mode is
  active, replacing the current icon-only toggle that users overlook.

### Part D: Version History UI

- **Rollback button:** Add a "Restore this version" action to each entry in the version history
  panel. Clicking it creates a new version whose content matches the selected historical version.
- **Diff preview:** Show a summary of changed nodes/edges between the selected version and the
  current version before confirming rollback.
- **Timestamp formatting:** Display relative timestamps ("2 hours ago") with absolute tooltip
  on hover.

## Consequences

- C4 diagrams achieve better visual fidelity to the canonical c4model.com notation.
- Inline SVG glyphs remove the dependency on Lucide icons for C4 type indicators.
- NotationPills improve discoverability of available element and relationship types.
- Consistent "Element" naming reduces user confusion across the UI.
- Improved handle visibility and edge routing produce a cleaner canvas editing experience.
- Version history becomes actionable, enabling users to recover from mistakes without manual
  recreation.
- The theme loading skeleton eliminates the flash of unstyled content on diagram open.
