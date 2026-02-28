# ADR-011: Canvas Integration and Testing Strategy

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-011 |
| **Initiative** | Canvas Integration and Testing Strategy |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas subsystem, where a Council diagnostic revealed zero E2E test coverage for the canvas, three critical integration bugs (simpleEntity type bug using a hardcoded string instead of entityType, RelationshipDialog built but unwired, EntityDetailPanel built but unused in browse mode), and multiple built-but-unwired components (SequenceDiagram, Full View UML/ArchiMate canvases) with no canvas interaction spec existing,

**facing** the risk that canvas functionality is demonstrably broken in production paths, that users cannot create relationships between entities, that browse mode shows no entity detail on node click, that three of ModelDialog's five model types render nothing, and that there is no test suite to catch regressions or validate fixes,

**we decided for** wiring all existing canvas components into routes (SequenceDiagram, FullViewCanvas for UML/ArchiMate, EntityDetailPanel in browse mode, RelationshipDialog on connection), fixing the simpleEntity type bug (use entityType instead of hardcoded 'simpleEntity'), adopting playwright-bdd (v8.4.2) for canvas E2E tests with Gherkin feature files as executable specs, installing Playwright MCP as a developer-only exploration tool (not for CI), creating a FullViewCanvas.svelte orchestrator for UML and ArchiMate rendering, and mapping ModelDialog's five model types to their correct canvas components,

**and neglected** ignoring the integration bugs and leaving canvas partially broken (which would undermine the core value proposition of Iris as a modelling tool), writing standard Playwright tests without Gherkin (which would miss the opportunity for business-readable executable specs), and rewriting the canvas subsystem from scratch (which would discard working components that only need wiring),

**to achieve** a fully functional canvas where all five model types render correctly, relationships can be created through the dialog, entity detail is visible in browse mode, the simpleEntity type bug is eliminated, and a Gherkin BDD test suite provides business-readable executable specs that document canvas behaviour,

**accepting that** playwright-bdd introduces a new dependency and Gherkin authoring conventions, that the BDD test suite runs as a separate Playwright project alongside the existing 41 E2E tests, and that FullViewCanvas is a new orchestrator component that must be maintained for both UML and ArchiMate rendering paths.

---

## Integration Bugs Identified

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| **simpleEntity type bug** | Node type hardcoded as `'simpleEntity'` instead of using the entity's `entityType` field | Use `entityType` to look up the correct node type from `simpleViewNodeTypes` registry |
| **RelationshipDialog unwired** | Dialog component exists but is never opened on edge connection | Wire `onconnect` callback to open RelationshipDialog with source/target context |
| **EntityDetailPanel unused** | Panel component exists but is never rendered in browse mode | Wire node click in BrowseCanvas to display EntityDetailPanel with entity data |

---

## Unwired Components

| Component | Intended Use | Integration Path |
|-----------|-------------|-----------------|
| **SequenceDiagram** | Render sequence model type | Conditional render when `model.model_type === 'sequence'` |
| **FullViewCanvas (UML)** | Render UML model type with full UML node/edge types | New FullViewCanvas.svelte with `viewType='uml'` |
| **FullViewCanvas (ArchiMate)** | Render ArchiMate model type with ArchiMate node/edge types | New FullViewCanvas.svelte with `viewType='archimate'` |

---

## Model Type to Canvas Component Mapping

| Model Type | Canvas Component | Node Types | Edge Types |
|-----------|-----------------|------------|------------|
| simple | ModelCanvas | simpleViewNodeTypes | simpleViewEdgeTypes |
| component | ModelCanvas | simpleViewNodeTypes | simpleViewEdgeTypes |
| sequence | SequenceDiagram | N/A (parsed as SequenceDiagramData) | N/A |
| uml | FullViewCanvas(uml) | umlNodeTypes | umlEdgeTypes |
| archimate | FullViewCanvas(archimate) | archimateNodeTypes | archimateEdgeTypes |

---

## Testing Strategy

| Aspect | Decision |
|--------|----------|
| **Framework** | playwright-bdd v8.4.2 |
| **Spec format** | Gherkin `.feature` files as executable specifications |
| **Step definitions** | TypeScript step files co-located with features |
| **CI integration** | `bddgen` generates Playwright test files from features; standard `playwright test` runs them |
| **Existing tests** | 41 E2E tests remain unchanged in their own Playwright project |
| **Project structure** | Dual Playwright projects: `e2e` (existing) and `bdd` (new canvas tests) |
| **Playwright MCP** | Developer-only exploration tool; not used in CI |

---

## Options Considered

### Option 1: Wire Components and Add BDD Tests (Selected)

**Pros:**
- Fixes all three critical bugs
- Wires all five model types to correct canvas components
- Gherkin feature files serve as both specs and executable tests
- Business-readable test suite documents canvas behaviour
- Existing 41 E2E tests remain untouched

**Cons:**
- playwright-bdd is an additional dependency
- Gherkin requires a learning curve for contributors unfamiliar with BDD
- FullViewCanvas is a new component to maintain

### Option 2: Standard Playwright Tests Without Gherkin (Rejected)

**Pros:**
- No new testing framework to learn
- Simpler tooling chain

**Cons:**
- Loses business-readable executable specs
- Test intent is less clear without Given/When/Then structure
- No separation between spec and implementation

**Why rejected:** Canvas interactions are complex enough that Gherkin's structured scenarios provide significant clarity and documentation value.

### Option 3: Leave Canvas Partially Broken (Rejected)

**Pros:**
- No implementation effort

**Cons:**
- Three of five model types render nothing
- Relationships cannot be created
- Browse mode shows no entity detail
- Core modelling functionality is broken

**Why rejected:** Canvas is the core of Iris. Leaving it broken is not an option.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Wire components, fix bugs, implement BDD suite | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | Canvas built on Svelte Flow (xyflow) |
| Relates To | ADR-008 | Accessibility WCAG 2.2 | Canvas keyboard interactions must meet WCAG requirements |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-011-A | Canvas Interactions | Technical Specification | [specs/SPEC-011-A-Canvas-Interactions.md](specs/SPEC-011-A-Canvas-Interactions.md) |
| SPEC-011-B | Full View Integration | Technical Specification | [specs/SPEC-011-B-Full-View-Integration.md](specs/SPEC-011-B-Full-View-Integration.md) |
| SPEC-011-C | Sequence Diagram Integration | Technical Specification | [specs/SPEC-011-C-Sequence-Diagram-Integration.md](specs/SPEC-011-C-Sequence-Diagram-Integration.md) |
| SPEC-011-D | Canvas BDD Test Plan | Technical Specification | [specs/SPEC-011-D-Canvas-BDD-Test-Plan.md](specs/SPEC-011-D-Canvas-BDD-Test-Plan.md) |
| SPEC-011-E | Browse Mode Interactions | Technical Specification | [specs/SPEC-011-E-Browse-Mode-Interactions.md](specs/SPEC-011-E-Browse-Mode-Interactions.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
