# Changelog

All notable changes to Iris are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Search now returns results for all entities and models; FTS index rebuilt on startup

## [1.4.0] - 2026-02-28

### Added
- Focus view for all canvas types (fullscreen overlay, Escape to exit)
- Sequence diagram zoom/pan/fit-to-view via SVG viewBox manipulation
- Sequence diagram edit mode (Add Participant, Add Message, Delete Selected, Save/Discard)
- Sequence diagram zoom toolbar (bottom-left, matching SvelteFlow Controls style)
- ADR-014: Canvas UX Parity
- SPEC-014-A: Canvas UX Parity Implementation

### Fixed
- Duplicate zoom controls — removed top-right CanvasToolbar, keeping bottom-left SvelteFlow Controls

## [1.3.1] - 2026-02-28

### Added
- Model preview thumbnails in gallery cards (static SVG rendering of canvas/sequence diagrams)
- ADR-013: Model Preview Thumbnails
- SPEC-013-A: Model Preview Thumbnails Implementation

## [1.3.0] - 2026-02-28

### Added
- Gallery/card view mode on models list page with responsive CSS grid layout
- View mode toggle (list/gallery) in models toolbar with `aria-pressed` state
- Card size slider (200px–400px) for adjusting gallery card width, visible only in gallery mode
- localStorage persistence for view mode and card size preferences across sessions
- Gallery cards show model name, type badge, full description, and updated date
- ADR-012: Models Page Gallery View
- SPEC-012-A: Gallery View Implementation
- BDD test suite for gallery view (6 scenarios in models-gallery.feature)

## [1.2.1] - 2026-02-28

### Fixed
- SvelteFlow canvas rendering crash: `useSvelteFlow()` was called outside `<SvelteFlow>` context in ModelCanvas, FullViewCanvas, and KeyboardHandler — moved CanvasToolbar and KeyboardHandler inside SvelteFlow slot where context is available
- Test infrastructure: replaced globalSetup with wrapper script (globalSetup runs after webServer, killing the backend)
- BDD test reliability: fixed model navigation selectors, entity detail panel locators, SVG strict mode, and feature file scenarios for 100% pass rate (42/42 BDD, 41/41 E2E)

## [1.2.0] - 2026-02-28

### Added
- Full View canvas (UML + ArchiMate) with FullViewCanvas.svelte orchestrator
- Sequence diagram rendering on canvas tab for sequence model types
- RelationshipDialog wired to canvas edge creation with 5 relationship types
- EntityDetailPanel in browse mode — click node to see entity details
- Entity edit and delete on entity detail page with optimistic concurrency
- Model type filter on models list page
- Bookmark toggle on model detail page
- Password change on Settings page with NZISM-compliant 12-char minimum
- Audit date range filters (from_date/to_date) on admin audit page
- Comments UI on model and entity detail pages (add, edit, delete)
- Version rollback on model detail Version History tab
- Canvas link existing entity via EntityPicker dialog
- CommentsPanel component for inline comment CRUD
- EntityPicker component for searchable entity selection
- Gherkin BDD test suite with playwright-bdd (12 feature files, 5 step definition files)
- Playwright MCP configuration for exploratory testing
- ADR-011: Canvas Integration and Testing Strategy
- SPEC-011-A through SPEC-011-E: Canvas interactions, Full View, sequence, BDD test plan, browse mode

### Fixed
- Canvas node type bug: entities now render with correct shapes (was using unregistered 'simpleEntity' type)
- Canvas relationship creation: users can now choose relationship type via dialog (was hardcoded to 'uses')
- Browse mode node clicks now show entity detail panel (was silently ignored)

## [1.1.1] - 2026-02-28

### Added
- Settings page with theme picker (Light, Dark, High Contrast)
- "New Model" button on models list page with create dialog
- Edit and Delete actions on model detail page
- "New Entity" button on entities list page

### Changed
- Theme selection moved from header toggle to Settings page
- Sidebar items: removed letter prefixes, added keyboard shortcut tooltips

### Fixed
- Theme toggle cycle bug: Light mode now reachable (was stuck in Dark/HC loop)
- Auth redirect race condition in layout preventing login navigation
- Auth store now persists to sessionStorage, surviving page reloads during E2E tests
- Dashboard heading always visible immediately (no longer hidden behind loading state)
- Vite preview proxy: API calls now correctly proxy to backend in production preview mode
- Backend rate limits configurable via environment variables (IRIS_RATE_LIMIT_LOGIN, IRIS_RATE_LIMIT_GENERAL, IRIS_RATE_LIMIT_REFRESH)
- E2E test suite: fixed password mismatch, strict mode violations, rate limit handling, and timing-sensitive assertions (41/41 pass)

## [1.1.0] - 2026-02-27

### Added
- Read-only audit log API: `GET /api/audit` with pagination, filtering, and admin-only access (ADR-009, SPEC-009-A)
- Audit chain verification API: `GET /api/audit/verify` returns hash chain integrity status
- Entity statistics API: `GET /api/entities/{id}/stats` returns relationship and model usage counts
- Entity cross-reference API: `GET /api/entities/{id}/models` returns models referencing an entity
- Dashboard page with entity/model counts, bookmarked models, search, and quick navigation
- Admin home page with navigation cards for user management and audit log
- Admin users page with full CRUD: list, search, create, edit role, activate/deactivate
- Admin audit page with paginated log table, filters, chain verification badge, and expandable row detail
- ADR-009: Audit Log Read API
- ADR-010: Search Implementation Clarification
- SPEC-009-A: Audit Read API specification
- SPEC-010-A: Search Roadmap specification
- `docs/ROADMAP.md` documenting future semantic search enhancement
- Comprehensive E2E test suite (10 suites, Playwright) covering auth, dashboard, models, entities, admin, navigation, theming, accessibility, and errors
- Protocol 12: README Accuracy

