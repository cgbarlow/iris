# ADR-230: GEANZ diagram render fidelity (stop the theme flip + faithful capability styling)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-230 |
| **Initiative** | Make Iris render the GEANZ Common Business Capabilities set faithfully to the Sparx EA ground-truth |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the GEANZ Common Business Capabilities set
(`set_id=7f2521de-d7c8-41ba-982c-d1246ba81428`, e.g. the CCS.00 view
`e5549ec8-b5c9-4e7b-8710-4ce02b83ceaa`), whose diagrams are imported
from Sparx EA and must look like the EA HTML-report ground-truth
(`/tmp/geanz/EARoot/EA1/EA34.png` for CCS.00): light-cyan capability
**zones** (`#ccf2fe` fill, `#4169e1` royal-blue border, ~3px, rounded),
white **capabilities** (`#4169e1` border, ~2px, rounded), dashed
pill-shaped **theme** elements with italic centred labels, dashed
**proposed/redirect** boxes, and **no ArchiMate icons or description
text** inside the boxes,

**facing** two defects observed on `/views/[id]`:

  1. **The theme flip (primary bug).** The canvas first paints
     correctly — `parseCanvasData()` loads each node's stored
     `data.visual` verbatim (the EA fill/border + explicit
     width/height) — but a few seconds later
     `refreshNodeDescriptions()`
     (`frontend/src/routes/views/[id]/+page.svelte:672-708`,
     added for ADR-192 / issue #164 to live-refresh class
     attributes) re-hydrates every node from its source element via
     `elementToNodeData()` and **unconditionally spreads the result
     over `node.data`** (`:688` `const next = { ...node.data,
     ...hydrated, description: desc }`). For GEANZ elements
     `element.data.visual` is `undefined`
     (`elementToNodeData.ts:53` returns `visual: data.visual`), so the
     spread overwrites the node's themed `visual` with `undefined`
     and its `notation`/size too. The change-guard (`:689-696`)
     diffs only `diffKeys = [label, description, diagramUsageCount,
     attributes, operations, literals, stereotype, qualifier]` —
     **`visual`, `notation` and `entityType` are absent**, so they are
     never protected. With `data.visual` gone, per-node colours vanish,
     the lost explicit width/height forces a SvelteFlow re-measure
     (visible re-layout), and the capability nodes fall back to the
     plain white / thin-black-border / icon look of the
     `iris-default-uml` seed. Editing a GEANZ model shows the same
     fallback. This is the `1.png → 2.png` flip the user reported.

  2. **Fidelity gaps that remain even on the correct first paint.**
     Every GEANZ node is `entityType: 'capability'`, which
     `DynamicNode` routes to `ArchimateRenderer`. That renderer
     **always** draws an ArchiMate grid icon and the description text,
     **centres** the label, and hard-codes `border-radius: 4px`. It is
     also the only renderer that does **not** consume the theme
     `rendering` config (`getThemeRendering`) — unlike `UmlRenderer`,
     `NoteNode`, `BaseNode`. The per-node `visual` override
     (`NodeVisualOverrides`) has no way to express a corner radius or a
     pill shape, and the GEANZ theme-pill / proposed boxes carry no
     `borderStyle: 'dashed'` / `italic` in their stored `visual`. So
     the boxes show icons, descriptions and square-ish corners the
     ground-truth does not have, and theme pills are not dashed pills.

All GEANZ elements share `element_type='capability'` and
`stereotype='ArchiMate_Capability'`, so a theme **cannot** distinguish
zone vs capability vs theme-pill vs proposed by type or stereotype
alone. The three classes are distinguishable only by the per-node
`visual` colours already present (zone `#ccf2fe` vs capability white)
plus naming signals on the node (`qualifier: 'CBC Themes'` and a
`… (theme)` / `… (redirect)` label suffix),

