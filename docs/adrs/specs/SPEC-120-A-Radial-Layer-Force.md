# SPEC-120-A: Radial Layer Force

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-120-A |
| **ADR** | [ADR-120](../ADR-120-Radial-Layer-Force.md) |
| **Predecessor** | [SPEC-119-A](./SPEC-119-A-Per-Layer-Force-Model.md) |
| **Status** | Approved |
| **Date** | 2026-04-21 |

## Overview

Adds a per-galaxy radial layer force to the custom cluster force in
`frontend/src/lib/components/KnowledgeGraph.svelte`, and replaces the
SPEC-119-A centroid-only `1/dist²` separation at the set and root-package
layers with a **radius-aware inter-galaxy collision** that uses each
galaxy's actual extent.

The goal is two invariants that SPEC-119-A does not express:

1. **Radial hierarchy** — within each galaxy (a collection + its
   descendants), the distance from a node to the collection centre
   strictly increases with descent rank:
   `collection < set < package < diagram < element`.
2. **Bounded galaxy separation** — inter-galaxy target distance scales
   with the actual radius of each galaxy, not a fixed constant.

All other SPEC-119-A decisions (collection-layer bidirectional force
with pull-back, orphan-set `__orphan_<sid>` binding, flat cohesion,
linear spread scaling, `VITE_IRIS_DEBUG` probe hook, two-mode
`applySeparation`) are retained as-is. The `applySeparation` function
and its `inverseSq` branch remain in the codebase — they are still
invoked at the collection layer (bidirectional) and available as a fallback,
but the set/root-package `inverseSq` call sites are removed.

## Layer radii

Each layer has a target radius from its governing collection centroid:

| Layer | Target radius | Rationale |
|---|---|---|
| Collection | `0` | The origin of each galaxy. |
| Set | `R₁ = 120 × link_length × node_spacing` | Same order as the pre-existing Set→Package link distance (60 × link_length). Doubled to give room between set and packages. |
| Package | `R₂ = 240 × link_length × node_spacing` | 2 × R₁. Empirical choice that gives a clean ring between set and diagrams without overcrowding. |
| Diagram | `R₃ = 360 × link_length × node_spacing` | 3 × R₁. Matches the Set→Diagram link distance (120) plus margin — diagrams beyond their packages, within reach of both set and package links. |
| Element | `R₄ = 480 × link_length × node_spacing` | 4 × R₁. Keeps Elements outside Diagrams when users enable that layer. |

Constants `{120, 240, 360, 480}` are deliberately chosen as a simple
arithmetic progression. They can be globally scaled by the user via
`link_length` and `node_spacing` — no new slider.

`R_total = R₄` is the maximum layer radius. It defines each galaxy's
outer extent for the inter-galaxy collision described below.

## Force construction

### Per-galaxy radial force

Added inside the existing `fg.d3Force('cluster', …)` custom force, before
the cohesion pass:

```ts
// Per-galaxy radial ordering. Each node is pulled toward a layer-specific
// radius from its governing collection centroid. Implemented inline (not
// via d3.forceRadial) so the per-collection centroid is re-evaluated each
// tick — d3.forceRadial applies a single origin globally.
const LAYER_RADIUS: Record<string, number> = {
    collection: 0,
    set: 120,
    package: 240,
    diagram: 360,
    element: 480,
};
const radialStrength = 0.15; // alpha-multiplied below; matches cohesion scale
const linkLen = settings.link_length ?? 1.0;
const nodeSpacing = settings.node_spacing ?? 1.0;
const radiusScale = linkLen * nodeSpacing;

for (const n of graphData.nodes) {
    const cid = nodeCollectionMap.get(n.id);
    if (!cid) continue;
    const targetR = (LAYER_RADIUS[n.node_type] ?? 0) * radiusScale;
    if (targetR === 0) continue; // collection: no radial pull
    const col = colCentroids.get(cid);
    if (!col) continue;
    const dx = (n.x ?? 0) - col.x;
    const dy = (n.y ?? 0) - col.y;
    const r = Math.sqrt(dx * dx + dy * dy) || 1;
    const delta = targetR - r;
    const push = radialStrength * alpha * delta;
    // Push along the radial unit vector pointing away from the collection centre.
    n.vx += (dx / r) * push;
    n.vy += (dy / r) * push;
}
```

Strength `0.15` is of the same order as the cohesion `0.03` (both are
flat, alpha-multiplied). The radial force is applied in addition to the
existing forces — it does not replace link, charge, or cohesion. It
shapes the equilibrium radial ordering; intra-layer angular positioning
is still determined by link + charge + cohesion.

### Radius-aware inter-galaxy collision

Replaces the SPEC-119-A `inverseSq` call sites at the set and root-
package layers. The new force acts on collection-level centroids only —
the radial force has already enforced intra-galaxy ordering, so the
inner layers no longer need their own separators.

```ts
// Radius-aware collision between collection galaxies.
// Each galaxy has a total radius = R₄ × scale; the inter-centroid
// target distance = R_total(A) + R_total(B) + padding.
if (colCentroids.size > 1) {
    const rTotal = 480 * radiusScale; // all galaxies have the same R_total
    const padding = 100 * radiusScale;
    const targetDist = 2 * rTotal + padding;
    applySeparation(
        colCentroids, nodeCollectionMap,
        80, targetDist, 'bidirectional',
    );
}
```

