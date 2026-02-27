# Iris — North Star

## Integrated Repository for Information & Systems

### Vision

Iris is the lens through which an organisation sees its own architecture. It is a web-based architectural modelling tool for solution, domain, and enterprise architects — a shared repository of truth where entities have identity, metadata, version history, and relationships. Diagrams are projections of that underlying truth, not drawings on a canvas.

### Purpose

Enable architects and stakeholders to communicate, decide, and align through clear, accessible, version-controlled models of their systems and enterprise.

### Who It Serves

| Persona | Mode | What They Do |
|---------|------|-------------|
| **Solution Architects** | Edit Mode (Simple View) | Create and maintain component and sequence diagrams for solution design |
| **Domain Architects** | Edit Mode (Simple/Full View) | Model domain boundaries, relationships, and integration patterns |
| **Enterprise Architects** | Edit Mode (Full View) | Create full UML and ArchiMate models of the enterprise landscape |
| **Stakeholders & Technologists** | Browse Mode | Navigate, explore, and understand the architecture without editing |

### Guiding Principles

1. **Repository first, visualisation second.** Entities exist once and are referenced everywhere. Diagrams are views into a shared model of reality.
2. **Simple by default, powerful when needed.** Simple View for everyday component and sequence diagrams. Full View for when the full UML/ArchiMate palette is required.
3. **Accessible to everyone.** Full WCAG compliance is not optional. Light, dark, system, and high-contrast modes. Keyboard navigation. Screen reader support.
4. **Secure and auditable.** Every mutation is recorded. Version control with rollback. RBAC. NZ ITSM controls. No shortcuts on security.
5. **Quality over speed.** We build it right, not fast. Test-driven development. Code quality and architectural integrity maintained throughout.
6. **Scope discipline.** The boundary is drawn. We build what is scoped and do not add more.

### Architectural Layers

| Layer | What | Key Components |
|-------|------|----------------|
| **The Foundation** | Data & Domain Model | SQLite schema, entity identity, versioning, audit trail, relationships |
| **The Engine** | API & Business Logic | Authentication, RBAC, semantic search, version control, deep links, comments |
| **The Lens** | Frontend & UX | Interactive canvas, Browse/Edit modes, Simple/Full views, theming, accessibility |

### Tech Stack

| Layer | Technology | ADR |
|-------|-----------|-----|
| Frontend Framework | SvelteKit / Svelte 5 | [ADR-002](adrs/ADR-002-Frontend-Tech-Stack.md) |
| Canvas | Svelte Flow (xyflow) | [ADR-002](adrs/ADR-002-Frontend-Tech-Stack.md) |
| UI Components | shadcn-svelte + Bits UI | [ADR-002](adrs/ADR-002-Frontend-Tech-Stack.md) |
| Frontend State | Svelte 5 runes ($state, $derived, $effect) | [ADR-002](adrs/ADR-002-Frontend-Tech-Stack.md) |
| Styling | Tailwind CSS | [ADR-002](adrs/ADR-002-Frontend-Tech-Stack.md) |
| Backend | Python / FastAPI | [ADR-004](adrs/ADR-004-Backend-Language-And-Framework.md) |
| Database | SQLite | — |
| Search | sqlite-vss / sentence-transformers | — |
| Frontend Language | TypeScript | [ADR-002](adrs/ADR-002-Frontend-Tech-Stack.md) |

### Success Criteria

1. Modelling engine delivers (component, sequence, UML, ArchiMate)
2. UX is minimalistic, beautiful, and functional (Browse Mode + Edit Mode with Simple/Full Views)
3. Full WCAG accessibility
4. Data layer is solid (SQLite, semantic search, metadata, bookmarks)
5. Governance and auditability (version control, audit trail, RBAC, NZ ITSM, auth)
6. Collaboration and sharing (deep links, comments)
7. Modern, appropriate tech stack
8. Quality over speed
9. Full business requirements extrapolation
10. Scope discipline

### Build Sequence

| Phase | Focus | Depends On |
|-------|-------|-----------|
| A | Data Foundation — SQLite schema, entity model, versioning, audit | — |
| B | Core API — Backend framework, auth, RBAC, CRUD, version ops | A |
| C | Search & Collaboration — Semantic search, comments, bookmarks | B |
| D | Frontend Foundation — SvelteKit shell, routing, auth flow, theming, a11y scaffolding | B |
| E | The Canvas — Interactive modelling, Simple View then Full View | D |
| F | Browse Mode & Entity Views — Stakeholder experience, relationship web | E |
| G | Polish & Compliance — WCAG audit, NZ ITSM verification, performance | All |