**we decided to** fix the flip at its source and make the renderer +
the per-node `visual` capable of expressing the full GEANZ style, then
populate that style at import time and repair the existing set:

  - **(F1) Stop the flip.** In `refreshNodeDescriptions()`, strip the
    presentation keys (`visual`, `notation`, `entityType`) from the
    hydrated payload before the spread and re-pin the node's own
    values, so only genuine content fields (label, description,
    attributes, operations, literals, stereotype, qualifier,
    diagramUsageCount) are refreshed. Add `visual`/`notation`/
    `entityType` to `diffKeys` as defence-in-depth. The ADR-192/#164
    behaviour (live class-attribute refresh) is fully preserved. Mirror
    the same protect-presentation rule at any other call site that
    spreads `elementToNodeData()` output over a node.

  - **(F2) Give `NodeVisualOverrides` a corner radius + pill.** Add
    `borderRadius?: number` and `cornerStyle?: 'pill' | 'rounded' |
    'sharp'` to the type and emit `border-radius` from
    `nodeOverrideStyle()` (`cornerStyle: 'pill'` → `border-radius:
    9999px`; `borderRadius: n` → `n`px). No theme-config schema change
    needed for radius — it travels on the node.

  - **(F3) Make `ArchimateRenderer` honour rendering hints.** Consume
    `getThemeRendering(notation, preferredThemeId)` like the other
    renderers, and additionally respect per-node `data.hideDescription`
    and a per-node `data.visual.hideIcon`. When the resolved theme sets
    `hideIcons` / `hideDescription` / `textAlign`, or the node sets
    `hideIcon` / `hideDescription`, suppress the icon, suppress the
    description, and align the header accordingly. Honour the node
    `visual.borderRadius` / `cornerStyle` from (F2).

  - **(F4) Add a `geanz-default` theme.** Seed an 8th built-in theme
    (`seed_default_themes()`), notation `uml`, that sets the GEANZ
    palette defaults (`capability` → white fill, `#4169e1` border) and
    `rendering: { hideIcons: true, hideDescription: true, borderRadius:
    10, textAlign: 'left' }`. GEANZ diagrams reference it explicitly
    via `metadata.theme_id='geanz-default'`, which `themeStore`
    respects ahead of the alphabetical `is_default` fallback that today
    wrongly resolves `iris-default-uml`.

  - **(F5) Classify GEANZ archetypes at import + repair existing data.**
    In the Sparx import path, classify each placed node from its name
    suffix + EA fill/line style into one of `geanz_zone`,
    `geanz_capability`, `geanz_proposed_capability`, `geanz_theme_pill`,
    `geanz_proposed_zone`, and enrich its `node.data.visual` with the
    archetype style (dashed for pills/proposed, `cornerStyle: 'pill'` +
    `italic` for pills, `borderRadius` 14/10 for zones/capabilities,
    `hideIcon`/`hideDescription`), set the diagram's
    `metadata.theme_id='geanz-default'`, and lower the **zone** node's
    z-index so it sits behind its child capabilities (EA renders
    children on top of the zone fill). Ship a **targeted, dry-run-first
    data-repair script** (scoped to `set_id=7f2521de…` only, per the
    prod-data-repair-scoping discipline) that applies the same
    enrichment to the already-imported GEANZ diagrams on UAT.

  - **(F6) Prove it with Playwright.** A new
    `frontend/tests/e2e/geanz-render.spec.ts` seeds a CCS.00-shaped
    archimate/capability diagram via the REST fixtures, navigates to
    its view, asserts the **computed** styles per archetype
    (`background-color`, `border-color`, `border-style`,
    `border-radius`, `font-style`, icon/description absence), captures a
    screenshot for human comparison against the EA ground-truth, and —
    the regression for the flip — **re-asserts the same styles after
    the `/api/elements/{id}` refresh batch settles** so a reintroduced
    clobber fails the build.

