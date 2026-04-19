# SPEC-118-A: Multi-Collection Cluster Separation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-118-A |
| **ADR** | [ADR-118](../ADR-118-Multi-Collection-Cluster-Separation.md) |
| **Status** | Approved |
| **Date** | 2026-04-19 |

## Overview

Replaces the hierarchical cluster force in `KnowledgeGraph.svelte`. The previous
model (cubic spread amplification, unbounded `1/dist²` repulsion, cross-collection
firing at every level, inverse-spread cohesion decay) was unstable on
multi-collection graphs — the slider "lost the plot" at both extremes of its
0.2–3.0 range. This spec defines the replacement force model, the hierarchical
gating predicate, target-distance constants, the `VITE_IRIS_DEBUG` probe hook
convention, and the regression-test acceptance criteria.

## Force model

### Bidirectional target-distance separator

Replaces `applySeparation` with a target-distance force. Given a pair of
centroids with distance `dist` and target `target`:

```ts
const rawOverlap = (target - dist) / target;
const overlap = Math.max(-0.2, Math.min(1, rawOverlap));   // clamp
const push    = strength * alpha * overlap;                // signed
const fx = (dx / dist) * push;
const fy = (dy / dist) * push;
```

Key properties:

| Region | Behaviour | Rationale |
|---|---|---|
| `dist < target` | `overlap ∈ (0, 1]` — apply full push apart | Guarantees separation up to the target distance. |
| `dist == target` | `overlap ≈ 0` — no force | Equilibrium. |
| `dist > target` | `overlap ∈ [−0.2, 0)` — apply 20% pull toward target | Stops the layout collapsing in on itself while still letting charge force dominate at long range. |

Floor (`-0.2`) and ceiling (`1`) prevent runaway velocities if the simulation
momentarily diverges far from equilibrium.

### Hierarchical gating

The three hierarchy levels fire with different scopes. Only the collection layer
is allowed to exert cross-collection force:

| Layer | Centroids over | Gate predicate | Purpose |
|---|---|---|---|
| **Collection** | nodes grouped by `collection_id` | _ungated_ — applies between all collection pairs | Pushes entire collections apart in screen space. |
| **Set** | nodes grouped by `set_id` | `setToCol(aId) === setToCol(bId)` | Separates sibling sets within a collection. Cross-collection set pairs are skipped (their collections already separated). |
| **Root package** | nodes grouped by `root_package_id` | `pkgToCol(aId) === pkgToCol(bId)` | Separates sibling package subtrees within a collection. |

The `setToCol` lookup uses the existing `set_membership` edge map; `pkgToCol`
resolves package → set → collection. Centroids with no resolvable collection
fall back to `__orphan_<id>` which is unique per centroid, so orphan pairs never
share a gate group and are effectively skipped.

### Linear spread scaling

Target distances scale linearly with the slider value:

```ts
// spread ∈ [0.2, 3.0], default 1.0
applySeparation(colCentroids, nodeCollectionMap, 80,  TARGET_COLLECTION * spread);
applySeparation(setCentroids, nodeSetFull,      50,  TARGET_SET        * spread, setGate);
applySeparation(pkgCentroids, nodeRootPkgMap,   30,  TARGET_PACKAGE    * spread, pkgGate);
```

Strength coefficients (`80`, `50`, `30`) carry over from the pre-ADR-118 model.
The `* spread * spread * spread` amplification is removed.

### Flat cohesion

Cohesion no longer divides by spread:

```ts
// Before ADR-118: const cohesion = (0.03 / Math.max(spread, 0.2)) * alpha;
const cohesion = 0.03 * alpha;
```

This keeps intra-cluster pull stable as the slider moves. The old inverse decay
made cohesion weakest exactly when the separator was strongest, which was the
second half of the "lose the plot" failure mode.

### Target-distance constants

Constants are empirically chosen from the probe runs in
`frontend/tests/probes/`. The candidate scales compared are the original
baseline (1×) and a widened scale (3×):

| Name | 1× (baseline) | 3× (widened candidate) | Chosen (ADR-118) |
|---|---|---|---|
| `TARGET_COLLECTION` | 400 | 1200 | **_TBD — filled in from probe run in Commit 3_** |
| `TARGET_SET` | 150 | 450 | **_TBD_** |
| `TARGET_PACKAGE` | 80 | 240 | **_TBD_** |

Selection criteria: see § Acceptance Criteria below. The chosen values are
codified as bare numeric literals in the `applySeparation` calls — they are
small enough and load-bearing enough that a named constant would only obscure
the relationship to the strength coefficients.

## Probe hook (`VITE_IRIS_DEBUG`)

To support regression testing of layout geometry (which is not directly visible
through Svelte component state), the force-graph instance is exposed on
`window.__irisGraph` but only when the build-time env flag is set:

```ts
if (import.meta.env.VITE_IRIS_DEBUG === '1') {
    (window as any).__irisGraph = fg;
}
```

Conventions:

- Read at **build time**, not runtime — Vite inlines `import.meta.env.VITE_*`
  during `vite build`. The flag must be set when the production bundle is
  produced, not when the preview server starts.
- Value `'1'` only. Other truthy values do not enable the hook.
- Default off. Production builds never expose the hook.
- Playwright's webServer in `playwright.config.ts` prefixes its `command` with
  `VITE_IRIS_DEBUG=1` so the e2e suite always has the hook; the dev helper
  `./scripts/dev.sh` is invoked with the flag set for probe runs.

## Regression test (`knowledge-graph-spread.spec.ts`)

Location: `frontend/tests/e2e/knowledge-graph-spread.spec.ts`.

Seed: via fixtures helpers `createCollection`, `createSet`, `createPackage`,
`createEntity`, `createRelationship`, seed **≥ 2 collections × 2 sets per
collection × 3 root packages per set** with sufficient hierarchy depth to
reproduce the original chaos. Reuse `seedAdmin` + `getAuthToken`.

Helper: local `setSpread(page, value)` drives the real `<input type="range"
min="0.2" max="3">` via DOM `input` + `change` events (same pattern as the UI
probe).

Readback: `window.__irisGraph.graphData()` nodes + links; metrics computed in
a single `page.evaluate` pass (same function shape as the probes'
`computeMetrics`).

### Acceptance Criteria

The test sweeps three representative spread values — `0.2`, `1.0`, `3.0` — with
an 8-second simulation settle after each change, then asserts:

1. **Bounded bbox growth.** `bbox_w × bbox_h` at `spread=3.0` is ≤ 50× the
   value at `spread=0.2`. Tighter than any practical failure of the pre-ADR-118
   model; loose enough to absorb Verlet settle jitter.
2. **Monotonic inter-collection separation.** Mean of
   `inter_collection_dists` is strictly non-decreasing across
   `0.2 → 1.0 → 3.0`.
3. **No collection-bbox overlap at `spread=3.0`.** For every pair of collection
   bounding boxes at the widest spread value, the boxes are disjoint on at
   least one axis (sanity check that collections remain visually separate).

Relative invariants, not absolute pixel values — the Verlet integrator is
non-deterministic across machines. If flake appears in CI, raise settle time
or mark `test.fixme` with probe screenshots as the acceptance fallback.

## Out of scope

- Tuning `charge` or `link` d3-forces — the cluster force is the documented
  cause; the existing charge/link coefficients are not changed.
- Persisting the target-distance constants as admin-editable settings (ADR-117
  covers slider-exposed values only; these live in code).
- Replacing d3-force with a different layout engine.
