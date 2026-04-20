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
| **Collection** | nodes grouped by `collection_id` (or `__orphan_<sid>` for orphan-set nodes — see Orphan-set contract below) | _ungated_ — applies between all collection pairs | Pushes entire collections apart in screen space, and binds orphan sets to the same collection-layer neighborhood. |
| **Set** | nodes grouped by `set_id` | `setToCol(aId) === setToCol(bId)` | Separates sibling sets within a collection. Cross-collection set pairs are skipped (their collections already separated). |
| **Root package** | nodes grouped by `root_package_id` | `pkgToCol(aId) === pkgToCol(bId)` | Separates sibling package subtrees within a collection. |

The `setToCol` lookup uses the existing `set_membership` edge map; `pkgToCol`
resolves package → set → collection. See Orphan-set contract for how sets with
no collection (e.g. the "default" set) participate in each layer.

### Orphan-set contract

Every node MUST belong to a collection-layer group. Sets with no
`collection_membership` edge (e.g. the "default" set) get a **shared** synthetic
group key `__orphan_<sid>` (one key per orphan set, shared across all of that
set's nodes). This is load-bearing: the collection layer is the only layer that
fires cross-collection, and the bidirectional separator's 20% pull-back (floor
`-0.2`) is what stops an orphan set drifting outward under charge repulsion
alone.

| Layer | Orphan-set key shape | Effect |
|---|---|---|
| Collection (`nodeCollectionMap`) | `__orphan_<sid>` shared across the orphan set's nodes | Orphan set acts as a one-set synthetic collection; the bidirectional separator pushes it apart from real collections when closer than target and pulls it back when farther — bounds its position to the collection-layer neighborhood. |
| Set gate (`setToCol`) | `__orphan_<sid>` (same sid as above) | Gate never matches a real collection, so the set layer doesn't push orphan sets against real sets. Within one orphan set there is only one set, so it doesn't push against itself either. |
| Package gate (`pkgToCol`) | `__orphan_<sid>` for every package inside the orphan set; `__orphan_no_set_<pid>` for hierarchy nodes whose `sid` cannot be resolved | Packages within an orphan set separate from each other (same gating as packages within a real collection). Truly-unparented hierarchy nodes get per-package keys so they don't all collapse to one synthetic group. |

**Why the fix matters.** Before this contract, orphan-set nodes were excluded
from `nodeCollectionMap` entirely. Nothing at the collection, set, or package
layer touched them; only cohesion (pull to set centroid) and charge (repel from
every node) applied. As spread rose, real collections spread apart under the
collection-layer separator, their combined charge pushed the orphan set outward,
and no counter-force pulled it back. Oscillating the spread slider ratcheted
the orphan set further away on every rise.

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

Constants are empirically chosen from probe runs against the regression-test
seed shape (3 collections × 3 sets × 4 root packages × 3 children × 2
grandchildren ≈ 336 hierarchy nodes). The candidate scales compared are the
original baseline (1×) and a widened scale (3×):

| Name | 1× (baseline) | 3× (widened candidate) | Chosen (ADR-118) |
|---|---|---|---|
| `TARGET_COLLECTION` | 400 | 1200 | **400 (1×)** |
| `TARGET_SET` | 150 | 450 | **150 (1×)** |
| `TARGET_PACKAGE` | 80 | 240 | **80 (1×)** |

**Empirical justification (from `knowledge-graph-spread.spec.ts` runs):**

| Variant | bbox area ratio (3.0 / 0.2) | mean inter-col ratio | Passes regression thresholds |
|---|---|---|---|
| Pre-ADR-118 (cubic `s³`, unbounded 1/dist²) | ≈ 6.6× | ≈ 2.4× | ✓ (but qualitative chaos — see probes) |
| Fix + 3× targets {1200, 450, 240} | ≈ 77× | ≈ 15× | ✗ (bbox ratio blows past 50× threshold) |
| **Fix + 1× targets {400, 150, 80}** | ≈ 9× | ≈ 20× | **✓** |

3× targets over-expand the layout at the spread-slider extremes, producing
bbox area ratios an order of magnitude larger than the 1× variant. The 1×
variant keeps the ratio close to the baseline's level while also smoothing
the transitional chaos reported in the UI probe — both criteria met.

The chosen values are codified as bare numeric literals in the
`applySeparation` calls — they are small enough and load-bearing enough that
a named constant would only obscure the relationship to the strength
coefficients.

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
reproduce the original chaos, **plus one orphan set** (`collection_id` null)
with its own shallow hierarchy to exercise the orphan-set contract. Reuse
`seedAdmin` + `getAuthToken`.

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
4. **Orphan-set stays bounded under hysteresis sweep.** A second test drives
   an up-down-up sweep (`3.0 → 0.2 → 3.0`) and asserts the orphan-set
   centroid magnitude remains within `3 × max(|collection centroid|) + 800`
   px of origin after the final settle. Catches the Orphan-set-contract
   regression: without the `__orphan_<sid>` collection-layer binding, the
   orphan set ratchets outward with each slider rise.

Relative invariants, not absolute pixel values — the Verlet integrator is
non-deterministic across machines. If flake appears in CI, raise settle time
or mark `test.fixme` with probe screenshots as the acceptance fallback.

## Out of scope

- Tuning `charge` or `link` d3-forces — the cluster force is the documented
  cause; the existing charge/link coefficients are not changed.
- Persisting the target-distance constants as admin-editable settings (ADR-117
  covers slider-exposed values only; these live in code).
- Replacing d3-force with a different layout engine.
