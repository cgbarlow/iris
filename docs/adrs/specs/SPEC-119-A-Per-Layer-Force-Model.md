# SPEC-119-A: Per-Layer Force Model

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-119-A |
| **ADR** | [ADR-119](../ADR-119-Per-Layer-Force-Model.md) |
| **Predecessor** | [SPEC-118-A](./SPEC-118-A-Multi-Collection-Cluster-Separation.md) |
| **Status** | Approved |
| **Date** | 2026-04-20 |

## Overview

Reshapes the force model inside the custom cluster force in
`frontend/src/lib/components/KnowledgeGraph.svelte`. SPEC-118-A applied a
bounded **bidirectional target-distance** separator at every hierarchy
layer (collection / set / root-package). That form works on small-to-medium
multi-collection data (the 336-node ADR-118 regression seed) but **collapses
inner-layer clusters** when the set-level aggregate mass grows beyond the
fixed target distance — observed concretely on UAT's DoView Strategy Models
collection (711 nodes, 11 sets × 60 packages × 639 diagrams) where all 11
per-set diagram clusters settle within a ±100 px radius of the origin.

This spec preserves every other SPEC-118-A decision (hierarchical gating,
orphan-set `__orphan_<sid>` binding, linear spread scaling, flat cohesion,
the `VITE_IRIS_DEBUG` probe hook) and changes **only** the force shape at
the set and root-package layers to self-decaying `1/dist²` repulsion. The
collection layer is unchanged — its pull-back is load-bearing for the
orphan-set contract and top-level compactness is a deliberate design choice.

## Force model

### Per-layer shape

| Layer | SPEC-118-A shape | SPEC-119-A shape | Strength base | Target dist | Spread applied to | Gate |
|---|---|---|---|---|---|---|
| **Collection** | Bidirectional, clamp `[-0.2, 1]` | **Unchanged** | `80` | `400 × spread` | `targetDist` | _ungated_ |
| **Set** | Bidirectional, clamp `[-0.2, 1]` | **`1/dist²` self-decay, repulsion only** | `50` | n/a | `strength` → `50 × spread` | `setToCol(a) === setToCol(b)` |
| **Root-package** | Bidirectional, clamp `[-0.2, 1]` | **`1/dist²` self-decay, repulsion only** | `30` | n/a | `strength` → `30 × spread` | `pkgToCol(a) === pkgToCol(b)` |

### `applySeparation` contract

The function grows a `mode` parameter. Both modes share the same pair loop,
gating predicate, unit-vector projection, and per-group velocity update —
only the scalar `push` expression differs.

```ts
applySeparation(
    centroids: Map<string, Centroid>,
    nodeGroupMap: Map<string, string>,
    strength: number,
    targetDist: number,                   // unused when mode === 'inverseSq'
    mode: 'bidirectional' | 'inverseSq',
    sameOuterGroup?: (aId: string, bId: string) => boolean,
);
```

Inside the inner pair loop, after computing `dx`, `dy`, `dist`:

```ts
let push: number;
if (mode === 'bidirectional') {
    // SPEC-118-A force shape — used at the collection layer only.
    const rawOverlap = (targetDist - dist) / targetDist;
    const overlap = Math.max(-0.2, Math.min(1, rawOverlap));
    push = strength * alpha * overlap;
} else {
    // 'inverseSq' — pure repulsion, no clamp, no pull-back.
    // Self-decays with distance, so the force adapts to whatever cluster
    // equilibrium radius the charge force produces at the actual density.
    push = (strength * alpha) / (dist * dist);
}
const fx = (dx / dist) * push;
const fy = (dy / dist) * push;
// Apply ±(fx, fy) to every node whose nodeGroupMap entry matches aId / bId.
```

### Call sites

```ts
// 1. Collection layer — bidirectional, unchanged from SPEC-118-A.
applySeparation(
    colCentroids, nodeCollectionMap, 80, 400 * spread, 'bidirectional',
);

// 2. Set layer — inverseSq, spread folded into strength.
applySeparation(
    setCentroids, nodeSetFull, 50 * spread, 0, 'inverseSq', setGate,
);

// 3. Root-package layer — inverseSq, spread folded into strength.
applySeparation(
    pkgCentroids, nodeRootPkgMap, 30 * spread, 0, 'inverseSq', pkgGate,
);
```

Passing `targetDist: 0` at the `inverseSq` call sites is a deliberate
unused-parameter convention so the argument-position order stays uniform
across all three calls — easier to read than overloads.

### Why `1/dist²` at inner layers

The inner layers (set, root-package) contain clusters whose equilibrium
radii are **data-driven**: a set with 5 members occupies a small area, a
set with 639 members occupies a large area, and the correct spacing
between them depends on d3-force's charge balance, which scales with node
count and density. `1/dist²` self-decays with distance, so the force
becomes negligible once groups have moved far enough apart — whatever
"far enough" means at the actual density. No tuning per deployment.

The outer layer (collection) contains O(1)–O(5) top-level groups in
practice. Compact top-level screen-space is a deliberate visual design
choice. The bidirectional target-distance form gives that fixed geometry
and anchors the orphan-set contract.

### Spread scaling

Linear spread from SPEC-118-A is unchanged in intent. At the collection
layer, spread scales `targetDist` (as before). At the set and package
layers, spread now scales `strength` instead — `1/dist²` has no target, so
the slider's effect must come from the strength multiplier.

