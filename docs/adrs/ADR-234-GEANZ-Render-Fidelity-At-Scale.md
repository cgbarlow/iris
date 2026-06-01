# ADR-234: GEANZ diagram render fidelity at scale (exact-size nodes + per-diagram overlap gate)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-234 |
| **Initiative** | Make every imported GEANZ diagram render without overlaps, faithful to the EA layout |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the GEANZ set imported on UAT, where each diagram
reuses the exact EA node positions and sizes,

**facing** that some diagrams render with **overlapping boxes** (e.g. CCO.08
Payroll: 100×70 capability boxes packed 12px apart inside a zone) — because
`nodeOverrideStyle` emits `min-height` (not exact `height`) for fixed-size
nodes "to avoid clipping", so with the GEANZ theme (`wrapLabels`, hidden
description) a long label grows its box past the EA height and collides with
the tightly-packed neighbour,

**we decided to** (extending ADR-230): for nodes that carry an explicit EA
`width` **and** `height`, render at **exact `height`** with `overflow:hidden`
and make the label fit the fixed box (reduced font / tighter line-height /
line-clamp) in the renderers' `--fixed` mode — so a box never exceeds its EA
footprint and the EA layout is reproduced faithfully. Non-fixed (authored)
nodes keep the forgiving `min-height` path. We verify with a new Playwright
**scale harness** that imports the full GEANZ model, renders every diagram,
and asserts **zero sibling bounding-box overlaps** (and children within their
parent zone), iterating the render until all diagrams pass.

**because** Iris already has the EA positions/sizes, so the only thing
breaking fidelity is boxes growing beyond their footprint; clamping them to
exact size reproduces the EA layout by construction. Pixel-identity to the EA
raster is infeasible (different font/layout engine) and is explicitly NOT the
gate — the deterministic, automatable gate is "no overlaps + children fit +
archetype styles hold", with screenshots for human sign-off.

## Consequences
- Imported GEANZ diagrams stop overlapping and match the EA layout.
- A reusable scale harness guards against regressions across all diagrams.
- Risk: clamping to exact height can clip very long labels — mitigated by
  font-shrink/line-clamp tuned in the iterate loop (legibility sub-criterion).
- Authored (non-EA-sized) diagrams are untouched (`min-height` path retained).

## Alternatives considered
- Keep `min-height` and auto-relayout to remove overlaps — rejected (destroys
  the authentic EA layout the user wants).
- Pixel-diff against EA PNGs as the gate — rejected (flaky; raster ≠ HTML).

## Surface parity (§14) / §15
Pure frontend CSS + a new e2e spec. No schema, no endpoints, no migration.

## Dependencies
Extends ADR-230 (GEANZ render fidelity) + SPEC-230-A + `geanz-render.spec.ts`.
Spec: `docs/adrs/specs/SPEC-234-A-GEANZ-Render-Fidelity-At-Scale.md`.
