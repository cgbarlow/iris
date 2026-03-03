# Changelog

All notable changes to Iris are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- SparxEA import now extracts package Notes, element Status/Stereotype/Version, diagram Notes, connector Notes, and tagged values from `.qea` files (ADR-064, SPEC-064-A)
- Metadata field (`metadata: dict | null`) threaded through model and entity CRUD (create/get/update/list/versions) using existing `metadata TEXT` column in version tables
- Model overview: accordion-based layout with Summary (open by default), Details (collapsed), and Extended (collapsed, conditional) groups using bits-ui Accordion
- Model overview: Extended group shows Stereotype and Tagged Values table when metadata is present
- Model overview: Details group shows Status (from metadata), Modified By (from latest version), and all previous fields
- Smart default tab: models with no canvas content default to Overview tab instead of Canvas
- Hierarchy toggle icon (tree-view SVG) positioned left of tab bar, visible on all three tabs (Overview, Canvas, Version History)
- Fullscreen icon replaces "Focus" text on canvas toolbar buttons
- 15 new backend tests: 7 reader metadata, 3 import metadata, 5 metadata CRUD
- ADR-064: Sparx EA Import Metadata & Accordion Overview
- SPEC-064-A: Sparx Import Metadata & Accordion specification

### Changed
- Canvas toolbars use `flex-wrap` for responsive wrapping on narrow windows
- SparxEA import: package Notes passed as model description (was `None`)
- SparxEA import: diagram Notes passed as diagram model description (was `None`)
- SparxEA import: connector Notes passed as relationship description (was `None`)
- SparxEA import: element metadata (status, stereotype, version, tagged values) stored as entity metadata JSON

## [1.7.1] - 2026-03-02

### Fixed
- Pagination Prev/Next buttons now show visual disabled state (`opacity-50`, `cursor-not-allowed`) when on first/last page (ADR-063)
- Audit log page pagination buttons also receive disabled styling
- Soft-deleted set names no longer block creation of new sets with the same name — partial unique index replaces full UNIQUE constraint (migration m014)

### Added
- Model detail page: collapsible hierarchy tree sidebar showing set-scoped model tree with search filtering (ADR-063, SPEC-063-A)
- Model detail page: "Add Child" button in sidebar to create child models with pre-set parent and set
- Model detail page: "Parent" field in overview tab with "Change" (ModelPicker) and "Remove" actions for reparenting models
- Hierarchy toggle button next to model title with visual state indication
- Set-scoped hierarchy API: `GET /api/models/hierarchy?set_id=` optional query parameter
- Database migration m014: partial unique index on sets.name for active rows only
- ADR-063: Pagination Disabled Styling, Set Name Uniqueness Fix, Model Tree Explorer
- SPEC-063-A: Pagination, Set Uniqueness, Tree Explorer specification
- 3 integration tests for set-filtered hierarchy
- 2 integration tests for soft-deleted set name reuse

## [1.7.0] - 2026-03-02

### Added
- Persistent set selection: selecting a set on any page carries the filter across Models, Entities, and Dashboard navigation via a sessionStorage-backed global store (ADR-062, SPEC-062-A)
- Active set display in AppShell header: "Iris / {SetName}" with link to Sets page when a set is active
- Sets page active set highlighting with primary-colored border and "Reset filter" button
- Import page inline set creation: "+ New Set..." option in SetSelector opens create dialog, auto-selects new set
- Import page "View Models" link now includes set filter for the imported set
- Read-only tag badges and "Template: Yes/No" field on model overview tab
- Read-only tag badges and "Set" field on entity details tab
- Editable tags and template toggle in model edit dialog
- Editable tags in entity edit dialog
- ADR-062: Persistent Set Selection
- SPEC-062-A: Persistent Set Selection specification

### Changed
- General API rate limit increased from 100 to 300 requests/minute to prevent 429 errors during normal browsing
- Model detail ID field styling normalized (removed `font-mono text-xs`, now matches other fields)
- Entity detail ID field styling normalized (same as models)
- SetSelector `onchange` now passes set name along with ID; added `showNewSet`/`onNewSet` props and `reload()` export
- Sets page button styling aligned with Models page pattern (consistent `gap-2`, `px-3`/`px-4 py-2`, `text-sm`)
- Dashboard search now scoped to active set when filtering

