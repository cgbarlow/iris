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

### Canvas Interaction

- **Edit Mode** — Full canvas editing with drag, connect, create, delete
- **Browse Mode** — Read-only canvas for viewers and reviewers, click node to show entity detail panel
- **Focus View** — Fullscreen overlay for distraction-free canvas work (all model types), Escape to exit
- **Relationship Dialog** — When connecting two entities, a dialog prompts for relationship type and optional label
- **Link Existing Entity** — Add entities from the repository to the canvas via searchable picker dialog
- **Model Type Routing** — Model type determines which canvas renders: Simple View, UML, ArchiMate, or Sequence Diagram
- **Sequence Editing** — Add/remove participants and messages, zoom/pan/fit-to-view via SVG viewBox

### Dashboard

- Entity and model counts with linked navigation
- Bookmarked models with quick access
- Full-text search across entities and models
- Quick navigation cards for key sections

### Admin Panel

- **User Management** — List, create, edit role, activate/deactivate users with WCAG-compliant forms and confirmation dialogs
- **Audit Log** — Paginated audit log viewer with action/username/target/date range filters, chain verification badge, and expandable row detail (JSON rendered as text, no `{@html}`)

### Models Gallery View

- Toggle between list view (compact single-line items) and gallery view (detailed cards)
- Gallery cards show static SVG preview thumbnails of model diagrams (canvas nodes/edges, sequence participants/lifelines)
- Gallery renders models as responsive CSS grid cards showing thumbnail, name, type, full description, and updated date
- Card size slider (200px–400px) adjusts card width in gallery mode
- View mode and card size persist in localStorage across sessions

### Sets & Workspace Grouping

- **Sets** — top-level workspace grouping; each model and entity belongs to exactly one set (like folders, not labels)
- **Default Set** — all existing items belong to the Default set; it cannot be deleted
- **Set-scoped Tags** — tags are independent per set; "v1.0" in Set A is isolated from "v1.0" in Set B
- **Auto-membership** — saving a model's canvas automatically moves referenced entities into the model's set
- **Set Selector** — dropdown on models, entities, and import pages for filtering and assignment

### Batch Operations

- Select mode toggle on models and entities list pages with checkboxes on each item
- Batch toolbar with Clone, Move to Set, Tags, and Delete actions (up to 100 items per request)
- Batch set dialog for moving items between sets
- Batch tag dialog for adding/removing tags across multiple items

### Pagination

- Page size selector (25, 50, 100 items per page) on models and entities list pages
- Previous/Next navigation with page number links
- Total items count display

### Entity & Model Management

- Inline "Edit Metadata" on model and entity detail pages — in-place editing of Name, Description, Tags (replaces popup dialogs)
- Entity and model detail pages with accordion layout (Summary, Details, Extended groups)
- Entity clone button on detail page
- Extended metadata display for imported entities (scope, abstract, persistence, author, dates, tagged values)
- Entity CRUD with optimistic concurrency via If-Match headers
- Model CRUD with type filter on list page (Simple, Component, Sequence, UML, ArchiMate)
- Bookmark toggle on model detail page
- Comments on model and entity detail pages (add, edit, delete)
- Version rollback on model detail Version History tab
- Password change on Settings page with NZISM-compliant validation

### Statistics & Cross-References

- Entity relationship counts and model usage statistics
- Entity-to-model cross-reference queries (which models reference an entity)

## Getting Started

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ with npm

### Quick Start (Dev Script)

```sh
# Start both backend and frontend
./scripts/dev.sh start

# Check status
./scripts/dev.sh status

# Stop both
./scripts/dev.sh stop

# Full restart
./scripts/dev.sh restart
```

### Manual Setup

#### Backend

```sh
cd backend
uv sync
uv run python -m app.main
```

The API server starts on `http://localhost:8000`.

#### Frontend

```sh
cd frontend
npm install
npm run dev
```

The frontend starts on `http://localhost:5173` with API proxy to the backend.

### Running Tests

```sh
# Backend (399 tests)
cd backend
uv run python -m pytest

# Frontend unit tests (453 tests)
cd frontend
npm test

# Frontend E2E tests (Playwright, existing scripted tests)
cd frontend
npm run test:e2e

# Frontend BDD tests (Gherkin feature files via playwright-bdd)
cd frontend
npm run test:bdd

# All frontend E2E tests (scripted + BDD)
cd frontend
npm run test:all-e2e
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
| `docs/adrs/` | 13 Architecture Decision Records |
| `docs/adrs/specs/` | 22 implementation specifications |
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
| Testing (Frontend Unit) | Vitest | 4.x |
| Testing (Frontend E2E) | Playwright | 1.58.x |
| Testing (Frontend BDD) | playwright-bdd | 8.4.x |
| Linting | Ruff | 0.9.x |
| Type Checking | mypy (strict) | 1.x |

## License

All rights reserved.