This re-uses the existing `applySeparation` `bidirectional` path with a
dynamic target distance — no new code path. The pre-existing fixed-
target `400 × spread` call at the collection layer is **replaced** by
this radius-aware version; there is one collection-layer separation
call, not two. The `floor = -0.2` pull-back is preserved, which anchors
the orphan-set `__orphan_<sid>` contract (nodes whose synthetic
collection group has no real collection centroid still get pulled back
into the main galaxy cluster rather than drifting outward indefinitely).

### Removed SPEC-119-A call sites

```ts
// Removed:
//   applySeparation(setCentroids, nodeSetFull, 50 * spread, 0, 'inverseSq');
//   applySeparation(pkgCentroids, nodeRootPkgMap, 30 * spread, 0, 'inverseSq');
```

Intra-collection set-to-set and package-to-package repulsion is now
handled by the radial layer force (which forbids them from sitting at
the same radius) plus the existing charge force (which handles angular
separation at the same radius). Cross-collection repulsion is handled
by the radius-aware collision at the collection layer.

### Cohesion

Unchanged from SPEC-119-A — flat `0.03 × alpha` pull toward the node's
finest-level cluster centroid (root package, falling back to set). The
radial force adds a perpendicular constraint (radius from collection
centre); the cohesion pull still resolves angular clustering within each
layer.

## Spread / slider behaviour

| Slider | Effect on radial force |
|---|---|
| `node_spacing` | Multiplies all layer radii — the whole galaxy breathes outward. |
| `link_length` | Multiplies all layer radii — same effect as above; both sliders compose. |
| `size_contrast` | No effect on radial force (only affects node visual size). |
| `label_density` | No effect on forces. |

The `spread` term used in SPEC-119-A's strength multipliers no longer
appears in the inner layers (those call sites are removed). It still
scales the collection-layer `targetDist` via `node_spacing`, preserving
ADR-118's linear spread scaling for the outermost force.

## Regression test

Location: `frontend/tests/e2e/knowledge-graph-radial-ordering.spec.ts`.

Uses the same UAT fixture as SPEC-119-A
(`frontend/tests/fixtures/uat-doview-strategy-models-graph.json` —
711 nodes, 1349 edges) injected via Playwright `page.route` with full
hierarchy visibility (no edges hidden).

### Acceptance criteria

After a 15-second simulation settle at `spread=1.0`:

1. **Per-set radial ordering ≥ 80%.** For each set, compute mean
   distance from its packages → set node (`rPkg`) and its diagrams →
   set node (`rDiag`). At least 80% of sets with both packages and
   diagrams must satisfy `rPkg < rDiag`. Pre-fix reality on the UAT
   fixture: 0/11 (0%) — every set had packages further out than
   diagrams.
2. **Global mean ordering.** Weighted-by-count across all sets:
   `mean(rPkg) < mean(rDiag)`. Pre-fix: 170 px vs 145 px — inverted.

Both assertions are relative — no absolute pixel bounds sensitive to
verlet nondeterminism across machines.

## Amendment to the SPEC-118-A multi-collection test

SPEC-118-A's multi-collection spread-slider test
(`knowledge-graph-spread.spec.ts`, multi-collection describe block) has
three assertions. Assertion #1 (bbox area ratio 0.2 → 3.0) needs
re-calibration under SPEC-120-A because each galaxy's layer radii now
scale linearly with `spread`, so both galaxy extent and inter-centroid
distance grow together. In principle area grows as `(3.0/0.2)² = 225×`;
accounting for galaxy-shape anisotropy we bound at **300×** instead of
the original SPEC-118-A 50×. This still catches the original regression
(unbounded cubic amplification that produced ~1000×+ ratios pre-ADR-118)
while tolerating the principled linear-in-spread growth introduced by
the radial force.

Assertion #2 (monotonicity relaxed in SPEC-119-A to endpoint comparison
`high > low`) and assertion #3 (SPEC-119-A's centroid-geometry checks:
max pair > 800 px, min pair > 100 px) remain valid — both test slider
endpoint behaviour which ADR-120 preserves. The change lives in the test
file; SPEC-118-A and SPEC-119-A remain immutable.

The UAT cluster-collapse regression test (SPEC-119-A, `meanRadius <
0.5 × meanInter`, `maxInter > 500 px`) should continue to pass: the
radial force compacts each galaxy more tightly than the old inverse-
square force did, so meanRadius goes down, and the radius-aware
collision produces larger inter-centroid separation at the default
spread.

## Out of scope

- Tuning the `{120, 240, 360, 480}` layer radii — chosen as a simple
  arithmetic progression, revisited only if a real deployment shows a
  failure case.
- Per-node-type radial strength variation — all layers use the same
  `0.15 × alpha` strength; no evidence a differentiated strength helps.
- Promoting the radial force to a d3-force primitive (`d3.forceRadial`)
  — the primitive uses a single global origin; per-galaxy requires an
  inline loop over each collection's centroid.
- Radial force for unscoped (multi-collection, no `collection_id`)
  views — the existing galaxy effect from cohesion and charge is
  adequate; the radial-ordering bug only manifests at UAT scale within
  a single collection.
- Changing the label rendering. Same-tier label overlap suppression is
  a separate bug fix shipped alongside this change (see CHANGELOG) and
  is a frontend layout concern, not a force-model decision.
