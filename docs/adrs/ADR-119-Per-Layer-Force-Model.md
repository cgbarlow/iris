# ADR-119: Per-Layer Force Model

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-119 |
| **Initiative** | Knowledge Graph |
| **Proposed By** | Engineering |
| **Date** | 2026-04-20 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the custom cluster force introduced by ADR-116 and
reshaped by ADR-118 / SPEC-118-A — a three-layer (collection / set /
root-package) bidirectional target-distance separator with fixed targets
`{400, 150, 80} × spread`, hierarchical gating, orphan-set `__orphan_<sid>`
binding, linear spread scaling, and flat `0.03 · alpha` cohesion — which
shipped in v4.0.0 and is well-behaved on the 336-node multi-collection
regression seed,

**facing** a layout regression on UAT-scale single-collection data
(`iris-uat.chrisbarlow.nz`, "DoView Strategy Models" collection — 11 sets ×
60 packages × 639 diagrams, 711 visible nodes with Elements off and "Direct
diagram links" off) where all 11 per-set diagram clusters collapse toward
the graph centre: the captured `/api/graph` response produces a **mean
cluster radius of 142 px against a mean inter-centroid distance of only
96 px** (ratio 1.48×, well above 0.5 where clusters are visually
separable) and a maximum pairwise centroid separation of only ≈ 200 px —
the 11 sets are indistinguishable in screen space, matching the "one big
ball at the centre" symptom users reported,

**we decided for** a **per-layer force model**: the collection layer
keeps ADR-118's bidirectional target-distance separator (top-level
screen-space compactness is a deliberate fixed-geometry design choice,
and orphan-set `__orphan_<sid>` binding depends on the collection-layer
pull-back), but the set and root-package layers revert to the
**self-decaying `1/dist²` repulsion shape** that worked pre-ADR-118.
Linear spread scaling is preserved as a strength multiplier at every
layer; hierarchical gating, orphan-set keying, and flat cohesion are
unchanged,

**and neglected** (a) tuning the inner-layer bidirectional target
constants upward — target distance is a fixed assumption about cluster
sizes and any single constant fails at some data density; (b) scaling
target by member count (`√n` or similar) — still data-dependent, more
complex, couples cohesion to cardinality in a way that makes cluster
maths harder to reason about; (c) removing the inner separators
entirely and relying on charge + links alone — loses the visual grouping
cue; (d) an adaptive model that switches shape across spread values —
added complexity without evidence of benefit over a single well-behaved
per-layer shape,

**to achieve** a force model where the **outer layer** uses fixed
geometry by design (few collections in practice, compact top-level is a
feature) and the **inner layers** are data-independent — they
self-equilibrate to whatever cluster radius d3-force's charge requires
at the actual density of the graph — so the spread slider remains
predictable across both the small multi-collection regression seed
(ADR-118) and large single-collection datasets like UAT without
re-tuning any constants,

**accepting that** the collection layer remains a data-dependent design
choice (rare collection counts make that a safe assumption for now),
that the `1/dist²` form historically caused the "loses the plot"
failure mode when combined with `spread³` amplification and
cross-layer cross-collection firing (both fixed by ADR-118 and
preserved here), that `applySeparation` now carries a mode flag —
adding one branch inside the hot loop to keep both behaviours in one
function for DRY, and that the regression artifact is a captured
`/api/graph` fixture (407 KB of JSON under `frontend/tests/fixtures/`)
which ties the regression test to a specific real-world payload rather
than a parameterisable seed.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Per-Layer Force Model | `applySeparation` gains a `mode: 'bidirectional' \| 'inverseSq'` parameter. Collection layer stays bidirectional (strength `80`, target `400 × spread`, floor `-0.2`). Set layer switches to `inverseSq` (strength `50 × spread`, self-decay). Root-package layer switches to `inverseSq` (strength `30 × spread`, self-decay). Regression test mocks `/api/graph` with a captured UAT fixture; asserts mean cluster radius < 0.5 × mean inter-centroid distance AND max pairwise inter-centroid > 500 px. | [SPEC-119-A](./specs/SPEC-119-A-Per-Layer-Force-Model.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Refines | ADR-118 | Multi-Collection Cluster Separation | Preserves ADR-118's gating, orphan-set `__orphan_<sid>` binding, linear spread scaling, and flat cohesion. Changes only the force shape at the set and root-package layers. ADR-118 is immutable; ADR-119 supersedes its per-layer force-shape decision. |
| Refines | ADR-117 | Graph Settings & Admin Defaults | Keeps the `node_spacing` slider predictable across dataset scales without per-deployment tuning. |
| Extends | ADR-116 | Knowledge Graph Visualization | Continues the custom cluster force layer added on top of d3-force. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-119-A | Per-Layer Force Model | Technical Specification | [specs/SPEC-119-A-Per-Layer-Force-Model.md](./specs/SPEC-119-A-Per-Layer-Force-Model.md) |
| SPEC-118-A | Multi-Collection Cluster Separation | Predecessor Specification | [specs/SPEC-118-A-Multi-Collection-Cluster-Separation.md](./specs/SPEC-118-A-Multi-Collection-Cluster-Separation.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-20 |
| Approved | Engineering | 2026-04-20 |
