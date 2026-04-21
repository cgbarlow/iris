# ADR-120: Radial Layer Force

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-120 |
| **Initiative** | Knowledge Graph |
| **Proposed By** | Engineering |
| **Date** | 2026-04-21 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the per-layer force model shipped in v4.0.1 and
refined in v4.0.2–v4.0.3 (ADR-119 / SPEC-119-A) — collection-layer
bidirectional separator with pull-back, ungated `1/dist²` self-decay
repulsion at the set and root-package layers, flat `0.03 × alpha`
cohesion, hierarchical orphan-set `__orphan_<sid>` binding — which
resolved the UAT cluster-collapse regression and restored a recognisable
galaxy effect across collections,

**facing** two residual regressions on UAT-scale single-collection data
(`iris-uat.chrisbarlow.nz`, "DoView Strategy Models" — 11 sets × 60
packages × 639 diagrams): (1) **radial hierarchy inversion** — the new
radial-ordering regression test records 0/11 sets with packages closer to
their set than diagrams (mean package-radius ≈ 170–190 px vs mean
diagram-radius ≈ 140–150 px), so packages visually sit outside their own
children instead of between the set and them, breaking the expected
`set → package → diagram` visual ordering users rely on to read the
graph; and (2) **cross-galaxy bbox overlap** — centroid-only `1/dist²`
repulsion ignores each galaxy's actual extent, so two galaxies whose
centroids are far apart can still visually mingle when their member
clusters are wide,

**we decided for** a **per-galaxy radial layer force**: each node is
pulled toward a prescribed radius from its governing collection centroid
— `Collection=0`, `Set=R₁`, `Package=R₂ > R₁`, `Diagram=R₃ > R₂`,
`Element=R₄ > R₃` — implemented with `d3.forceRadial` per collection
group. Layer radii are derived from the existing link-distance scale
(multiplied by `link_length` and `node_spacing`) so the slider behaviour
remains intuitive and no new tuning constants appear. With a bounded
galaxy radius `R_total = R₄`, inter-galaxy separation becomes a
**radius-aware collision**: target centroid distance = `R_total(A) +
R_total(B) + padding`, replacing the centroid-only `1/dist²` force at the
set and root-package layers. The collection-layer bidirectional
separator, cohesion, orphan-set binding, and the `applySeparation` two-
mode contract from SPEC-119-A are all retained where they still apply;
the SPEC-119-A inner-layer `1/dist²` calls are superseded by this radial
+ radius-aware-collision pair,

**and neglected** (a) an edge-repel force (O(e²) per tick, does not fix
the hierarchy inversion — only affects inter-cluster spacing); (b)
raising the Set→Diagram link distance to push diagrams out past packages
— a fixed constant per deployment, still data-dependent and fragile
across different ratios of diagrams-per-package; (c) adding a per-set
"ring" constraint instead of a per-galaxy radial — more force terms,
harder to compose with the existing charge and link forces, no clear
benefit over a single radial with consistent layer radii; (d) switching
to a tree layout (`d3.tree` / `flextree`) — loses the organic
force-directed aesthetic and breaks the interactive drag / spread slider
affordances,

**to achieve** a force model where the hierarchy ordering is a **first-
class radial invariant** rather than an emergent property of link-length
tuning — packages cannot visually escape their children because they are
mass-pulled to a smaller target radius than diagrams — and where galaxy
separation is **bounded by actual galaxy extent** rather than a fixed
target distance, so the slider behaviour remains predictable across
small multi-collection data and UAT-scale single-collection data without
re-tuning,

**accepting that** a radial force adds a layer of structure absent from
a pure spring-mass layout (some users prefer the "organic" look over
radial bands — offset by the radial strength being low enough that link
forces still shape intra-layer positions), that the layer radii become a
new tuning surface (mitigated by deriving them from `link_length`/
`node_spacing` so they move with existing sliders), that SPEC-119-A's
ungated inner `1/dist²` repulsion is superseded at the set and root-
package layers (the `applySeparation` function's `inverseSq` mode stays
in the codebase — it remains the right tool for future experiments, and
removing it would make restoring SPEC-119-A behaviour non-trivial), and
that the ADR-118 multi-collection spread-slider test's assertion
thresholds may need re-calibration against the new radius-aware
collision shape.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Per-Galaxy Radial Layer Force | `d3.forceRadial` applied per collection group with layer targets `{collection:0, set:R₁, package:R₂, diagram:R₃, element:R₄}` derived from link-length × spacing. Radius-aware inter-galaxy collision replaces centroid-only `1/dist²`: target = `R_total(A) + R_total(B) + padding`. Collection-layer bidirectional separator, cohesion, and orphan-set binding retained from SPEC-119-A. Regression test asserts ≥ 80% of sets lay out with mean package-radius < mean diagram-radius, plus a global-mean check. | [SPEC-120-A](./specs/SPEC-120-A-Radial-Layer-Force.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Refines | ADR-119 | Per-Layer Force Model | Supersedes SPEC-119-A's centroid-only `1/dist²` call sites at the set and root-package layers; retains the `applySeparation` two-mode function (unused `inverseSq` branch remains for reversibility / future work), the collection-layer bidirectional separator, orphan-set `__orphan_<sid>` binding, flat cohesion, linear spread scaling, and the `VITE_IRIS_DEBUG` probe hook. ADR-119 is immutable. |
| Refines | ADR-118 | Multi-Collection Cluster Separation | Preserves the SPEC-118-A gating discipline at the collection layer and the orphan-set hysteresis invariant. |
| Refines | ADR-117 | Graph Settings & Admin Defaults | Radial layer radii track `link_length` and `node_spacing` so the existing sliders continue to control the visible layout. |
| Extends | ADR-116 | Knowledge Graph Visualization | Continues the custom cluster force layer added on top of d3-force. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-120-A | Radial Layer Force | Technical Specification | [specs/SPEC-120-A-Radial-Layer-Force.md](./specs/SPEC-120-A-Radial-Layer-Force.md) |
| SPEC-119-A | Per-Layer Force Model | Predecessor Specification | [specs/SPEC-119-A-Per-Layer-Force-Model.md](./specs/SPEC-119-A-Per-Layer-Force-Model.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-21 |
| Approved | Engineering | 2026-04-21 |
