# ADR-118: Multi-Collection Cluster Separation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-118 |
| **Initiative** | Knowledge Graph |
| **Proposed By** | Engineering |
| **Date** | 2026-04-19 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the knowledge graph's hierarchical cluster force introduced alongside ADR-117 (collection / set / root-package separation driven by the `node_spacing` slider), where the force model used a cubic `spread³` amplification, an unbounded `1 / dist²` repulsion, and fired all three hierarchy levels cross-collection,

**facing** reports that the spread slider "loses the plot" once more than one collection is on screen — at high spread the graph explodes (cross-collection set and package layers compound the collection push), at low spread collections and sets collapse into each other, and cohesion is simultaneously weakened by the inverse-spread divisor so the graph cannot settle at extreme slider values,

**we decided for** replacing the repulsion-only separator with a **bidirectional target-distance** force (push when nodes are inside the target distance at full strength, pull back toward it when they drift outside at 20% strength, floor at −0.2 so the charge force still dominates long-range), **gating** set- and package-level separation to centroids that share a collection (cross-collection separation is handled exclusively at the collection layer), and **scaling targets linearly** rather than cubically so slider movement maps to a predictable layout change,

**and neglected** (a) tightening the cubic model's coefficients without changing its shape — the non-linearity is the primary failure mode, not the constants; (b) removing hierarchical separation entirely and relying on charge force alone — loses the intended collection-level visual grouping; (c) making the force switch adaptive (different model at different spread values) — adds complexity with no clear benefit over a single well-behaved model,

**to achieve** predictable, smooth slider behaviour across the full 0.2–3.0 range on multi-collection graphs, with monotonically-growing inter-collection distance and bounded viewport growth, so the slider feels like a direct scale control rather than a chaos knob,

**accepting that** the new model introduces a gating predicate (set→collection and package→collection lookups per centroid pair), the concrete target-distance constants (`{collection, set, package} × spread`) are empirically chosen rather than derived, and exposing `window.__irisGraph` for Playwright regression coverage requires a build-time `VITE_IRIS_DEBUG=1` flag which adds one new environment convention to the frontend.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Multi-Collection Cluster Separation | Force-model changes: bidirectional target-distance separator, hierarchical gating, linear spread scaling, flat cohesion; plus the `VITE_IRIS_DEBUG` probe hook convention and a multi-collection spread-slider regression test. | [SPEC-118-A](./specs/SPEC-118-A-Multi-Collection-Cluster-Separation.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Refines | ADR-117 | Graph Settings & Admin Defaults | Fixes the force model behind the `node_spacing` slider introduced by ADR-117. |
| Extends | ADR-116 | Knowledge Graph Visualization | Changes the custom cluster force layer added on top of d3-force. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-118-A | Multi-Collection Cluster Separation | Technical Specification | [specs/SPEC-118-A-Multi-Collection-Cluster-Separation.md](./specs/SPEC-118-A-Multi-Collection-Cluster-Separation.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-19 |
| Approved | Engineering | 2026-04-19 |
