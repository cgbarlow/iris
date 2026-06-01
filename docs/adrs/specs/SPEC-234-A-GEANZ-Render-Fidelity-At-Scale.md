# SPEC-234-A: GEANZ render fidelity at scale

Implements **[ADR-234](../ADR-234-GEANZ-Render-Fidelity-At-Scale.md)** (extends ADR-230).

## Render fix
- `frontend/src/lib/canvas/utils/visualStyles.ts`: when `fixedSize` AND `visual.height != null`, emit exact `height: {h}px` (not `min-height`) — keep `box-sizing: border-box`.
- `frontend/src/lib/canvas/renderers/ArchimateRenderer.svelte` (`--fixed`) and `UmlRenderer.svelte` (`--fixed`): ensure the label fits the fixed box — `overflow:hidden`, reduced font / tighter line-height, `-webkit-line-clamp` ellipsis. Tune the font floor in the iterate loop. Non-fixed nodes keep the `min-height` path.

## Scale harness — `frontend/tests/e2e/geanz-render-scale.spec.ts`
- `beforeAll`: import the full `GEANZ Common Business Capabilities Sparx EA model.xml` (repo root) via the import path into a local set; capture `set_id`.
- Enumerate all diagrams via `/api/diagrams/hierarchy?set_id=…` (walk `node_type:'diagram'`).
- Per diagram: `goto /views/{id}`, wait out the post-paint refresh (mirror `geanz-render.spec.ts`), then:
  - collect every `.svelte-flow__node` `getBoundingClientRect()`; assert **no pairwise overlap among siblings** (AABB test, small epsilon for touching borders) and **each child fits inside its parent zone rect**;
  - spot-check ADR-230 archetype computed styles (no regression);
  - screenshot `.svelte-flow__viewport` → `tests/e2e/uat/screenshots/geanz-scale-<name>.png`.
- Ground-truth map: EA exports at `/tmp/geanz/EARoot/EA1/*.png` (e.g. `EA34.png`=CCS.00) by diagram title — for human sign-off only.

## Iterate loop + acceptance gate
Run → list diagrams with overlaps + offending node pairs → refine exact-size render → re-run until **zero overlaps across all diagrams**. Gate = zero overlaps + children within parents + archetype styles hold + screenshots captured. Pixel-diff is NOT a gate.