- Sets: top-level workspace grouping — each model/entity belongs to exactly one set; Default set (well-known UUID) created on migration with all existing items backfilled (ADR-060, SPEC-060-A)
- Sets CRUD API: `POST/GET/PUT/DELETE /api/sets`, `GET /api/sets/{id}/tags` for scoped tag listing; 409 on non-empty delete, 403 on Default set delete
- Set-scoped tags: tags are stored the same way but filtered per-set in UI and API — "v1.0" in Set A is independent from "v1.0" in Set B
- Auto-membership: saving a model's canvas automatically moves referenced entities into the model's set
- Batch operations API: 8 endpoints under `/api/batch/{models,entities}/{delete,clone,set,tags}` for bulk actions on up to 100 items per request; all return `{ succeeded, failed, errors }`
- Pagination controls: `Pagination.svelte` component with page size selector (25/50/100), prev/next buttons, and page number links on models and entities list pages
- Set selector: `SetSelector.svelte` dropdown on models page, entities page, and import page for filtering and assignment
- Batch toolbar: select mode toggle with checkboxes on list/gallery items; sticky `BatchToolbar.svelte` with Clone, Move to Set, Tags, Delete actions; `BatchSetDialog.svelte` and `BatchTagDialog.svelte` for batch move and tag operations
- Import set assignment: set selector on import page sends `set_id` form field with upload; all imported items assigned to chosen set
- Set name display on model detail overview tab
- `set_id` and `set_name` fields on model and entity API responses (JOIN to sets table)
- `set_id` query parameter on `GET /api/models`, `GET /api/entities`, and `GET /api/entities/tags/all` for set-scoped filtering
- ADR-060: Sets, Batch Operations & Pagination
- SPEC-060-A: Sets, Batch Operations & Pagination specification
- Database migration m012: sets table, set_id columns on models/entities with indexes and backfill
- 20 integration tests for sets CRUD (default set, create, get, update, delete protection, tag scoping, model/entity set integration)
- 11 integration tests for batch operations (delete, clone, set reassignment, tag modification, validation, auth)
- Sets page: dedicated `/sets` page with list and gallery views, client-side search, edit mode toggle, and create dialog (ADR-061, SPEC-061-A)
- Dashboard integration: `?set_id=` URL parameter filters entity/model counts with "(filtered)" labels, 3-column stats grid with Sets card and reset filter link
- Set edit page: `/sets/[id]` with name/description editing, thumbnail management (none/model/image), and force-delete with confirmation
- Set thumbnails: `POST/GET /api/sets/{id}/thumbnail` endpoints for image upload and retrieval; model thumbnail proxy; 2 MB limit, PNG/JPG only
- Force-delete sets: `DELETE /api/sets/{id}?force=true` soft-deletes all models, entities, and search indexes; returns deletion counts
- Sidebar: Sets navigation item between Entities and Import; `aria-current` fix for sub-page highlighting
- Database migration m013: `thumbnail_source`, `thumbnail_model_id`, and `thumbnail_image` columns on sets table
- ADR-061: Sets Page & Dashboard Integration
- SPEC-061-A: Sets Page & Dashboard Integration specification
- 5 integration tests for force-delete (empty set, non-empty set with counts, default set protection, nonexistent, regular delete non-empty)
- 8 integration tests for set thumbnails (upload PNG, JPG, oversized rejection, invalid type, GET retrieval, 404 handling, model source, model-in-set validation)

## [1.6.0] - 2026-03-02

### Added
- Model Hierarchy: parent/child relationships for models via `parent_model_id` column; API endpoints for hierarchy tree, ancestors, children, and parent assignment with cycle validation (ADR-055, WP-1)
- Tree View: hierarchical model navigation on the Models page alongside list and gallery views; recursive TreeNode component with expand/collapse, search filtering, and keyboard support (WP-2)
- Breadcrumbs: ancestor chain navigation on model detail pages showing path from root to current model (WP-2)
- ArchiMate Full Specification: expanded from 11 to 45 entity types across 6 layers (business, application, technology, motivation, strategy, implementation & migration); 3 new relationship types (specialization, assignment, association); layer-specific CSS styling (ADR-056, WP-3)
- UML Type Expansion: 5 new node types (Interface, Enumeration, Abstract Class, Component, Package) with dedicated Svelte components; Usage edge type (ADR-057, WP-4)
- SparxEA Import: backend module to read `.qea` SQLite files (EA 16+) and import elements, connectors, diagrams, and package hierarchy into Iris; type mapping for UML/ArchiMate; coordinate conversion; `POST /api/import/sparx` endpoint (ADR-059, WP-5)
- Import UI: drag-and-drop upload page for `.qea` files with progress indicator and results summary; Import link in sidebar navigation (WP-6)
- BPMN Deferral: ADR-058 documenting decision to defer BPMN support to a future phase
- ADR-055 through ADR-059 and corresponding specs
- 20 backend tests for model hierarchy (create with parent, hierarchy tree, ancestors, children, cycle prevention, deleted model exclusion)
- 42 backend tests for SparxEA import (reader, mapper, converter, full import, API endpoint)

## [1.5.2] - 2026-03-02

