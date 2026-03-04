# ADR-071: Naming Rename — Entity to Element, Model to Diagram, Package as First-Class

## Proposal: Align Iris terminology with UML/ArchiMate standards

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-071 |
| **Initiative** | SparxEA Gap Closure |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-068, ADR-069, ADR-070 |

---

## ADR (WH(Y) Statement format)

**In the context of** "Entity" carrying ER-diagram connotations (a Note is not an "entity") and "Model" being overloaded (used for both diagrams and packages), while the North Star says "diagrams are projections" but the code says "models" and packages exist as models with empty data,

**facing** confusion for users importing from SparxEA where elements are not entities and diagrams are not models, and packages having no distinct first-class representation,

**we decided for** renaming Entity→Element, splitting Model into Diagram (with canvas data) and Package (organisational container), creating dedicated database tables, API routes, and frontend routes for each concept,

**and neglected** keeping the current naming (perpetuates confusion) and a minimal UI-only rename (leaves code inconsistent),

**to achieve** terminology alignment with UML/ArchiMate/C4 standards, clear separation of packages from diagrams, and a clean API surface,

**accepting that** this is a breaking change requiring database migration, API route renames, and frontend route renames.

---

## Decisions

1. **Database migration m016**: Rename tables (entities→elements, models→diagrams+packages)
2. **Backend modules**: entities/→elements/, models_crud/→diagrams/+packages/
3. **API routes**: /api/entities→/api/elements, /api/models→/api/diagrams+/api/packages
4. **Frontend routes**: /entities→/elements, /models→/diagrams, new /packages
5. **Package detail page**: tabs for Overview, Contents, Relationships, Version History

---

## Specification

See [SPEC-071-A](specs/SPEC-071-A-Database-Schema-Rename.md).
