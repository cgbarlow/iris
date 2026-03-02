# ADR-057: UML Type Expansion

## Proposal: Add New UML Node Types and Edge Types

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-057 |
| **Initiative** | UML Specification Expansion (WP-4) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris Full View UML canvas, which currently supports 6 node types (class, object, use_case, state, activity, node) and 6 edge types (association, aggregation, composition, dependency, realization, generalization),

**facing** the need for fuller UML coverage to model interfaces, enumerations, abstract classes, components, and packages — all standard UML structural diagram elements — as well as the usage relationship type,

**we decided for** adding 5 new UML node types (interface_uml, enumeration, abstract_class, component_uml, package_uml) each with a dedicated Svelte 5 component, and 1 new edge type (usage) with its own edge component, registered in the existing type registries and type system,

**and neglected** using a single generic UML node component with conditional rendering (would reduce type safety and make per-type styling harder), and reusing Simple View types with different labels (would conflate the two view systems),

**to achieve** comprehensive UML structural diagram support covering the most commonly used UML diagram element types, enabling users to model interfaces, enumerations, abstract classes, components, and packages with proper UML notation,

**accepting that** unlike ArchiMate (which uses a single generic node component parameterised by layer), UML requires separate Svelte components per node type due to differing visual structures (compartments, stereotypes, tab-folder notation, etc.), increasing the component count in the UML node directory.

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-011 | Canvas Integration and Testing Strategy | UML node/edge type registries |
| Relates To | ADR-053 | Centre-Point Handle | All new nodes include 5-position handles |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-057-A | UML New Node Types | Technical Specification | [specs/SPEC-057-A-UML-New-Node-Types.md](./specs/SPEC-057-A-UML-New-Node-Types.md) |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | 2026-03-02 | Accepted | Implementation | 6 months | 2026-09-02 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Accepted | Architecture Team | 2026-03-02 |