Across the slider's range:

- `spread=0.2` → inner-layer strengths `{10, 6}`: repulsion is weak;
  members compact tightly.
- `spread=1.0` → `{50, 30}` (the pre-ADR-118 baseline).
- `spread=3.0` → `{150, 90}`: repulsion is 3× stronger; clusters spread
  wider but still self-decay, so the layout does not explode the way the
  `spread³` model did.

### What stays from SPEC-118-A

- **Hierarchical gating** at the set and package layers (cross-collection
  repulsion fires **only** at the collection layer).
- **Orphan-set contract**: nodes whose set has no `collection_membership`
  edge get a synthetic `__orphan_<sid>` collection-layer group so the
  collection-layer pull-back binds them.
- **`pkgToCol` gating**: packages inside an orphan set group by
  `__orphan_<sid>` (shared across the set's packages, so package-layer
  separation fires within the orphan set); unparented hierarchy nodes get
  `__orphan_no_set_<pid>`.
- **Flat cohesion** `0.03 * alpha`.
- **`VITE_IRIS_DEBUG` probe hook** exposing `window.__irisGraph`.

## Regression test

Location: `frontend/tests/e2e/uat-graph-reproducer.spec.ts`.

Fixture: `frontend/tests/fixtures/uat-doview-strategy-models-graph.json` —
a captured `/api/graph` response from the UAT DoView Strategy Models
collection. 711 nodes, 1349 edges (11 collection_membership, 699
set_membership, 639 hierarchy). 407 KB.

### Mechanism

Playwright `page.route()` intercepts `/api/graph*` and `/api/graph/settings*`:

- `/api/graph*` returns the fixture's `{nodes, edges}` payload.
- `/api/graph/settings*` returns a settings blob that mirrors the UAT
  user's visibility state: elements hidden, "Direct diagram links"
  unchecked (`direct_diagram_links: false`), node/link defaults.

This bypasses the backend entirely — no seeding, no rate limits, no auth
round-trips past the initial admin login. Deterministic, fast (~35 s),
CI-friendly.

### Acceptance criteria

After a 15-second simulation settle at `spread=1.0`:

1. **Clusters must be tighter than the gaps between them.** Mean per-set
   cluster radius (mean distance from each diagram to its own set's
   centroid, averaged across all sets and diagrams) must be less than
   **0.5 ×** mean pairwise inter-centroid distance. Pre-fix reality on
   the UAT fixture: meanRadius ≈ 142 px, meanInter ≈ 96 px (ratio
   1.48×). Post-fix expectation: ratio < 0.5.
2. **Maximum inter-centroid separation ≥ 500 px.** With 11 sets and 711
   nodes, anything tighter indicates the set-layer separator is capping
   spread. Pre-fix: maxInter ≈ 200 px.

Both assertions are relative — no absolute pixel bounds sensitive to
verlet nondeterminism across machines.

## Amendment to the SPEC-118-A regression test

The SPEC-118-A multi-collection spread-slider test
(`knowledge-graph-spread.spec.ts`, multi-collection describe block) asserts
three invariants at `spread=3.0`. Assertion #3 originally required that
every pair of collection bboxes be disjoint on at least one axis — a
property that implicitly assumed **bounded** inner cluster radii (which
the bidirectional target-distance separator at set and pkg layers
provided). With the SPEC-119-A change to `1/dist²` self-decay at those
inner layers, cluster radii are no longer bounded: at `spread=3.0` on the
ADR-118 regression seed, each collection's inner hierarchy expands wide
enough that bboxes legitimately overlap in 2D even though their centroids
are well-separated. The bbox-disjoint invariant is no longer a reliable
regression guard under the new model.

Assertion #3 is therefore replaced with two principled centroid-geometry
checks. The SPEC-118-A document remains immutable; the change lives in
the test file and is tracked here:

- **Max pair centroid distance at spread=3 ≥ 800 px** — the collection
  layer must produce a visibly spread layout (catches global collapse).
- **Min pair centroid distance at spread=3 ≥ 100 px** — no two
  collections may coincide (catches partial collapse).

Assertions #1 (`bbox area ratio bounded < 50×` across 0.2 → 3.0) and #2
(mean inter-collection distance monotonic non-decreasing) are unchanged.
Their invariants do not depend on inner cluster bounds — they test slider
behaviour across the full 0.2–3.0 range, which remains valid.

The SPEC-118-A orphan-set hysteresis test (assertion: orphan-set centroid
magnitude stays within `3 × max(|collection centroid|) + 800 px`) is
unchanged and continues to pass.

## Out of scope

- Tuning the inner-layer strength constants `{50, 30}`. They carry over
  from the pre-ADR-118 baseline and are deliberately not tuned as part of
  this change.
- Changing the collection-layer force (unchanged from SPEC-118-A).
- Making target distances member-count-aware at the collection layer (see
  ADR-119 alternative (b) — rejected as too complex for expected scale).
- Adding a new slider or admin setting to switch between force modes.
- Running the captured UAT fixture against spread slider extremes (0.2,
  3.0) — the SPEC-118-A regression tests already cover sweep invariants
  on a multi-collection seed; this spec focuses on the steady-state
  cluster-collapse regression at default spread.