**because** the flip is a data-clobber bug, not a theme bug — the cure
is to preserve the per-node presentation the cascade
(`themeStore.svelte.ts:4`: *per-element visual wins*) already promises;
and because faithful GEANZ rendering needs per-archetype dash/pill/
radius/label that only the node can carry (uniform type+stereotype rule
out a pure theme solution), with a `geanz-default` theme supplying the
shared icon/description/radius defaults and a stable, explicit
`theme_id` that removes the accidental `iris-default-uml` fallback.

---

## Consequences

**Positive**

- The GEANZ diagrams stop flipping; the first (correct) paint is stable
  through the post-paint element refresh and in edit mode.
- Capability zones, capabilities, theme pills and proposed boxes render
  faithfully to the EA ground-truth (fills, royal-blue borders, dashed
  pills, rounded corners, no icons/descriptions).
- `borderRadius`/`cornerStyle` on `NodeVisualOverrides` and
  rendering-hint support in `ArchimateRenderer` are generic — any EA
  import or manual styling can now express rounded/pill nodes and hide
  icons/descriptions, not just GEANZ.
- A Playwright regression encodes the flip so it can't silently return.

**Negative / risks**

- `ArchimateRenderer` now reads theme context; a wrong `preferredThemeId`
  or missing theme must degrade to today's CSS-layer look (guarded with
  `?? false` defaults).
- The data-repair touches live UAT diagram JSON. Mitigated by strict
  set-scoping, an explicit dry-run that prints a diff, and idempotency
  (re-running yields no change).
- GEANZ archetype classification keys on name suffix (`(theme)`,
  `(redirect)`) + EA fill — a future renamed element could be
  misclassified. Mitigated by also keying on `qualifier='CBC Themes'`
  and the EA line style, and by the classification living only in the
  GEANZ-aware import/repair path, never in the shared renderer.

## Alternatives considered

1. **Mutate `ea-default-uml` or `scenia-default` instead of adding a
   theme.** Rejected: those are `is_default` themes shared by all
   UML/scenia diagrams; repurposing them regresses non-GEANZ content.
   They also can't express per-archetype radius (one global
   `rendering.borderRadius`).

2. **Pure theme solution (no per-node enrichment).** Rejected: all GEANZ
   nodes share type+stereotype, so a theme cannot make only the pills
   dashed/italic or give zones a different radius from capabilities.

3. **Introduce a new `geanz` notation + dedicated renderer.** Rejected
   for now: requires a notations migration, `DynamicNode` routing
   changes and surface ripple, for no gain over reusing
   `capability`/`ArchimateRenderer` with rendering hints. Can be
   revisited if GEANZ diverges further from ArchiMate.

4. **Only fix the flip, leave fidelity.** Rejected: the `/goal`
   explicitly requires Playwright-verified fidelity to the ground-truth;
   the stable first paint still shows icons, descriptions, square
   corners and non-dashed pills.

## Surface parity (§14)

No new backend write endpoint is added (the `geanz-default` theme is
seeded, not exposed via a new route). Theme CRUD (`POST/PUT
/api/themes`) already exists but is invisible to
`check_surface_parity.py` because `theme` is not in `_KNOWN_ENTITIES`;
that pre-existing asymmetry is documented in the script's exception
catalogue as part of this change rather than silently expanded.

## SQLite ↔ Supabase parity (§15)

No schema change — the `themes` table exists since m024 and
`seed_default_themes()` runs on both backends at startup
(`startup.py:205`, `:251-257`) via the same `INSERT OR REPLACE`
upsert, so the new `geanz-default` row seeds identically on SQLite and
Supabase. No new migration file is required; if any column is later
added it must ship the paired SQLite + Supabase migration.

## Dependencies

- Supersedes nothing; depends on ADR-192 (the refresh whose clobber is
  fixed here), the theme system (m024), and the Sparx import path.
- Spec: `docs/adrs/specs/SPEC-230-A-GEANZ-Diagram-Render-Fidelity.md`.
