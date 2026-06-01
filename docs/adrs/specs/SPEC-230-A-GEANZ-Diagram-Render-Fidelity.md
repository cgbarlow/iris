# SPEC-230-A: GEANZ diagram render fidelity

Implements **[ADR-230](../ADR-230-GEANZ-Diagram-Render-Fidelity.md)**.
Living document — updated as the Playwright iterate-loop refines values.

## Ground-truth reference

- Canonical diagram: **CCS.00 Customer Service Delivery capability zone**
  — `/tmp/geanz/EARoot/EA1/EA34.png` (EA page `EA33.htm`).
- Live Iris equivalent: view `e5549ec8-b5c9-4e7b-8710-4ce02b83ceaa` in
  set `7f2521de-d7c8-41ba-982c-d1246ba81428`.
- Colours pixel-sampled from `EA34.png`: zone fill `#ccf2fe`, all
  borders `#4169e1` (royal blue); capabilities/pills white. (The
  imported nodes already carry these in `data.visual`.)

## Archetype → style table

Keyed at import/repair time onto `node.data` (`stereotype` synthetic tag
+ enriched `visual`). The shared renderer stays GEANZ-agnostic; it only
honours `visual` + theme rendering hints.

| archetype | detect (import/repair) | bgColor | borderColor | borderWidth | borderStyle | cornerStyle / radius | italic | hideIcon | hideDescription | label align | zIndex |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zone | name ends `capability zone` **or** `visual.bgColor==#ccf2fe` & large | `#ccf2fe` | `#4169e1` | 3 | solid | radius 14 | no | yes | yes | left | below children |
| capability | default capability | `#ffffff` | `#4169e1` | 2 | solid | radius 10 | no | yes | yes | left | default |
| proposed_capability | label ends `(redirect)` **or** EA dashed line | `#ffffff` | `#4169e1` | 2 | **dashed** | radius 10 | no | yes | yes | left | default |
| theme_pill | `qualifier=='CBC Themes'` **or** name ends `(theme)` | `#ffffff` | `#4169e1` | 1 | **dashed** | **pill** | **yes** | yes | yes | center | default |
| proposed_zone | name `…00a/00b/00c` & dashed | `#ffffff` | `#4169e1` | 2 | **dashed** | radius 14 | **yes** | yes | yes | left | below children |
| note | `entityType=='note'` | `#ffffff` | `#000000` | 1 | solid | radius 0 | no | n/a | (keep) | left | default |

Exact px (borderWidth, radius) are refined against screenshots during
the iterate-loop; the table is the starting point.

## Acceptance criteria

### AC1 — flip is fixed (the regression)
- Open `/views/<ccs00>`; after the `/api/elements/{id}` refresh batch
  resolves, every node's computed `background-color` / `border-color` /
  width is **unchanged** from the first paint. Zone stays `#ccf2fe` and
  ~866×390; capabilities stay white with `#4169e1` border. No node flips
  to white/thin-black/iris-default-uml. Holds in view **and** edit mode.

### AC2 — `NodeVisualOverrides` radius/pill
- `nodeOverrideStyle({cornerStyle:'pill'})` → contains `border-radius:
  9999px`; `nodeOverrideStyle({borderRadius:14})` → `border-radius:
  14px`. Unit-tested.

### AC3 — `ArchimateRenderer` rendering hints
- With theme/ node `hideIcons`/`hideDescription`, the rendered node has
  **no** `.archimate-node__icon` and **no** `.archimate-node__description`.
- `textAlign:'left'` → header is left-aligned. Default (no hints) is
  unchanged from today (icon + description + centred).

### AC4 — `geanz-default` theme seeded
- After startup, `GET /api/themes?notation=uml` includes
  `id='geanz-default'` with `rendering.hideIcons==true`,
  `rendering.hideDescription==true`, `rendering.borderRadius==10`,
  `rendering.textAlign=='left'`, and `element_defaults.capability`
  white/`#4169e1`. Seeds identically on SQLite + Supabase.

### AC5 — import classification + theme_id
- Importing a minimal GEANZ fixture XMI (1 zone + 3 capabilities +
  1 theme-pill + 1 redirect) yields nodes whose `data.visual` matches
  the archetype table (dashed pill is `borderStyle:'dashed'`,
  `cornerStyle:'pill'`, `italic:true`; zone `cornerStyle/ radius` set;
  all `hideIcon`/`hideDescription` true) and the diagram
  `metadata.theme_id=='geanz-default'`; the zone node has a lower
  z-index than its children.

### AC6 — Playwright fidelity assertions
- Per archetype, computed CSS on the rendered node matches the table:
  zone bg `rgb(204,242,254)`, border `rgb(65,105,225)`, solid, radius
  ≈14px; capability bg white, border `rgb(65,105,225)`, solid, radius
  ≈10px; proposed `border-style: dashed`; theme-pill `border-style:
  dashed`, `font-style: italic`, radius ≥ half-height (pill). No icon /
  description SVG/element present on any.
- Screenshot saved to `tests/e2e/uat/screenshots/geanz-ccs00.png` for
  human comparison vs `EA34.png`.

## Files

Frontend
- `frontend/src/routes/views/[id]/+page.svelte` — F1 (refresh guard).
- `frontend/src/lib/canvas/elementToNodeData.ts` — F1 (don't emit
  clobbering `visual`/`notation` when absent on the element).
- `frontend/src/lib/types/canvas.ts` — F2 (`borderRadius`,`cornerStyle`).
- `frontend/src/lib/canvas/utils/visualStyles.ts` — F2 (emit radius).
- `frontend/src/lib/canvas/renderers/ArchimateRenderer.svelte` — F3.
- `frontend/tests/e2e/geanz-render.spec.ts` — F6.
- `frontend/src/lib/canvas/utils/visualStyles.test.ts` — AC2.

Backend
- `backend/app/themes/service.py` — F4 (`geanz-default` seed).
- `backend/app/import_sparx/*` (service/converter/mapper) — F5
  (archetype classification + visual enrichment + theme_id + z-index).
- `backend/tests/test_themes/…` — AC4.
- `backend/tests/test_import_sparx*/…` + fixture XMI — AC5.

Ops
- `scripts/repair_geanz_render.py` — F5 data repair, dry-run default,
  set-scoped to `7f2521de…`.

## Out of scope
- New `geanz` notation / dedicated renderer (ADR-230 alt 3).
- Theme CRUD MCP tool + CLI (the §14 asymmetry is documented, not
  closed, here).
- Relabelling capabilities to EA codes (CCS.01 …); Iris keeps names.
