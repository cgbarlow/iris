# ADR-074: C4 Model Support

## Proposal: Add C4 diagram notation with all element types and renderers

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-074 |
| **Initiative** | SparxEA Gap Closure |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-04 |
| **Status** | Approved |
| **Dependencies** | ADR-068, ADR-071 |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris supporting UML, ArchiMate, and Simple notations but lacking C4 — a widely-used developer-friendly architecture diagramming approach with ~10 elements and simple labeled relationships,

**facing** users wanting to create C4 diagrams (System Context, Container, Component, Code, Deployment) alongside existing notation types,

**we decided for** adding C4 as a fourth notation with 9 element types (Person, Software System, External System, Container, Component, Code Element, Deployment Node, Infrastructure Node, Container Instance), one relationship type (c4_relationship with label and technology annotation), and notation-aware renderers that plug into the existing DynamicNode/DynamicEdge architecture,

**and neglected** treating C4 as a subset of ArchiMate (would lose C4-specific visual identity),

**to achieve** comprehensive multi-notation architecture modelling covering UML, ArchiMate, C4, and Simple views,

**accepting that** C4 is Iris-native (not imported from SparxEA) and has simpler relationship semantics than UML/ArchiMate.

---

## Decisions

1. **C4 types**: 9 element types across 5 levels (system_context, container, component, code, deployment)
2. **C4 relationship**: Single `c4_relationship` type with label and technology annotation
3. **C4Renderer**: Level badges, C4-style blue/grey colour scheme, dark mode support
4. **C4EdgeRenderer**: Solid lines for all C4 relationships
5. **Registry**: All C4 types registered in unified registry via DynamicNode/DynamicEdge
6. **Type equivalences**: component→c4_component, actor→person

---

## Specification

See [SPEC-074-A](specs/SPEC-074-A-C4-Element-Types-Rendering.md).
