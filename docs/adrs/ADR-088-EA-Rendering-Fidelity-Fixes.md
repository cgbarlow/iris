# ADR-088: EA Rendering Fidelity Fixes

**Status:** Accepted
**Date:** 2026-03-07
**Extends:** ADR-087

## Context

Comparing AIXM 5.1.1 "Main" diagram import against EA ground truth reveals 7 rendering issues that reduce visual fidelity. Aviation industry software demands pixel-accurate rendering.

Issues identified (Round 1-2):
1. Note "Feature Properties" duplicates title in body
2. Attribute text inherits italic from abstract class node
3. Node widths exceed EA dimensions, breaking vertical alignment
4. Composition edges missing arrowhead at target end
5. Edges route from wrong handles when EA says "auto-route"
6. Edge labels (cardinality/role) not correctly positioned
7. Diagram frame fixed in viewport, doesn't zoom/pan

Issues identified (Round 3 — Playwright validation):
8. Node content clipped — UML icon wastes vertical space in fixed-size nodes
9. Package nodes missing from diagrams — skipped during element creation
10. Diagram frame type label shows raw EA type instead of mapped type

## Decision

Fix all 10 issues:

1. **Note dedup:** Strip label prefix from description when building note node data
2. **Italic inheritance:** Add `font-style: normal` to `.uml-node__attr` and `.uml-node__compartment`
3. **Fixed sizing:** Pass `fixedSize=true` to `nodeOverrideStyle()` when visual has width/height
4. **Composition arrows:** Add composition/aggregation to markerEnd when direction is set; fix diamond refX
5. **Handle routing:** Add dual-type handles (source+target on each side); compute auto-handles from node geometry
6. **Label positions:** Parse LLB/LLT/LRT/LRB from EA Geometry; use data-driven offsets in EdgeEndpointLabels
7. **Diagram frame:** Convert from absolute-positioned SVG to a SvelteFlow node that participates in canvas transforms
8. **Fix clipping:** Hide UML icons and reduce padding for fixed-size nodes
9. **Package nodes:** Create Iris elements for Package objects, map as `package_uml`
10. **Frame type label:** Use mapped diagram type (e.g. "class", "pkg") instead of raw EA type (e.g. "Logical", "Package")

## Consequences

- Notes no longer show duplicate titles
- Attribute text always renders upright regardless of abstract class italic
- Nodes size exactly to EA dimensions, maintaining vertical alignment
- Composition edges show both diamond source marker and arrow target marker
- Edges route via geometrically optimal handles when EA specifies auto-routing
- Cardinality and role labels positioned per EA's stored coordinates
- Diagram frame zooms and pans with the canvas
- Fixed-size node content no longer clipped — icons hidden and compact CSS applied
- Package nodes appear on diagrams with their dependency edges
- Diagram frame labels show standard UML type names ("class", "pkg")
