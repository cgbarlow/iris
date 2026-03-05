# SPEC-082-A: Diagram-Type Element Filtering

## Parent ADR
ADR-082: Diagram-Type Element Filtering

## Overview
Implements diagram-type-aware element filtering in the canvas EntityDialog, adds 6 new diagram types to the registry, and provides a user override toggle.

## Backend Changes

### Migration m023 (`backend/app/migrations/m023_new_diagram_types.py`)

**New diagram types:**

| ID | Name | Description | display_order |
|---|---|---|---|
| `use_case` | Use Case | User goals and system interactions | 7 |
| `state_machine` | State Machine | State transitions and lifecycles | 8 |
| `system_context` | System Context | C4 Level 1 — systems and actors | 9 |
| `container` | Container | C4 Level 2 — containers within a system | 10 |
| `motivation` | Motivation | ArchiMate motivation viewpoint | 11 |
| `strategy` | Strategy | ArchiMate strategy viewpoint | 12 |

**Notation mappings for new types:**

| Diagram Type | Notations | Default |
|---|---|---|
| `use_case` | simple, uml | uml |
| `state_machine` | simple, uml | uml |
| `system_context` | simple, c4 | c4 |
| `container` | simple, c4 | c4 |
| `motivation` | archimate | archimate |
| `strategy` | archimate | archimate |

**Quick-win mappings added to existing types:**
- `roadmap`: add `archimate` (default stays `simple`)
- `sequence`: add `c4` (default stays `uml`)

### Registration
Import and call `m023_up` in `backend/app/startup.py` after `m022_up`.

## Frontend Changes

### Filter Constants (`frontend/src/lib/types/canvas.ts`)

Three exported constants define element filtering per diagram type. `null` = no filtering.

**UML_DIAGRAM_TYPE_FILTER** — maps diagram type → allowed UML type keys.

**ARCHIMATE_DIAGRAM_TYPE_LAYERS** — maps diagram type → allowed ArchiMate layers.

**C4_DIAGRAM_TYPE_LEVELS** — maps diagram type → allowed C4 levels.

Simple notation has no filtering (all types always shown).

### EntityDialog (`frontend/src/lib/canvas/controls/EntityDialog.svelte`)

- New prop: `diagramType?: string`
- New state: `showAllTypes = $state(false)` — resets to false on dialog open
- Filtering logic applied after notation-based type computation
- Override checkbox: "Show all types" below the Type dropdown
- When filtering active for ArchiMate: constrain Layer dropdown options
- When filtering active for C4: constrain Scope dropdown options
- Auto-select single remaining layer/scope; hide dropdown if only one option

### DiagramDialog (`frontend/src/lib/components/DiagramDialog.svelte`)

Update `NOTATION_TYPE_FALLBACK` to include new diagram types per notation.

### Diagram Page (`frontend/src/routes/diagrams/[id]/+page.svelte`)

Pass `diagramType={diagram?.diagram_type}` to both EntityDialog instances.

## Test Plan

### Backend (`backend/tests/test_diagrams/test_new_diagram_types.py`)
- 6 new diagram types exist in registry after migration
- Notation mappings correct for each new type
- Quick-win mappings present (archimate→roadmap, c4→sequence)
- Creating a diagram with each new type succeeds

### Frontend (`frontend/tests/unit/diagramTypeElementFilter.test.ts`)
- UML filter returns correct types per diagram type
- ArchiMate filter constrains to correct layers
- C4 filter constrains to correct levels
- free_form always returns null (no filter)
- Simple notation never filters
- Override toggle bypasses filtering
