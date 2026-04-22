# SPEC-132-A: Expanded AI Creation Prompts

**ADR:** [ADR-132](../ADR-132-Expanded-AI-Creation-Notations.md)
**Part:** A — Prompt authoring for Simple, UML, ArchiMate, and C4 creation bundles
**Status:** In Progress

---

## Overview

Authoring conventions and concrete content for the 11 new `ai_creation_prompts` rows that extend AI diagram creation to the four non-DoView notations. All new prompts compose with the existing `creation-base-v1` row (DoView-era base layer) via `build_creation_system_prompt()`. No edits are made to the shipped DoView prompts.

---

## Row inventory

| ID | Layer | Notation | Diagram type | Display order |
|----|-------|----------|--------------|---------------|
| `creation-simple-notation-v1`     | notation     | simple    | —          | 10 |
| `creation-simple-component-v1`    | diagram_type | simple    | component  | 110 |
| `creation-simple-roadmap-v1`      | diagram_type | simple    | roadmap    | 120 |
| `creation-simple-freeform-v1`     | diagram_type | simple    | free_form  | 130 |
| `creation-uml-notation-v1`        | notation     | uml       | —          | 20 |
| `creation-uml-sequence-v1`        | diagram_type | uml       | sequence   | 210 |
| `creation-uml-class-v1`           | diagram_type | uml       | class      | 220 |
| `creation-archimate-notation-v1`  | notation     | archimate | —          | 30 |
| `creation-archimate-process-v1`   | diagram_type | archimate | process    | 310 |
| `creation-c4-notation-v1`         | notation     | c4        | —          | 40 |
| `creation-c4-deployment-v1`       | diagram_type | c4        | deployment | 410 |

All rows: `is_active = 1`, `created_by = 'system'`.

---

## Authoring conventions (shared across all new prompts)

Every new prompt follows the structure proven in `DOVIEW_NOTATION_PROMPT` in `backend/app/seed/creation_prompts.py`. Each section below is mandatory in notation-layer prompts. Diagram-type layer prompts may omit Stage 0 (the notation layer owns setup questions) and focus on layout rules, allowed types, and any diagram-specific refinements.

### Required sections in a notation-layer prompt

1. **One-paragraph introduction** — who you are (expert in this notation), what you create, one sentence on the visual language.
2. **Stage 0 — Setup questions** — 3–6 short questions, one-at-a-time rule. Always includes a "what are we diagramming" opener and a "how should I source the content" question (self-supplied vs general knowledge).
3. **Stage 1 — Structure confirmation** — draft a node list / page list / responsibility map and ask the user to approve before proceeding.
4. **Stage 2 — Detailed content** — present the concrete element roster, relationships/flow, and ask for confirmation.
5. **Stage 3 — Generate JSON** — instruct the model to output only the base-layer JSON schema, no prose, no markdown fences.
6. **Allowed types** — explicit enumerations of `type` values permitted for nodes and edges in this notation. Must match the arrays in `frontend/src/lib/types/canvas.ts` and the filters in ADR-082.
7. **Colour palette** — the notation's theme defaults from the theme seed (ADR-085). Prompts reference hex codes rather than theme-store lookups so the LLM can emit concrete `visual` fields.

### Required sections in a diagram-type-layer prompt

1. **Layout rules** — origin, column/row/lane positions, node sizes, gaps. Concrete numbers so the LLM produces coordinates that render cleanly on first paint.
2. **Allowed element types** — the subset of the notation's entity types valid for this diagram type (per `SIMPLE_DIAGRAM_TYPE_FILTER`, `UML_DIAGRAM_TYPE_FILTER`, `ARCHIMATE_DIAGRAM_TYPE_LAYERS`, `C4_DIAGRAM_TYPE_LEVELS`).
3. **Edge conventions** — which relationship types are used, any routing preferences, marker conventions.
4. **Diagram-specific refinements** — e.g. sequence lifelines start at y=120 and extend downward; class compartments are width-uniform; process lanes have labelled headers.

---

## Per-notation authoring briefs

Each of the four notation-layer prompts is authored to the following intent. Full prompt text lives in `backend/app/seed/creation_prompts.py` as module-level string constants; the migration seeds those strings into rows.

### Simple (creation-simple-notation-v1)