### Added
- Data Model seed: 6th example model mapping the complete Iris database schema (20 tables, 19 FK relationships) across both databases, linked to the Data Layer model via modelref
- System Overview seed updated with Data Model modelref node and "Schema for" edge to Data Layer

### Fixed
- Centre-point connector persistence: edges connected via centre handles disappeared on save/reload because only a `type="source"` handle existed — @xyflow couldn't match `targetHandle: "center"` on the target node. Added matching `type="target"` centre handle to all 15 node components (ADR-053)

## [1.5.1] - 2026-03-02

### Added
- Centre-point connector mode: invisible centre Handle on all 15 node components (8 Simple View, 6 UML, 1 ArchiMate) enabling straight centre-to-centre connections; visible on hover with enlarged hit area (ADR-053, SPEC-053-A)
- ADR-053: Centre-Point Connection Mode
- SPEC-053-A: Centre-Point Handle Implementation
- ADR-054: ArchiMate Seed Data Node Type Mapping
- SPEC-054-A: ArchiMate Seed Data Fix

### Fixed
- Seed model node overlap: increased vertical spacing in all seed model builders to 250px row gaps, preventing node overlap with multi-line descriptions
- Seed model descriptions: replaced abbreviated hardcoded descriptions with full entity descriptions from `_ENTITIES` via `_ENTITY_DESCRIPTIONS` lookup dict
- ArchiMate Enterprise View rendering: seed data now uses correct ArchiMate node types (business_actor, application_component, etc.) with `layer` and `archimateType` data fields so ArchimateNode.svelte renders properly with coloured layer badges (ADR-054, SPEC-054-A)

## [1.5.0] - 2026-03-01

### Added
- Theme-aware PNG thumbnails: 3 theme variants (light/dark/high-contrast) with parameterized SVG colors, composite PK migration, ?theme= query param on thumbnail API (WP-1)
- Edge label editing: shared EdgeLabel.svelte component using EdgeLabelRenderer with double-click inline editing, DOMPurify sanitization, and CustomEvent dispatch (WP-3)
- Edge label repositioning: drag-to-reposition via pointer events, labelOffsetX/Y/Rotation in CanvasEdgeData (WP-4)
- Canvas node description sync: refreshNodeDescriptions() fetches entity data after canvas load, updating labels and descriptions via Promise.all (WP-5)
- Sequence diagram browse mode: onparticipantselect callback enables click-to-detail on participants with linked entities (WP-7)
- Model-in-model visual differentiation: ModelRefNode.svelte with stacked-squares visual, registered as 'modelref' node type (WP-8)
- Admin PNG regeneration button: POST /api/admin/thumbnails/regenerate endpoint with admin guard, settings page button with loading/success states (WP-9)
- Tag autocomplete: suggestions prop on TagInput with filtered dropdown, keyboard navigation (Arrow keys, Enter, Escape), ARIA combobox support (WP-10)
- ADR-046 through ADR-052 and corresponding specs
- Example Iris Architecture Models: idempotent seed creates 15 entities, 20 relationships, and 4 models (Iris Architecture, API Request Flow sequence diagram, Data Layer, Iris Enterprise View) with full canvas layouts and DB relationship records on first startup (WP-16)
- ADR-045: Example Iris Architecture Models
- SPEC-045-A: Example Architecture Models Seed
- Entity Edit from Model Editor: "Edit Entity" button in canvas toolbar (edit mode) when a linked entity node is selected; fetches entity from API, opens EntityDialog in edit mode, saves via PUT with If-Match header, and updates canvas node label/type/description in place (WP-15)
- ADR-044: Entity Edit from Model Editor
- SPEC-044-A: Entity Edit from Model Editor Implementation
- Template Designation: "Template" checkbox on model detail overview tab to mark models as reusable templates via the `template` tag; "Templates" toggle button on model list page filters to template models; green "Template" badge on model cards/list items (WP-13)
- ADR-043: Template Designation
- SPEC-043-A: Template Designation Implementation
- Connector Manipulation: per-edge routing type selection (Default, Straight, Step, Smooth Step, Bezier) via toolbar dropdown when an edge is selected in edit mode; routing type persists with model data and integrates with undo/redo (WP-11)
- ADR-042: Connector Manipulation
- SPEC-042-A: Connector Manipulation Implementation
- 59 tests for connector routing (type definitions, edge component path functions, routing change logic, undo/redo integration, page UI)
- Export Model: "Export" dropdown in canvas toolbar (edit mode) supports SVG, PNG, and PDF download; Visio and Draw.io shown as disabled placeholders (WP-10)
- ADR-039: Model Export
- SPEC-039-A: Model Export Implementation
- 13 unit tests for export utilities (filename sanitization, SVG extraction, DOM integrity)
- Clone Model: "Clone" button on model detail page duplicates a model with its canvas layout, pre-filling name with "(Copy)" suffix (WP-14)
- ADR-041: Clone Model
- SPEC-041-A: Clone Model Implementation
- Roadmap model type: available in model creation dialog, model type filter, and detail page canvas (uses simple canvas view)
- ADR-040: Roadmap Model Type
- SPEC-040-A: Roadmap Model Type Implementation
- Admin Settings link in application header for admin users, providing quick access to `/admin/settings` regardless of sidebar state
- ADR-031: Admin Settings Header Link
- ADR-031: Session Timeout During Active Use
- ADR-033: Search Display Fix — verified entity CRUD operations correctly maintain FTS5 search index
- ADR-034: GUID to Username Resolution
- SPEC-034-A: GUID Username Resolution Implementation
- 6 regression tests for entity search indexing (create, update, delete, description search, multiple entities, deep link format)
- 8 tests for GUID-to-username resolution (entity, model, and relationship endpoints)
- ADR-032: PNG Thumbnail Startup Regeneration and Frontend Fallback
- SPEC-032-A: PNG Thumbnail Fix
- 8 tests for PNG thumbnail generation (endpoint returns PNG, startup regeneration, stale SVG replacement, deleted model skipping)
- ADR-036: Browse Mode Fixes
- SPEC-036-A: Browse Mode Fixes Implementation
- ADR-038: Edge Reconnection Fix
- SPEC-038-A: Edge Reconnection Fix Implementation
- 45 tests for edge reconnection (reconnection logic, undo integration, EdgeReconnectAnchor presence in all 12 edge components)

