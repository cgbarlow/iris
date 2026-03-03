# ADR-066: Import All Skipped Items, Smart Tab Fix, Import Change Summary

## Proposal: Import Note/Boundary elements, NoteLink connectors, Package dependencies as model relationships, self-referencing associations; fix smart tab regression; add import change summaries

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-066 |
| **Initiative** | Complete SparxEA Import Coverage |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-065 (Inline Edit, Entity Revamp, Extended Import) |

---

## ADR (WH(Y) Statement format)

**In the context of** SparxEA import currently skipping Note elements, Boundary elements, NoteLink connectors, self-referencing associations, and Package-to-Package dependencies, while also showing "—" in version history for imported entities/models due to missing change summaries, and a smart tab regression where the model detail page fails to reset tab selection when navigating between models,

**facing** incomplete import coverage (users see "6 elements skipped, 3+ connectors skipped"), loss of architectural documentation notes and boundary groupings, missing dependency relationships between packages, inability to model self-referential associations, uninformative version history for imported items, and a UX regression where empty models don't default to the Details tab,

**we decided for** importing Note and Boundary as first-class entity types with dedicated canvas components (NoteNode, BoundaryNode), importing NoteLink as a relationship type with a dotted NoteLinkEdge, removing the self-reference guard to support self-loop edges (SelfLoopEdge), creating a model_relationships table for Package-to-Package dependencies with a Relationships tab on the model detail page, adding descriptive change_summary values during import, and fixing the smart tab to reset userSelectedTab on model navigation,

**and neglected** treating Notes as annotations rather than entities (loses queryability), implementing boundaries as group nodes (requires @xyflow group support, deferred), and keeping self-references blocked (legitimate UML pattern),

**to achieve** zero skipped items during import, complete preservation of SparxEA model content, informative version history for imported items, correct smart tab defaults, and first-class model-level dependency tracking,

**accepting that** Note and Boundary entities add new types to the entity system, model_relationships introduces a new table and API surface, and self-loop edges require a custom rendering component.

---

## Decisions

1. **Note entity type**: Move "Note" from SKIP_OBJECT_TYPES to OBJECT_TYPE_MAP as `note`; create NoteNode canvas component with yellow background and DOMPurify-sanitized HTML content
2. **Boundary entity type**: Move "Boundary" from SKIP_OBJECT_TYPES to OBJECT_TYPE_MAP as `boundary`; create BoundaryNode canvas component with dashed border
3. **NoteLink relationship type**: Move "NoteLink"/"Notelink" from SKIP_CONNECTOR_TYPES to CONNECTOR_TYPE_MAP as `note_link`; create NoteLinkEdge with dotted line
4. **Self-referencing associations**: Remove self-ref guard from import service and canvas auto-create; create SelfLoopEdge for rendering
5. **Model relationships**: Migration m015 for model_relationships table; new service/router; Relationships tab on model detail page
6. **Package dependencies**: Import Package-to-Package connectors as model_relationships using element_to_package reverse map
7. **Import change summary**: Add `change_summary` parameter to `create_entity()` and `create_model()`; pass descriptive summaries from import
8. **Smart tab fix**: Reset `userSelectedTab = false` when model ID changes in the navigation effect
9. **DOMPurify**: NoteNode uses DOMPurify for HTML content rendering per Protocol 7

---

## Specification

See [SPEC-066-A](specs/SPEC-066-A-Import-All-Skipped-Items.md).
