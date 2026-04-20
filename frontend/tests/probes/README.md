# Knowledge-Graph Spread-Slider Probes

Investigation tooling used to characterise the multi-collection spread-slider
force-model fix (ADR-118 / SPEC-118-A). Three variants exercise the slider at
different layers of the stack:

| Script | Mode | What it measures |
|---|---|---|
| `spread-slider-probe.ts` | Fresh reload per spread value | Steady-state metrics after a cold page load. Baseline for target-distance decisions. |
| `spread-slider-live.ts` | Load once, mutate charge+link forces in place | Isolates the contribution of charge+link force scaling (cluster force not updated). |
| `spread-slider-ui.ts` | Load once, drive the DOM slider via input events | Closest to the live user experience; matches the "lose the plot" transition complaint. |

All three scripts import shared helpers from `probe-utils.ts` which reuses
`getAuthToken` and `ADMIN_PASSWORD` from `tests/e2e/fixtures.ts`.

## Prerequisites

The probes read graph state via `window.__irisGraph`, exposed only when
`VITE_IRIS_DEBUG=1` is set **at build time**. For `npm run dev`:

```bash
VITE_IRIS_DEBUG=1 ./scripts/dev.sh restart
```

For the e2e suite (Playwright-managed preview server) the flag is set in
`playwright.config.ts` for the `webServer.command`.

## Running

```bash
# Start backend + frontend with the debug hook
VITE_IRIS_DEBUG=1 ./scripts/dev.sh start

# Seed admin + multi-collection data (≥ 2 collections × 2 sets × 3 root packages)
# either via the app UI or the fixtures.ts helpers (createCollection, createSet,
# createPackage) from tests/e2e/fixtures.ts.

# Baseline fresh-reload sweep
IRIS_ADMIN_PASSWORD=AdminPass123! \
npx tsx frontend/tests/probes/spread-slider-probe.ts --label=1x

# Live-slider charge+link-only sweep
IRIS_ADMIN_PASSWORD=AdminPass123! \
npx tsx frontend/tests/probes/spread-slider-live.ts

# UI-driven slider drag sweep
IRIS_ADMIN_PASSWORD=AdminPass123! \
npx tsx frontend/tests/probes/spread-slider-ui.ts
```

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `FRONTEND_URL` | `http://localhost:5173` | Where the Vite dev server is listening. |
| `BACKEND_URL` | `http://localhost:8000` | Where the FastAPI backend is listening. |
| `IRIS_ADMIN_USERNAME` | `admin` (fixtures default) | Admin username for login. |
| `IRIS_ADMIN_PASSWORD` | fixtures `TestPassword12345` | Admin password. Set to `AdminPass123!` against local dev DB. |
| `IRIS_SINGLE_COLLECTION_ID` | — | If set, also runs the sweep against `/?collection_id=<uuid>` to compare single- vs multi-collection behaviour. |
| `IRIS_PROBE_OUTPUT_DIR` | `tests/probes/output` | Where Markdown results + screenshots land. |

## Output

Results land in `tests/probes/output/` which is git-ignored:

- `output/results.md` — Markdown tables appended by each run
- `output/screenshots/*.png` — viewport captures at key spread values

## Capturing a 1× vs 3× comparison (SPEC-118-A criterion)

To compare the two candidate target-distance scales in
`KnowledgeGraph.svelte`'s cluster force:

1. Set collection/set/package targets to `{400, 150, 80}` (1×) and re-run
   `spread-slider-probe.ts --label=1x`.
2. Set them to `{1200, 450, 240}` (3×) and re-run `spread-slider-probe.ts --label=3x`.
3. Compare the two runs on inter-collection monotonicity, overlap count,
   bbox boundedness, and intra-collection cohesion. See SPEC-118-A § Acceptance
   Criteria for the specific thresholds.