### Changed
- TagInput component now accepts optional `suggestions` prop for autocomplete (WP-10)
- Edge components (Uses, DependsOn, Composes, Implements, Contains) now use shared EdgeLabel component (WP-3)
- CanvasEdgeData extended with labelOffsetX, labelOffsetY, labelRotation fields (WP-4)
- Undo/redo now covers node drag moves: dragging a node pushes pre-drag state to the undo stack
- Undo/Redo button tooltips updated from "Ctrl+Z"/"Ctrl+Y" to "Ctrl/Cmd+Z"/"Ctrl/Cmd+Y" for Mac compatibility
- Non-focus-mode editing canvases now pass onundo/onredo to enable Ctrl+Z/Ctrl+Y keyboard shortcuts
- ADR-035: Undo/Redo Node Moves + Mac Shortcut Labels

### Fixed
- Gallery thumbnail sizing: changed object-cover to object-contain with flex centering for correct aspect ratio (WP-2)
- Canvas node description sync: node descriptions now refresh from linked entities after canvas load (WP-5)
- Audit log username resolution: audit entries now show username instead of GUID via _resolve_username() (WP-6)
- Entity tag display: get_entity() now includes tags from entity_tags table (WP-11)
- Export captures full viewport: uses html-to-image for complete node+edge capture, export button always visible (WP-12)
- Edge endpoint selection highlight: CSS for handle hover glow, larger dot size, and primary color on selected edges (WP-13)
- Edge reconnection now works: added `EdgeReconnectAnchor` to all 12 custom edge components (Simple View, UML, ArchiMate) enabling drag-to-reconnect endpoints (ADR-038)
- Canvas connector creation now creates a real relationship record in the database when both nodes are linked to entities, so entity detail pages show the connection
- Edge reconnection and deletion now push to undo history, enabling Ctrl+Z reversal
- PNG gallery mode now displays images: added `cairosvg` as required dependency, thumbnails regenerated on startup for all models, frontend falls back to SVG component on image load error (ADR-032)
- "Used In Models" panel now shows all models including the current model (marked with "(current)") instead of filtering it out, fixing empty list when entity is only in the current model
- Browse mode canvas nodes now show a "View details" hover overlay link for direct navigation to entity detail page
- Session timeout warning no longer appears during active use; the `$effect` timer now reschedules whenever the JWT is silently refreshed by `apiFetch` auto-refresh
- Entity and model API responses now include `created_by_username` field (Pydantic schemas were stripping the field returned by the service layer)
- Version history API responses now include `created_by_username` for all entity and model versions
- Relationships API responses now include `source_entity_name` and `target_entity_name` (service layer JOINs entities table to resolve names)
- Relationships tab on entity detail page now shows entity names instead of raw GUIDs for source/target entities
- EdgeLabel component: fixed import of non-existent `EdgeLabelRenderer` — now correctly uses `EdgeLabel` from @xyflow/svelte
- Canvas nodes now have standard 200px width with word-wrapping descriptions instead of truncation
- New node placement uses grid-based overlap avoidance instead of diagonal offset
- Focus mode edit controls: toolbar (Add Entity, Undo/Redo, Save/Discard) now renders inside the FocusView overlay so controls are visible in fullscreen
- Focus mode no longer renders the normal canvas underneath the overlay

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