**Intent:** A non-technical, onboarding-friendly view. The user is often not an architect. Setup questions emphasise "what system/process are we describing" rather than notation theory.

- **Allowed node types** (from `SIMPLE_ENTITY_TYPES`): `component`, `service`, `interface`, `actor`, `database`, `navigation_cell`, `note`, `boundary`.
- **Allowed edge types** (from `SIMPLE_RELATIONSHIP_TYPES`): `uses`, `depends_on`, `contains`, `note_link`.
- **Palette:** lean on theme defaults (grey/blue neutrals); allow users to override via follow-up prompts but do not over-specify colours.
- **Language:** lay terms, avoid UML/ArchiMate jargon; "box", "arrow", "group", "person" instead of "component", "aggregation", "actor".

### UML (creation-uml-notation-v1)

**Intent:** Technical readers. The prompt assumes UML literacy, uses canonical names for entity types (class, interface, use case, activity, state, etc.), and references UML relationship semantics accurately.

- **Allowed node types** (from `UML_ENTITY_TYPES`, 11 entries): `class`, `object`, `use_case`, `state`, `activity`, `node`, `interface_uml`, `enumeration`, `abstract_class`, `component_uml`, `package_uml`.
- **Allowed edge types** (from `UML_RELATIONSHIP_TYPES`, 7 entries): `association`, `aggregation`, `composition`, `dependency`, `realization`, `generalization`, `usage`.
- Stage 0 must ask the user which UML diagram type they want (class vs sequence) so the diagram-type selector's value is corroborated in the prompt's own flow.
- When Stage 3 emits compartments for `class` elements, use the `ClassCompartments` shape from `canvas.ts`.

### ArchiMate (creation-archimate-notation-v1)

**Intent:** Enterprise-architecture audience. Prompt respects ArchiMate layer discipline — business, application, technology, motivation, strategy, implementation/migration. Setup asks which layers are in scope so elements are drawn from the right pool.

- **Allowed node types** (from `ARCHIMATE_ENTITY_TYPES`, 45 entries across 6 layers — full list referenced by layer name, not inline).
- **Allowed edge types** (from `ARCHIMATE_RELATIONSHIP_TYPES`, 11 entries): `serving`, `flow`, `triggering`, `access`, `influence`, `archimate_realization`, `archimate_composition`, `archimate_aggregation`, `specialization`, `assignment`, `association_archimate`.
- Stage 0 asks which layer(s) to include; Stage 1 groups elements by layer when presenting the structure.
- Palette: defer to the ArchiMate theme's per-layer tints (business=yellow, application=blue, technology=green, motivation=purple, strategy=red, implementation_migration=grey — draw from theme seed rather than hardcoding numeric hex in the prompt).

### C4 (creation-c4-notation-v1)

**Intent:** Software architecture audience. Prompt enforces the C4 hierarchy (system context → container → component → code) and asks which level is intended.

- **Allowed node types** (from `C4_ENTITY_TYPES`, 9 entries): `person`, `software_system`, `software_system_external`, `container`, `c4_component`, `code_element`, `deployment_node`, `infrastructure_node`, `container_instance`.
- **Allowed edge type** (from `C4_RELATIONSHIP_TYPES`): `c4_relationship` (single type with optional technology annotation — prompt documents the technology field convention).
- Stage 0 asks which C4 level (system_context / container / component / code / deployment); Stage 1 constrains the element roster to the level's allowed types via `C4_DIAGRAM_TYPE_LEVELS`.

---

## Per-diagram-type authoring briefs

### simple/component (creation-simple-component-v1)

- **Allowed types** (from `SIMPLE_DIAGRAM_TYPE_FILTER.component`): `component`, `service`, `interface`, `actor`, `database`.
- **Layout:** rows of components left→right, services above or below the component they belong to, actors on the far left as entry-points, databases on the far right.
- **Default grid:** node size 180×80; x-spacing 240; y-spacing 120; origin (60, 60).
- Encourage grouping with `boundary` elements when the user describes subsystems.

### simple/roadmap (creation-simple-roadmap-v1)

