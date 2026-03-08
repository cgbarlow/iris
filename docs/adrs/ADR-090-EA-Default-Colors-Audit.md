# ADR-090: EA Default Colors and Visual Audit Fixes

**Status:** Accepted
**Date:** 2026-03-07
**Depends on:** ADR-087, ADR-088, ADR-089

## Context

A comprehensive visual audit (ea-audit.mjs, iteration 0) across all 163 imported diagrams
found 651 issues. After classifying root causes:

- **missing_bg_color (144 high):** EA elements with default Backcolor (-1) produce no bgColor
  in API data. `build_node_visual()` returns None when all colors are defaults.
- **missing_edge_visual (40 medium):** EA connectors with default LineColor (-1) produce no
  lineColor in API data. `build_edge_visual()` returns None.
- **edge_stereotype_hidden (3 medium):** Edges with a stereotype but empty label don't show
  the stereotype text.
- **missing_waypoints (146 high):** Expected behavior — EA only stores waypoints for
  manually-routed edges (89% are auto-routed). Not a bug.
- **text_overflow (157 medium):** Expected behavior — CSS ellipsis triggers scrollWidth >
  clientWidth detection. Not a bug.
- **node_overlap (160 medium):** Mostly false positives from parent-child containment.

## Decision

1. **Apply EA default colors**: When EA stores -1 (default), emit the EA default values
   (#FFFFFF background, #000000 border/line) instead of omitting the field.
2. **Show edge stereotype as label**: When an edge has a stereotype but no name, render the
   stereotype with guillemets as the edge label.
3. **Do not change waypoint handling**: Auto-routed edges correctly use SvelteFlow routing.

## Consequences

- 144 diagrams gain correct white backgrounds instead of relying on theme fallback.
- 40 diagrams gain explicit black edge colors.
- 3 edges show their stereotype text.
- Audit false positives (text_overflow, node_overlap, waypoints) remain but are classified
  as expected behavior.
