# ADR-068: Canvas Consolidation, Unified Registry, and Notation-Aware Rendering Layer

## Proposal: Replace three canvas components and 30+ individual node/edge components with unified DynamicNode/DynamicEdge + notation-aware renderers

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-068 |
| **Initiative** | Canvas Architecture Consolidation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-066 (Note/Boundary types) |

---

## ADR (WH(Y) Statement format)

**In the context of** three canvas components (ModelCanvas, FullViewCanvas, BrowseCanvas) using different node/edge registries, 30+ separate node components duplicating shared logic (handles, selection, browseMode, labels), and no way for the same element to render differently based on diagram notation,

**facing** rendering failures when type registries don't align, massive code duplication across node components, and inability to support the North Star principle "Repository first, visualisation second" where the same element should render differently per notation,

**we decided for** a notation-aware rendering layer with single DynamicNode/DynamicEdge components that dispatch to notation-specific renderers (Simple, UML, ArchiMate), a BaseNode/BaseEdge handling all shared logic, a unified type registry, and a single UnifiedCanvas that sets notation via Svelte context,

**and neglected** keeping separate canvas components (perpetuates duplication), and a single monolithic node component (would become unmaintainable),

**to achieve** consistent rendering across all diagram types, eliminated code duplication, extensible architecture for future notations (C4), and fixed bugs where class nodes fail in browse mode and note/boundary nodes fail in UML edit mode,

**accepting that** this is a significant architectural change touching many files, and the renderer dispatch adds one level of indirection.

---

## Decisions

1. **DynamicNode/DynamicEdge**: Single node/edge components registered for ALL types, dispatching to notation-specific renderers via Svelte context
2. **BaseNode/BaseEdge**: Shared components handling handles, selection, browseMode, labels, a11y, routing, EdgeLabel, reconnection
3. **Notation renderers**: SimpleRenderer, UmlRenderer, ArchimateRenderer (+ edge variants) handle notation-specific visuals
4. **UnifiedCanvas**: Single canvas component replacing ModelCanvas, FullViewCanvas, BrowseCanvas, sets notation context
5. **Unified registry**: Maps ALL type keys to DynamicNode/DynamicEdge
6. **Type equivalences**: Cross-notation mapping for element reuse

---

## Specifications

- [SPEC-068-A](specs/SPEC-068-A-Canvas-Consolidation.md)
- [SPEC-068-B](specs/SPEC-068-B-Notation-Aware-Rendering.md)