- **Allowed types** (from `SIMPLE_DIAGRAM_TYPE_FILTER.roadmap`): `component`, `service` (representing initiatives or milestones).
- **Layout:** horizontal swim of time periods. X represents time (quarters or phases). Use `boundary` elements as column headers (Q1, Q2, …). Nodes placed inside the appropriate column.
- **Default grid:** column width 260; row height 96; column origin x=60. Use small height (60) nodes to fit more per column.

### simple/free_form (creation-simple-freeform-v1)

- **Allowed types:** all `SIMPLE_ENTITY_TYPES` (filter returns `null` = unrestricted).
- **Layout:** no fixed rules. Prompt instructs the model to pick a sensible layout for the user's described content and ask for layout preferences in Stage 0.

### uml/sequence (creation-uml-sequence-v1)

- **Allowed types** (from `UML_DIAGRAM_TYPE_FILTER.sequence`): `class`, `object`, `component_uml`, `interface_uml`. Also draw `actor` from Simple when an actor is needed (UML notation diagrams permit cross-notation actors per existing pattern).
- **Layout:** lifelines anchored at the top of the canvas (y=60), lifeline heads spaced 180px across. Messages flow downward; each message y-position increments by 80.
- Prompt instructs the LLM to author messages as `dependency` edges with a `label` in edge data (per `CanvasEdgeData.label`).

### uml/class (creation-uml-class-v1)

- **Allowed types** (from `UML_DIAGRAM_TYPE_FILTER.class`): `class`, `object`, `interface_uml`, `enumeration`, `abstract_class`, `package_uml`.
- **Layout:** grid layout, classes 200×140, 260×180 for classes with many attributes. Packages grouping related classes via `boundary`-style containment.
- **Compartments:** prompt specifies attributes/operations are passed via a `compartments: {attributes: [...], operations: [...]}` object in node data, matching `ClassCompartments` in `canvas.ts`.

### archimate/process (creation-archimate-process-v1)

- **Allowed layers** (from `ARCHIMATE_DIAGRAM_TYPE_LAYERS.process`): `business`, `application`, `technology`.
- **Layout:** left-to-right process flow. Business process elements across the middle; triggering business_events positioned before/after. Application_services that back each step placed below their corresponding process step. Technology_services below those when relevant.
- **Default grid:** step width 200; step height 80; x-spacing 260; band y-offsets: business=60, application=220, technology=380.
- Edge type is usually `triggering` between process steps, `serving` between layers (application → business, technology → application).

### c4/deployment (creation-c4-deployment-v1)

- **Allowed levels** (from `C4_DIAGRAM_TYPE_LEVELS.deployment`): `deployment`.
- **Allowed types:** `deployment_node`, `infrastructure_node`, `container_instance`.
- **Layout:** nested containment — regions contain availability zones, which contain hosts/VMs, which contain container instances. Depth-first nesting via `boundary`-style groupings.
- Default sizes: region 600×400, zone 400×260, host 260×160, instance 180×80.

---

## JSON output inheritance

All new prompts rely on `creation-base-v1` for the output schema. They do NOT restate it. The only output-layer instruction diagram-type prompts add is diagram-type-specific hints about `position`, `size`, and `visual` defaults — everything else (top-level `total_pages`, `diagrams[]`, `nodes[]`, `edges[]` shape, `linkedDiagramIndex`) is inherited.

---

## Prompt versioning

- All new rows are suffixed `-v1` in their IDs, matching DoView's precedent.
- Future iterations of a specific prompt land as a new row (`-v2`) with `is_active=0` on `-v1` and `is_active=1` on `-v2`, rather than editing the `prompt_text` in-place. This keeps the prompt lineage auditable and admin-reversible.
- Admin editing of a prompt's text via the admin UI (ADR-094) is still allowed — it updates `prompt_text` directly on the active row. Versioning is only required when we ship a new canonical revision via migration.

---

## Acceptance

- `SELECT layer, notation, diagram_type FROM ai_creation_prompts WHERE is_active=1` returns 15 rows after migration (4 existing DoView-era rows + 11 new).
- `build_creation_system_prompt(db, 'uml', 'sequence')` returns a non-empty string containing the base JSON schema markers AND the UML-notation section header AND the UML sequence layout rules.
- `build_creation_system_prompt(db, 'doview', None)` returns exactly the string it returned pre-migration (DoView unchanged — regression test).
- Same invariant for `('doview', 'outcomes_map')` and `('doview', 'overview')`.
