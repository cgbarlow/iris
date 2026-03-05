# ADR-081: Notation-First UX

## Proposal: Surface notation as a first-class UX concept with default setting, notation-first filtering, and element-level notation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-081 |
| **Initiative** | User Experience |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-05 |
| **Status** | Approved |
| **Dependencies** | ADR-079 |

---

## ADR (WH(Y) Statement format)

**In the context of** ADR-079 having separated diagram type from notation in the data model, but the UX not surfacing notation selection effectively — the DiagramDialog shows notation conditionally after type, the EntityDialog has no visible notation dropdown, elements don't store their notation, and there is no user default notation setting,

**facing** users having to manually select notation each time they create a diagram, entity types not being filtered by notation in the EntityDialog, elements losing their notation provenance after creation, and no way to establish a preferred working notation,

**we decided for** a notation-first UX where: (1) a default notation user setting is stored in localStorage and exposed in Settings, (2) the DiagramDialog shows notation as the first dropdown that filters available diagram types, (3) the EntityDialog shows a visible notation dropdown that filters entity types, and (4) elements carry a `notation` column displayed in browse-mode popups and detail pages,

**and neglected** server-side user preference storage (adds complexity for a simple UI preference), automatic notation inference from element type (ambiguous — many types exist in multiple notations), and keeping notation invisible to users (undermines the notation-first workflow),

**to achieve** a streamlined notation-first workflow where users set their preferred notation once, create diagrams and elements with notation-aware filtering, and can always see which notation an element was created under,

**accepting that** the element notation column requires a database migration, the default notation setting is per-browser (localStorage), and the notation dropdown adds one more field to the create dialogs.

---

## Decisions

1. **Default notation setting**: Stored in `localStorage` under key `iris-default-notation`, configurable on Settings page
2. **DiagramDialog notation-first**: Notation dropdown appears before diagram type, filters available types by selected notation
3. **EntityDialog notation dropdown**: Visible notation dropdown above type dropdown, defaults to diagram's notation or user default
4. **Element notation column**: `notation TEXT DEFAULT 'simple'` on `elements` table, displayed in EntityDetailPanel and element detail page
5. **Seed data**: All seed elements get explicit notation values

---

## Specification

See [SPEC-081-A](specs/SPEC-081-A-Notation-First-UX.md).
