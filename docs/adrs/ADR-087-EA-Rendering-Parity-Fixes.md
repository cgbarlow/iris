# ADR-087: EA Rendering Ground Truth Parity

**Status:** Accepted
**Date:** 2026-03-06
**Extends:** ADR-086

## Context

ADR-086 addressed attributes, UML markers, cardinality, role names, and abstract class detection. Comparing the AIXM 5.1.1 "Diagram_Main" import against the EA ground truth reveals remaining gaps:

1. `<<abstract>>` stereotype text shown when EA uses italic-only
2. Class names not centered in header
3. Abstract class names bold+italic instead of italic-only
4. Note elements scaled 1.4x causing overlap with adjacent elements
5. Note background ignoring theme colours
6. SVG markers clipped at certain zoom levels
7. EA connector geometry (waypoints, connection points) not imported
8. No diagram frame/title block
9. Theme selector dropdown not overriding diagram preferred theme
10. ThemeRenderingConfig missing fields for EA-specific rendering
11. Edit mode not persisting theme to diagram metadata

## Decision

Implement fixes across 7 phases to achieve full visual parity with EA's rendering of UML class diagrams:

- **Phase 1:** Fix theme selector priority and expand ThemeRenderingConfig
- **Phase 2:** Suppress type stereotypes, center labels, italic-only abstract names
- **Phase 3:** Remove 1.4x note scale, fix note CSS for EA dimensions
- **Phase 4:** Add overflow:visible to markers, import EA edge geometry
- **Phase 5:** Diagram frame/title block component
- **Phase 6:** Attribute sort option (pos vs alpha)
- **Phase 7:** Edit mode theme persistence

## Consequences

- EA-imported diagrams visually match EA ground truth
- Theme system gains finer rendering control
- Edge rendering supports EA waypoints and connection points
- Diagram frame provides visual context for imported diagrams
