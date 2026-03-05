# ADR-079: Diagram Type and Notation Registry

## Proposal: Separate diagram type from visual notation with a registry of valid combinations

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-079 |
| **Initiative** | Data Model |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-05 |
| **Status** | Approved |
| **Dependencies** | ADR-071, ADR-074 |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris conflating diagram structural purpose (component, sequence, deployment) with visual notation (UML, ArchiMate, C4) in a single `diagram_type` field,

**facing** the inability to render the same structural diagram type in different visual notations (e.g., a Component diagram in C4 notation), limited extensibility for new notations, and auto-detection of which notations are actually used on a canvas,

**we decided for** a registry of diagram types and notations stored in database tables with a many-to-many mapping of valid combinations, a `notation` column on diagrams, and automatic detection of notations present in canvas data based on entity types,

**and neglected** enum-only approaches (not extensible), single notation per diagram (too restrictive), and client-only notation resolution (inconsistent across views),

**to achieve** flexible multi-notation support where any diagram type can use any compatible notation, auto-detection of notations for mixed-notation diagrams, and a clean separation between structural purpose and visual rendering,

**accepting that** existing diagrams require data migration to populate the new notation column, the registry tables add modest schema complexity, and the mapping matrix must be maintained as new notations are added.

---

## Decisions

1. **Registry tables**: `diagram_types`, `notations`, and `diagram_type_notations` store the valid combinations
2. **Notation on identity table**: The `notation` column is on `diagrams`, not `diagram_versions` — changing notation is visual, not content
3. **Default notation**: Each (type, notation) pair can be marked as default; when creating a diagram without specifying notation, the default for that type is used
4. **Data migration**: Existing `diagram_type` values are normalized (uml/archimate/c4 become component type with respective notation)
5. **Auto-detection**: `detected_notations` column stores JSON array of notations found by scanning canvas node entity types
6. **Seven diagram types**: component, sequence, class, deployment, process, roadmap, free_form
7. **Four notations**: simple, uml, archimate, c4

---

## Specification

See [SPEC-079-A](specs/SPEC-079-A-Diagram-Type-Notation-Registry.md).
