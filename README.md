# Iris

**Integrated Repository for Information & Systems**

Iris is a web-based architectural modelling tool for creating, managing, and versioning architectural entities, relationships, and models. It supports Simple View, UML, ArchiMate, and sequence diagram notations with full keyboard accessibility and WCAG 2.2 Level AA compliance.

## Architecture

Iris follows a **repository-first architecture** (ADR-003): entities are first-class citizens stored in a versioned repository. Diagrams are projections of entity data, not the source of truth.

```
iris/
  backend/       Python/FastAPI API server with SQLite
  frontend/      SvelteKit/Svelte 5 single-page application
  docs/          ADRs, specs, protocols, and compliance documents
```

### Backend

- **Framework:** FastAPI with async SQLite (aiosqlite)
- **Database:** SQLite with WAL mode, foreign keys, and 7 PRAGMAs per SPEC-004-A
- **Auth:** Argon2id password hashing, JWT access tokens (15min), refresh token rotation
- **RBAC:** 4 roles (Admin, Architect, Reviewer, Viewer) with 26 permission mappings
- **Audit:** Separate audit database with SHA-256 hash-chained immutable log
- **Versioning:** Immutable append-only entity versions with revert-as-new-version rollback
- **Search:** Full-text search with SQLite FTS5 (semantic search planned — see docs/ROADMAP.md)

### Frontend

- **Framework:** SvelteKit with Svelte 5 (runes: `$state`, `$derived`, `$effect`, `$props`)
- **Canvas:** @xyflow/svelte (SvelteFlow) for interactive diagram editing
- **Styling:** Tailwind CSS v4 with CSS custom properties for theming
- **Accessibility:** WCAG 2.2 Level AA + adopted AAA (2.4.13 Focus Appearance, 2.1.3 Keyboard No Exception)
- **Security:** DOMPurify sanitisation on all user-generated content rendered in canvas

## Features

### Canvas Views

| View | Entity Types | Relationship Types |
|------|-------------|-------------------|
| **Simple View** | Component, Service, Interface, Package, Actor, Database, Queue | Uses, Depends On, Composes, Implements, Contains |
| **UML** | Class, Object, Use Case, State, Activity, Deployment | Association, Aggregation, Composition, Dependency, Realization, Generalization |
| **ArchiMate** | 11 types across Business, Application, Technology layers | Serving, Composition, Aggregation, Assignment, Realization, Access, Influence, Triggering |
| **Sequence** | Participants with lifelines | Sync, Async, Reply messages with activation boxes |

### Keyboard Accessibility

All canvas operations have keyboard equivalents:

| Key | Action |
|-----|--------|
| Tab / Shift+Tab | Navigate between entities |
| Arrow keys | Move selected entity (Shift = large steps) |
| Ctrl+N | Create new entity |
| C | Toggle connect mode |
| Enter / Space | Select / confirm |
| Delete | Delete selected entity |
| Escape | Deselect / cancel |
| Ctrl+= / Ctrl+- | Zoom in / out |
| Ctrl+0 | Fit to screen |
| F | Focus selected entity |

### Theming

Four colour modes with WCAG-compliant contrast ratios:

- **Light** — Default theme
- **Dark** — Dark background with light text
- **High Contrast** — Black background, yellow primary, 7:1+ ratios
- **System** — Follows OS preference via `prefers-color-scheme`

### Browse & Edit Modes

- **Edit Mode** — Full canvas editing with drag, connect, create, delete
- **Browse Mode** — Read-only canvas for viewers and reviewers, with entity detail panel

### Dashboard

- Entity and model counts with linked navigation
- Bookmarked models with quick access
- Full-text search across entities and models
- Quick navigation cards for key sections

### Admin Panel

- **User Management** — List, create, edit role, activate/deactivate users with WCAG-compliant forms and confirmation dialogs
- **Audit Log** — Paginated audit log viewer with action/username/target filters, chain verification badge, and expandable row detail (JSON rendered as text, no `{@html}`)

### Statistics & Cross-References

- Entity relationship counts and model usage statistics
- Entity-to-model cross-reference queries (which models reference an entity)

## Getting Started

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ with npm

### Backend

```sh
cd backend
uv sync
uv run python -m app.main
```

The API server starts on `http://localhost:8000`.

### Frontend

```sh
cd frontend
npm install
npm run dev
```

The frontend starts on `http://localhost:5173` with API proxy to the backend.

### Running Tests

```sh
# Backend (217 tests)
cd backend
uv run python -m pytest

# Frontend unit tests (120 tests)
cd frontend
npm test

# Frontend E2E tests (10 suites, Playwright)
cd frontend
npx playwright test
```

## Compliance

### WCAG 2.2

58 criteria audited (56 AA + 2 adopted AAA). Key implementations:

- Skip links, ARIA landmarks, focus indicators (2px, 3:1 contrast)
- Keyboard navigation for all canvas operations (no keyboard traps)
- 24px minimum touch targets, reduced motion support
- Session timeout warning with extension option
- Help page with keyboard shortcut reference
- Three-theme system meeting all contrast requirements

### NZ ITSM (NZISM v3.9)

44 controls mapped across 6 families. Key implementations:

- Argon2id password hashing with 12-char minimum, complexity, and history
- JWT with 15-minute expiry and refresh token rotation
- SHA-256 hash-chained audit log in separate database
- Rate limiting (10/min login, 30/min refresh, 100/min general)
- DOMPurify XSS prevention, CSP headers, parameterised queries
- RBAC with least privilege (4 roles, 26 permission mappings)

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/north-star.md` | Vision, principles, and success criteria |
| `docs/protocols.md` | 12 non-negotiable development protocols |
| `docs/adrs/` | 10 Architecture Decision Records |
| `docs/adrs/specs/` | 15 implementation specifications |
| `docs/ROADMAP.md` | Future enhancements and semantic search roadmap |
| `docs/nz-itsm-control-mapping.md` | NZISM control compliance tracking |

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend Framework | SvelteKit | 2.x |
| UI Framework | Svelte 5 | 5.x (runes) |
| Canvas | @xyflow/svelte | 1.5.x |
| Styling | Tailwind CSS | 4.x |
| Backend Framework | FastAPI | 0.115.x |
| Database | SQLite | 3.x (aiosqlite) |
| Auth Hashing | Argon2id | argon2-cffi |
| JWT | python-jose | HS256 |
| Testing (Backend) | pytest | 8.x |
| Testing (Frontend) | Vitest | 4.x |
| Linting | Ruff | 0.9.x |
| Type Checking | mypy (strict) | 1.x |

## Versioning

| Version | Phase | Description |
|---------|-------|-------------|
| v0.1.0 | A | Data Foundation — database schema, migrations, audit service |
| v0.2.0 | B | Core API — auth, CRUD, rate limiting, audit middleware |
| v0.3.0 | C | Search & Collaboration — comments, bookmarks, full-text search |
| v0.4.0 | D | Frontend Foundation — auth flow, app shell, theming, routing, a11y |
| v0.5.0 | E | Canvas — Simple View, UML, ArchiMate, sequence diagrams, keyboard a11y |
| v0.6.0 | F | Browse Mode — read-only canvas, entity detail views, search UI |
| v1.0.0 | G | Polish — WCAG audit, NZ ITSM verification, performance testing |
| v1.1.0 | H | Remediation — audit API, entity statistics, dashboard, admin pages, documentation corrections, E2E tests |

## License

All rights reserved.
