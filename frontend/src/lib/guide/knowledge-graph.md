# Knowledge Graph

The knowledge graph visualises every entity and relationship in the current scope as an interactive force-directed layout. It's embedded on the dashboard and is the primary discovery surface for how content is connected.

![Knowledge graph](/guide/knowledge-graph.png)

## Nodes, edges, colours

Every node is an entity; every edge is a relationship. Node colours:

- 🔴 **Collection** (single centre of each galaxy)
- 🟣 **Set**
- 🟠 **Package**
- 🟢 **Diagram**
- 🔵 **Element** (hidden by default at dashboard scope; toggle on in settings)

Edge types:

- Solid thick — *collection → set*, *set → package*, *set → diagram*
- Solid thin — parent / child within package hierarchy
- Dashed — *diagram → diagram* navigation links

## Hierarchy flow (radial force)

Nodes are laid out in concentric bands around their governing collection centroid:

1. **Collection** at the centre.
2. **Sets** in a close ring.
3. **Packages** further out.
4. **Diagrams** further still.
5. **Elements** at the outer edge (when visible).

This layer ordering is enforced by a radial physics force so `collection → set → package → diagram → element` holds visually even at UAT scale (hundreds of diagrams per set). Multi-collection views show multiple galaxies with radius-aware collision so clusters don't overlap.

## Interaction

- **Drag a node** to reposition it. Released nodes re-settle under physics.
- **Scroll / pinch** — zoom the viewport.
- **Click and drag empty space** — pan the viewport.
- **Click a node** — navigate to that entity's detail page. Read-only users stay on detail; signed-in users land in edit mode if they have permission.
- **Hover a node** for 400 ms — triggers **focus-fade**: unrelated nodes dim to 10 % opacity so you can follow that node's relationships visually. Move off to restore.

Zoom to fit: **Fit** button, top-right of the graph area. Reset: **Reset** button.

## Settings panel

A gear icon (top-right of the graph area) opens the settings panel with four sliders and two toggle groups:

### Sliders

- **Spread** (0.2–3.0×) — overall scale. Low values produce a compact galaxy; high values fan wide and make individual clusters easier to read.
- **Labels** (1–50, default 10) — max labels per zoom tier. Higher values draw more labels at the cost of overlap.
- **Contrast** (0.0–3.0×) — node-size difference between hierarchy levels. 0 = uniform sizes; 1 = default; higher exaggerates collections and suppresses elements.
- **Link length** (0.5–2.0×) — multiplier on every link's target distance. Affects the radial band widths.

### Visibility toggles

- **Node types** — toggle Collections / Sets / Packages / Diagrams / Elements on or off. Useful: at dashboard scope, turn off Elements to prevent thousands of nodes rendering.
- **Edge types** — toggle Collection → Set, Set → Package, Set → Diagram (a.k.a. "direct diagram links"), Package → Diagram, Diagram → Diagram. Useful: turn off **Direct diagram links** to de-clutter when every set has hundreds of diagrams.

### Persistence

> **User-local** overrides live in `localStorage` per browser, per scope (global / per-collection / per-set). They survive across sessions on the same device.
>
> **Admins can also save a setting as the default** for their scope (**Save as default** button). Defaults cascade: global → collection-specific → set-specific. User overrides always win over admin defaults.

### Reset

**Reset to defaults** button reverts the user's `localStorage` override so admin defaults take over.

## Full screen

A maximise icon sits in the top-right of the graph area. Click to expand the graph to fill the browser viewport; press `Escape` or the exit button to return.

## Performance notes

Iris uses a custom radial-layer force instead of raw d3-force's repulsion. This makes the layout deterministic enough for reliable screenshots and fast enough for sets with hundreds of members. For truly massive datasets (tens of thousands of elements), turn Elements off; the physics stays responsive.

## Next steps

- [Search](search) — when you know the name, search is faster than visual exploration.
- [Dashboard](dashboard) — the default surface that embeds this graph.
- [Admin & Permissions](admin) — setting graph defaults for your team.
