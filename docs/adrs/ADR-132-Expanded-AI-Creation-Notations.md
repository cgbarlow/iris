# ADR-132: Expanded AI Creation — Scale the DoView Framework to Simple, UML, ArchiMate, and C4

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-132 |
| **Initiative** | AI Diagram Creation Expansion (Issue #22) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-04-22 |
| **Status** | Proposed |
| **Supersedes** | — |
| **Superseded By** | — |
| **Related ADRs** | ADR-094 (DoView + AI Creation), ADR-100 (DoView Element-Backed Nodes), ADR-079 (Notation Registry), ADR-082 (Diagram-Type Element Filtering), ADR-085 (Theme System), ADR-113 (Ask AI Tabbed Layout) |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris shipping a generic AI diagram-creation subsystem via ADR-094 (database-stored layered prompts in `ai_creation_prompts`, streamed through `/api/ai/sets/{id}/ask` in creation mode, materialised via `create_diagrams_from_ai()` into element-backed nodes per ADR-100) that is currently only exercised for the DoView notation, while the other four notations (Simple, UML, ArchiMate, C4) already have fully first-class canvas rendering, element types, relationship types, diagram-type filters (ADR-082), and themes (ADR-085) — but no creation-mode prompts and no UI path to select them,

**facing** the challenge that Iris users asking the AI to create Simple/UML/ArchiMate/C4 diagrams today fall through to an empty system prompt (because no rows exist in `ai_creation_prompts` for those notations) and that the `SetQA.svelte` notation selector is hardcoded to only offer DoView, making the proven DoView creation pattern invisible and unusable for the seven default notation × diagram-type pairs the registry already advertises,

**we decided for** scaling the DoView creation pattern outward by authoring new rows in the existing `ai_creation_prompts` table — 4 notation-layer prompts (simple, uml, archimate, c4) and 7 diagram_type-layer prompts covering the default pair for every non-DoView diagram type in the m020 registry (simple/component, simple/roadmap, simple/free_form, uml/sequence, uml/class, archimate/process, c4/deployment) — and surfacing them via a registry-driven notation + diagram-type selector in the Create Diagram UI, with DoView treated as one option among many and its existing in-prompt branching left intact,

**and neglected** editing or re-authoring any part of the shipped DoView subsystem (rows, prompts, renderer, themes, migrations m027/m028, seed diagrams — all frozen), introducing a new notation such as flowchart/BPMN/ER (would require new element types, renderer, theme, migration — out of scope for issue #22's "most common types available in Iris"), hardcoding the new prompts in Python source in `ai/creation.py` (breaks ADR-094's live-editable admin-control property and Protocol 13 DRY with the existing layered table), producing a single mega-prompt per notation covering all diagram types (would require bespoke branching logic per notation, duplicating the DB's existing diagram_type layer), and making DoView the default selection in the expanded selector (the explicit user direction is that no default is pre-selected),

**to achieve** full coverage of the seven default notation × diagram-type pairs from the m020 registry through AI-assisted creation, a uniform user entry path (single dropdown pair in `SetQA.svelte` instead of notation-specific UI branches), strict preservation of the DoView flow that already ships to customers, continued admin live-editability of every new prompt without redeployment, and a precedent for future notation additions that requires only `ai_creation_prompts` INSERTs rather than code changes,

**accepting that** authoring eleven high-quality guided prompts requires careful per-notation methodology research (setup questions, layout rules, element/edge allowlists that match the per-notation diagram-type filters in `frontend/src/lib/types/canvas.ts:385–429`), the LLM's adherence to the notation-appropriate entity types depends on prompt precision and may need iteration, changing `SetQA.svelte` from a hardcoded DoView dropdown to a registry-driven selector is a visible UX change for current DoView users (one option becomes one among several; no default is pre-selected), and the frontend now has to handle a two-selector state machine (notation then diagram_type, with diagram_type suppressed when DoView is chosen to preserve its internal branching).

---

## Problem Statement

The AI diagram-creation system shipped in ADR-094 was built generically — any notation that gets a row in `ai_creation_prompts` (layer='notation') and any diagram type that gets a row (layer='diagram_type') would compose a working system prompt via `build_creation_system_prompt()`. DoView was the first and only caller, demonstrating the pattern end-to-end.

The other four notations in Iris (Simple, UML, ArchiMate, C4) have every prerequisite already in place:

- Element type definitions in `frontend/src/lib/types/canvas.ts`
- Per-notation renderers in `frontend/src/lib/canvas/renderers/`
- Relationship types and diagram-type filters (ADR-082)
- Themes seeded per notation (ADR-085)
- Backend notation detection and materialisation paths

What they lack is (a) any rows in `ai_creation_prompts`, and (b) a UI path to select them in Create Diagram mode. As a result, the core promise of ADR-094 ("future notations add one DB row per prompt layer, zero code changes") is unrealised for anything other than DoView. Users cannot AI-create a UML sequence diagram, a C4 deployment view, or an ArchiMate process — despite every rendering and storage piece already existing.

Issue #22 asks us to "scale the DoView creation framework out to support the most common types of diagrams available in Iris." This ADR captures the decision on how to do that.

---

## Decision Details

### Scope

Seven new notation × diagram-type bundles, corresponding to the default pair for every diagram type in the m020 registry that is not already a DoView default:

| # | Notation  | Diagram type | Source of allowed element types |
|---|-----------|--------------|---------------------------------|
| 1 | simple    | component    | `SIMPLE_ENTITY_TYPES`, `SIMPLE_DIAGRAM_TYPE_FILTER.component` |
| 2 | simple    | roadmap      | `SIMPLE_ENTITY_TYPES`, `SIMPLE_DIAGRAM_TYPE_FILTER.roadmap` |
| 3 | simple    | free_form    | `SIMPLE_ENTITY_TYPES` (all) |
| 4 | uml       | sequence     | `UML_ENTITY_TYPES`, `UML_DIAGRAM_TYPE_FILTER.sequence` |
| 5 | uml       | class        | `UML_ENTITY_TYPES`, `UML_DIAGRAM_TYPE_FILTER.class` |
| 6 | archimate | process      | `ARCHIMATE_ENTITY_TYPES`, layers per `ARCHIMATE_DIAGRAM_TYPE_LAYERS.process` |
| 7 | c4        | deployment   | `C4_ENTITY_TYPES`, levels per `C4_DIAGRAM_TYPE_LEVELS.deployment` |

DoView's two bundles (`doview/outcomes_map`, `doview/overview`) remain untouched.

### Non-goals (frozen surfaces)

- Rows `creation-doview-notation-v1`, `creation-doview-outcomes-map-v1`, `creation-doview-overview-v1` in `ai_creation_prompts` — no edits, no re-authoring.
- `DoviewRenderer.svelte`, `DoviewEdgeRenderer.svelte`, DoView element types (`outcome_box`, `final_outcome`, `overview_tile`, `source_reference`), `causal_link` edge type, `doview-default` theme, DoView seed diagrams in `seed/example_models.py` — untouched.
- Migrations `m027_doview_notation.py` and `m028_ai_creation_prompts.py` — untouched.
- `build_creation_system_prompt()` and `create_diagrams_from_ai()` in `backend/app/ai/creation.py` — untouched; both are already notation-agnostic.

### New surfaces

- 4 notation-layer prompt rows + 7 diagram-type-layer prompt rows (11 rows total), inserted idempotently via a new migration pair.
- New endpoint `GET /api/diagrams/registry/creation-catalogue` returning the creatable `(notation, diagram_type)` pairs joined against `ai_creation_prompts`.
- Dynamic notation selector in `SetQA.svelte` (currently hardcoded to DoView), plus a new diagram-type selector that is rendered only for non-DoView notations so DoView's in-prompt Stage 0 branching is preserved.

### UI contract

- Default state in Create Diagram mode: both selectors empty. The user must pick a notation before anything else is possible. The send button is disabled until a valid selection is made.
- When a non-DoView notation is selected, the diagram-type selector is rendered and must be set before sending.
- When DoView is selected, the diagram-type selector is hidden; DoView's prompt owns the outcomes_map-vs-overview branching.
- The ask request body always carries `notation`; it carries `diagram_type` only when `notation !== 'doview'`.

### Prompt authoring conventions

All new prompts follow the DoView prompt's Stage 0–3 guided structure (setup questions → structure confirmation → content confirmation → JSON output). They inherit the JSON output schema from `creation-base-v1` unchanged. Each prompt declares allowed `type` values matching `frontend/src/lib/types/canvas.ts` and the per-notation filters from ADR-082. Detailed authoring guidance lives in SPEC-132-A.

---

## Consequences

**Positive:**
- AI-assisted creation reaches full parity with the notations Iris already renders.
- The ADR-094 generic-subsystem promise ("future notations add DB rows, zero code changes") is demonstrated at scale.
- DoView users see no behavioural regression — its prompts and flow are frozen.
- Prompts remain admin-editable via the existing admin surface; no redeployment needed to tune wording.

**Negative / Risks:**
- LLM output quality for any given new bundle depends on prompt precision; first-release prompts will likely iterate. Materialisation already rejects malformed JSON per ADR-094.
- The expanded notation dropdown removes the implicit "DoView only" affordance. Existing DoView users must pick it from a list, where previously there was a single option pre-selected. This is a deliberate choice per issue-22 clarification.
- Eleven new prompts carry eleven new maintenance points for the prompts team. Offset by the fact that the layered structure means the base and notation layers are reused across several diagram types.

**Neutral:**
- Display-order bands are reserved per notation (notation layer: simple=10, uml=20, archimate=30, c4=40; diagram_type layer: 100+ grouped by notation) to keep the admin prompts UI tidy as more are added.

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-094 | DoView Notation + AI Diagram Creation | Generic `ai_creation_prompts` table + creation flow |
| Depends On | ADR-100 | DoView Element-Backed Nodes | Materialiser invariants (entityId / relationshipId on nodes and edges) |
| Relates To | ADR-079 | Notation Registry | Draws creatable pairs from registry |
| Relates To | ADR-082 | Diagram-Type Element Filtering | Per-notation allowed element type sets used by prompts |
| Relates To | ADR-085 | Theme System | Prompts reference per-notation theme colour palettes |
| Relates To | ADR-113 | Ask AI Tabbed Layout | UI surface where the selectors live |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-132-A | Expanded Creation Prompts | Technical Specification | [specs/SPEC-132-A-Expanded-Creation-Prompts.md](./specs/SPEC-132-A-Expanded-Creation-Prompts.md) |
| SPEC-132-B | Creation Type Selector | Technical Specification | [specs/SPEC-132-B-Creation-Type-Selector.md](./specs/SPEC-132-B-Creation-Type-Selector.md) |
| ISSUE-22 | Expanded diagram use cases for Iris AI / Create Diagram | GitHub Issue | https://github.com/cgbarlow/iris/issues/22 |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | TBD | Pending | Spec review + prompt authoring | On release | TBD |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-04-22 |
