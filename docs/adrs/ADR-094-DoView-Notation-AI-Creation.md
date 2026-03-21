# ADR-094: DoView Notation and AI Diagram Creation System

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-094 |
| **Initiative** | DoView Notation + AI Diagram Creation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-21 |
| **Status** | Proposed |
| **Supersedes** | — |
| **Superseded By** | — |
| **Related ADRs** | ADR-079 (Notation Registry), ADR-081 (Notation-First UX), ADR-085 (Theme System), ADR-093 (AI Model Management) |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris having an extensible notation registry (ADR-079) supporting Simple, UML, ArchiMate, and C4 notations, an AI model management layer (ADR-093) with streaming chat, and a visual theme system (ADR-085), where users need to create outcomes-based theory of change diagrams and want AI-assisted creation workflows for complex multi-diagram models,

**facing** the challenge that DoView (an open methodology by Dr Paul Duignan, DoViewPlanning.org) has a well-defined visual language and question-driven creation methodology not captured by any existing Iris notation, and that manually creating multi-page DoView models (Overview, Final Outcomes, 5–10 subpages, Sources) is complex and time-consuming without AI guidance,

**we decided for** adding DoView as a fifth notation in Iris with its own element types (`outcome_box`, `final_outcome`, `overview_tile`, `source_reference`), relationship type (`causal_link`), diagram types (`outcomes_map`, `overview`), dedicated renderer, and 10-color theme; and simultaneously building a modular AI diagram creation system with database-stored layered system prompts (base + notation + diagram-type + optional override) integrated into the existing Ask AI chat as a "Create Diagram" mode, with DoView as the first supported creation type,

**and neglected** importing DoView files directly from .drawio/.excalidraw formats (avoids a third-party format dependency and format fragmentation), building a separate wizard UI outside of the Ask AI chat (adds surface area; the guided conversation in the AI chat is more natural and extensible), and hardcoding prompts in application code (reduces admin flexibility and prevents live prompt iteration without redeployment),

**to achieve** a fully native DoView authoring experience within Iris, a reusable AI creation infrastructure that any future notation can extend by adding notation/diagram-type prompts, admin-editable prompts allowing prompt engineering without code changes, and multi-diagram generation in one guided conversation flow,

**accepting that** this adds complexity to the AI subsystem (layered prompt composition, a new DB table, a creation-apply endpoint), requires the base prompt to precisely define Iris canvas JSON output format to ensure AI generates valid diagrams, and the DoView renderer is a new frontend component that must be maintained alongside UML/ArchiMate/C4.

---

## Problem Statement

Users working with outcomes-based strategy need a way to create DoView theory-of-change diagrams in Iris. DoView models are multi-page, methodologically structured, and time-consuming to create manually. The existing AI chat is optimised for Q&A over existing content — not for guided creation of new diagrams. Additionally, the question-driven methodology in the DoView skill (11 setup questions, 2 review checkpoints, structured JSON output) requires a different system prompt than the current "assistant for architecture Q&A" mode.

---

## Decision Details

### DoView Notation (Part A)

**Element types:**
| Type | Description | Default color |
|------|-------------|---------------|
| `outcome_box` | A single achieved outcome in causal flow | Pastel yellow (#FFF2CC / #D6B656) |
| `final_outcome` | Ultimate impact — white box with grey top rule | White (#FFFFFF / #CCCCCC) |
| `overview_tile` | Navigation card linking to a subpage | Cycling 10-color palette |
| `source_reference` | Citation or source URL | Light grey (#F5F5F5 / #666666) |

**Relationship type:** `causal_link` — grey (#C8C8C8), 2px, step routing, no special markers.

**Diagram types:**
- `outcomes_map` — left-to-right column flow (default notation: doview)
- `overview` — tile grid with raised Final Outcomes box (default notation: doview)

**Theme:** `doview-default` with full 10-color cycling palette and 10 stereotype overrides (`page_yellow` through `page_white`) for per-subpage color assignment.

### AI Creation System (Part B)

**Prompt layers** (composed in order, override replaces all):
1. `base` — Iris canvas JSON output schema, node/edge structure, coordinate system
2. `notation` — notation methodology (DoView: question flow, This-Then logic, outcome phrasing, subpage rules)
3. `diagram_type` — type-specific layout rules (outcomes_map: column layout, fan-out arrows; overview: tile grid)
4. `override` — replaces all layers (full admin control)

**Endpoints:**
- `POST /api/ai/sets/{set_id}/create-diagram?stream=true` — guided conversation with layered prompt
- `POST /api/ai/sets/{set_id}/create-diagram/apply` — parse AI JSON output → create diagrams in DB

**Frontend:** "Create Diagram" toggle in Ask AI chat. When active: notation selector (DoView), creation-mode visual indicator, and "Create Diagrams" action button after AI signals completion.

---

## Consequences

**Positive:**
- DoView is fully first-class in Iris (notation, theme, renderer, diagram types, seed examples)
- AI creation system is generic — future notations (e.g. "AI-guided ArchiMate motivation diagram") add one DB row per prompt layer, zero code changes
- Prompts are live-editable by admins without redeployment
- Multi-diagram generation (full DoView set) in one conversation

**Negative / Risks:**
- AI JSON output quality depends on LLM capability and prompt precision; malformed output must be handled gracefully
- DoView methodology is copyrighted by Dr Paul Duignan — implementation must comply with DoViewPlanning.org Attribution & Trademark Use Policy
- Prompt storage in DB means prompt history/versioning is not automatic (future work if needed)

---

## Attribution

The DoView® methodology is created by Dr Paul Duignan and is open to use under the [DoView® Planning Attribution & Trademark Use Policy](https://www.doviewplanning.org/trademarkuse). This implementation is not created or endorsed by DoViewPlanning.org.