### Changed
- Search documentation corrected from "semantic search with sentence-transformers" to "full-text search with SQLite FTS5" in README and north-star
- v0.3.0 changelog corrected: "semantic search" → "full-text search with FTS5"

### Fixed
- `apiFetch` return type handling: all list and detail pages now correctly use typed `apiFetch<T>()` instead of treating result as raw `Response`
- Entity detail page: versions, relationships, and used-in-models tabs now load real data from API
- Model detail page: canvas tab renders `BrowseCanvas`/`ModelCanvas` from model data, versions tab loads from API
- Dashboard page no longer a stub — displays live stats, bookmarks, search, and navigation
- Admin pages no longer stubs — full user management and audit log functionality

## [1.0.0] - 2026-02-27

### Added
- WCAG 2.2 audit with 50 compliance tests covering contrast ratios, keyboard ops, ARIA landmarks, focus indicators, and theme accessibility
- Session timeout warning component (WCAG 2.2.1 Timing Adjustable)
- Help page with keyboard shortcut reference (WCAG 3.2.6 Consistent Help)
- NZ ITSM control verification with 19 tests across 6 control families
- Performance tests for canvas operations at scale (500-5000 entities)
- Protocols 10-11: Claude agent teams and latest stable dependencies
- README with full project documentation
- CHANGELOG with versioned release history

### Changed
- Light theme border colour from #e2e8f0 to #6b7280 for WCAG 1.4.11 non-text contrast (3:1)
- Light theme danger colour from #ef4444 to #dc2626 for WCAG 1.4.3 text contrast (4.5:1)
- Dark theme border colour from #334155 to #64748b for WCAG 1.4.11 non-text contrast (3:1)
- NZ ITSM control mapping statuses updated from Pending to Verified

## [0.6.0] - 2026-02-27

### Added
- Browse mode with read-only canvas (nodesDraggable=false, nodesConnectable=false)
- Canvas mode store (edit/browse switching)
- Entity detail panel component for browse mode
- Entity detail page with tabs (details, version history, relationships, used-in models)
- Model detail page with tabs (overview, canvas, version history)
- Entity list page with search, type filter, and sort controls
- Model list page with search and sort controls

## [0.5.0] - 2026-02-27

### Added
- Simple View canvas with 7 node types and 5 edge types via @xyflow/svelte
- Canvas keyboard handler with full navigation (Tab, arrows, Enter, Delete, Escape, C, F)
- Canvas announcer (ARIA live region) for screen reader operation feedback
- Canvas toolbar with zoom controls
- Entity create/edit dialog with DOMPurify sanitisation
- Relationship dialog with type selection
- Canvas service for node/edge creation and placement serialisation
- Sequence diagram custom SVG renderer with keyboard navigation
- UML Full View: 6 node types (class with compartments, object, use case, state, activity, deployment) and 6 edge types
- ArchiMate Full View: 11 node types across 3 layers and 8 edge types with layer-specific styling

## [0.4.0] - 2026-02-27

### Added
- Authentication flow with JWT in-memory storage and auto-refresh
- App shell with skip links, ARIA landmarks, sidebar navigation
- Four-mode theming (light, dark, high-contrast, system) via mode-watcher
- All application routes with breadcrumbs and 404 handling
- Accessibility scaffolding: LiveRegion, ConfirmDialog, focus utilities
- Login page with WCAG compliance (autocomplete, paste, aria-describedby)

## [0.3.0] - 2026-02-27

### Added
- Comments CRUD on entities and models with soft delete
- Per-user model bookmarks (bookmark/unbookmark/list)
- Full-text search with SQLite FTS5

## [0.2.0] - 2026-02-27

### Added
- FastAPI app factory with lifespan management and security headers middleware
- Authentication service (Argon2id hashing, JWT HS256, refresh token rotation, password validation)
- Auth routes (login, refresh, logout, change-password, initial setup)
- Rate limiting middleware (sliding window: 10/min login, 30/min refresh, 100/min general)
- Audit middleware for intercepting mutating requests
- Entity CRUD with versioning, rollback, optimistic concurrency (If-Match), and soft delete
- Relationship CRUD with versioning
- Model CRUD with denormalised placements JSON and cross-reference queries
- User management API (admin only) with role assignment

## [0.1.0] - 2026-02-27

### Added
- Backend project setup (FastAPI, aiosqlite, argon2-cffi, python-jose, pytest, ruff, mypy)
- Frontend project setup (SvelteKit, Svelte 5, Tailwind v4, @xyflow/svelte, DOMPurify, mode-watcher, Vitest, Playwright)
- Database connection factory with 7 SQLite PRAGMAs (WAL, FK, busy_timeout, synchronous, cache_size, journal_size_limit, auto_vacuum)
- Database schema: roles, role_permissions, users, password_history, refresh_tokens
- Database schema: entities, entity_versions, relationships, relationship_versions, models, model_versions
- Audit database with SHA-256 hash-chained audit log
- Seed data for 4 roles (Admin, Architect, Reviewer, Viewer) and 26 permission mappings
- Audit service with genesis hash, hash computation, and chain verification
- Database startup initialisation (migrations, seeding, audit chain verification)
- 8 ADRs and 13 implementation specifications
- 11 non-negotiable development protocols
- NZ ITSM control mapping (44 controls across 6 families)
- WCAG 2.2 compliance matrix (58 criteria)
