# ADR-065: Inline Metadata Editing, Entity Detail Revamp, Extended Import Fields

## Proposal: Replace popup edit dialogs with inline editing, revamp entity detail page, import additional SparxEA fields

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-065 |
| **Initiative** | Inline Editing, Entity Detail Parity, Extended Import |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-064 (Sparx Import Metadata & Accordion Overview) |

---

## ADR (WH(Y) Statement format)

**In the context of** model and entity detail pages using popup dialogs for metadata editing (inconsistent with the inline "Edit Canvas" pattern), the entity detail page lacking the accordion layout and extended metadata display already present on models, and the SparxEA import pipeline discarding additional element fields (Scope, Abstract, Persistence, Author, Complexity, Phase, CreatedDate, ModifiedDate, GenType) and attribute fields (Notes, Default, LowerBound, UpperBound, Stereotype, Scope),

**facing** UX inconsistency between canvas inline editing and metadata popup editing, entity detail page being significantly less capable than the model detail page, loss of valuable metadata during SparxEA import, and attribute data being stored as flat strings rather than structured objects,

**we decided for** replacing popup edit dialogs with inline "Edit Metadata" editing on both model and entity detail pages, revamping the entity detail page with bits-ui Accordion groups (Summary, Details, Extended) matching the model page pattern, adding a clone button to the entity detail page, extending the SparxEA reader to extract 9 additional element fields and 6 additional attribute fields, and enriching the attribute import format from strings to structured objects with backward-compatible canvas rendering,

**and neglected** keeping popup dialogs (inconsistent UX), adding entity bookmarks (requires DB migration, deferred), and maintaining flat string attribute format (loses valuable type information),

**to achieve** consistent inline editing UX across the application, entity detail parity with models, full preservation of SparxEA element and attribute metadata, and richer attribute data for downstream consumption,

**accepting that** the enriched attribute format requires backward-compatible handling in canvas nodes, and the inline editing pattern increases the complexity of the detail page components.

---

## Decisions

1. **Inline metadata editing (models)**: Replace "Edit" button and ModelDialog popup with inline "Edit Metadata" button above accordion; editable fields: Name, Description, Tags, Template toggle
2. **Inline metadata editing (entities)**: Replace "Edit" button and EntityDialog popup with inline "Edit Metadata" button above accordion; editable fields: Name, Description, Tags
3. **Tab rename**: Model detail "Overview" tab renamed to "Details" for consistency with entity page
4. **Entity detail accordion**: Replace flat `<dl>` with bits-ui Accordion having Summary, Details, and Extended groups matching model page pattern
5. **Entity clone**: Add clone button to entity detail header
6. **Extended metadata display**: Entity Extended group shows all imported metadata fields (scope, abstract, persistence, author, complexity, phase, dates, gen_type) plus tagged values table
7. **Reader enhancements**: Add 9 fields to QeaElement (Scope, Abstract, Persistence, Author, Complexity, Phase, CreatedDate, ModifiedDate, GenType) and 6 fields to QeaAttribute (Notes, Default, LowerBound, UpperBound, Stereotype, Scope)
8. **Import enrichment**: Map new element fields to entity metadata, change attribute format from strings to structured objects
9. **Canvas backward compatibility**: ClassNode and AbstractClassNode handle both string and object attribute formats
10. **DOMPurify**: All inline edit save functions sanitize user inputs

---

## Specification

See [SPEC-065-A](specs/SPEC-065-A-Inline-Edit-Entity-Revamp.md).
