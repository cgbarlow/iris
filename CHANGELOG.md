# Changelog

All notable changes to Iris are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [5.1.0] - 2026-05-04

Two new notations and a bug fix that unblocked the Iris AI Legislation
feature on Supabase deployments. See
[ADR-135](docs/adrs/ADR-135-DocRef-Supabase-Migration-Parity.md)
through
[ADR-137](docs/adrs/ADR-137-Text-Diagram-Subclass-And-Shared-Markdown-Renderer.md)
for design rationale.

### Added

- **BPMN 2.0 notation** (ADR-136, issue #25). Full BPMN 2.0 §7.4
  element catalogue exposed across canvas, palette, MCP, and AI
  creation. 14 base entity types with discriminator fields on `data`
  (taskType, gatewayType, eventTrigger, eventDirection,
  boundaryInterrupting, subprocessKind, dataKind) cover every legal
  variant without bloating the registry. Adds `collaboration` and
  `choreography` diagram types; the existing `process` type gains
  BPMN as a non-default option (existing process diagrams unaffected).
- **BPMN authoring UX** (ADR-136 §UX). Six-section accordion palette,
  on-element context pad with discoverable wrench tooltip, searchable
  command palette bound to `N` (create-anything), `A` (append-anything),
  `R` (replace), 2D event matrix picker (Iris's strong opinion — no
  surveyed BPMN tool gets this right), always-on right-side property
  panel, and hybrid validation (silent draw-time prevention + persistent
  Problems panel) covering 15 well-known BPMN anti-patterns.
- **Text diagram subclass** (ADR-137, issue #26). Text is a Diagram
  with `diagram_type='text'` and `notation='markdown'`; the markdown
  source lives in `diagrams.data.content`. View mode renders the
  markdown; edit mode shows the source. TOC drawer mirrors the
  Comments tray pattern with depth-indented headings. Hierarchy menu
  gains a "View" submenu (Diagram / Text). Cross-links use the
  `iris://` URL scheme (`[label](iris://diagram/<id>)` /
  `iris://element/<id>`); diagram refs that target a Text document
  render in muted grey.
- **Shared MarkdownView component** (ADR-137). The `marked` +
  `DOMPurify` pipeline extracted into
  `frontend/src/lib/components/MarkdownView.svelte` and adopted by both
  the User Guide and the new Text canvas — DRY consolidation per
  protocol #13. URL scheme allowlist (`http`, `https`, `mailto`,
  `iris`) belt-and-braces against javascript:/data:/file: smuggling.

### Fixed

- **DocRef "Failed to load documents" on Supabase deployments**
  (ADR-135, issue #24). The `docref_documents` and `docref_chunks`
  tables existed only as a SQLite Python migration and were never
  ported to the Supabase SQL set, so the Iris AI Legislation feature
  failed on render-supabase-uat with a Postgres "relation does not
  exist" error surfaced as "Failed to load documents". Adds
  `m043_docref_tables.sql` mirroring the SQLite schema (TIMESTAMPTZ
  for dates, RLS enabled, admin-write/all-read policies). Static
  parser test enforces ongoing parity so this can't regress silently.

### Docs

- ADR-135 / SPEC-135-A — DocRef Supabase migration parity rule.
- ADR-136 / SPEC-136-A — BPMN 2.0 notation including UX recommendations
  researched against the most-loved BPMN tools (bpmn-js, Camunda
  Modeler, Bizagi, Lucidchart).
- ADR-137 / SPEC-137-A — Text diagram subclass and shared markdown
  renderer.
- `docs/deployment-render-supabase.md` — migration list extended to
  m041–m043; DocRef migration explicitly called out.

## [5.0.1] - 2026-05-04

### Fixed
- **iris-cli `login` against Supabase-mode backends.** The CLI was
  POSTing to `/api/auth/login`, which is intentionally 404'd in
  Supabase deployment mode (auth flows through Supabase Auth). The
  command now accepts `--token <PAT>` to skip the username/password
  flow entirely — mint a PAT externally (curl + Supabase JWT, or the
  upcoming frontend Settings → API Tokens page) and hand it to the
  CLI. Without `--token` against a Supabase backend, the command
  exits with an actionable error pointing to the `--token` workaround
  rather than the cryptic 404 detail.

### Docs
- `docs/cli.md` — `iris login --url` requires the **iris-api backend
  service**, not the frontend or iris-mcp host. Spelled this out plus
  the SQLite-vs-Supabase deployment-mode split, with a curl recipe
  for minting a PAT in Supabase mode.

## [5.0.0] - 2026-05-04

Major release: iris becomes agent-friendly. Three coordinated surfaces
— a stable HTTP API with Personal Access Tokens, a CLI, and an MCP
server — let humans and AI agents drive iris with the same auth,
search, browse, ask, and export capabilities the web frontend uses.
See [ADR-127](docs/adrs/ADR-127-Personal-Access-Tokens.md) through
[ADR-134](docs/adrs/ADR-134-MCP-Standalone-Service.md) for full
design rationale.

### Added
- **Personal Access Tokens** (ADR-127). New `/api/users/me/tokens` mgmt
  endpoints let any authenticated user mint long-lived revocable
  `iris_pat_…` bearer tokens for CLI / MCP / agent use. Tokens inherit
  the creating user's role, are Argon2id-hashed, and the plaintext
  value is returned exactly once. Authorisation goes through the same
  `Authorization: Bearer …` header the frontend uses — the auth
  dependency routes `iris_pat_` tokens through a new PAT validator and
  leaves the JWT code path unchanged.
- **Server-side export** (ADR-128). New `/api/export/*` endpoints
  produce JSON or Markdown bundles for diagrams, elements, packages,
  sets, and collections. Anonymous-friendly (ADR-123 parity), subject
  to a 10,000-element cap per bundle. Complements ADR-039 — client-side
  visual export in the browser is unchanged.
- **Public OpenAPI docs** (ADR-129). `/api/docs` (Swagger UI) and
  `/api/openapi.json` are now served in every environment, not just
  debug mode. `docs/api.md` describes the auth model, rate-limit
  buckets, and the unversioned-path + `-v2` deprecation policy.
- **Per-auth-type rate-limit buckets**. Middleware now splits traffic
  into `login` / `refresh` / `anon` / `anon_ai` / `pat` / `general` and
  tunes each independently so a busy CLI user can't starve browser
  traffic and vice versa. Configurable via `IRIS_RATE_LIMIT_*` env vars.
- **iris-client** (ADR-132): shared async Python client library under
  `iris-client/`. Typed methods for every v1 endpoint plus an SSE
  streaming helper for `ask`.
- **iris-cli** (ADR-130): Python command-line tool (`iris`) for read-
  only + AI operations. `iris login`, `iris search`, `iris diagrams
  get`, `iris export diagram|set|… --format json|markdown`, `iris ask
  --stream`, etc. Installable via `uv tool install` from the repo;
  config in `~/.config/iris/config.toml` (0600).
- **iris-mcp** (ADR-131): stdio Model Context Protocol server for AI
  agents. Installable into Claude Desktop / Claude Code / Cursor via a
  three-line config block. Exposes ~19 tools and `iris://` resources.
- **Remote MCP transport** (ADR-133): iris-mcp now also runs as a
  Streamable-HTTP server mounted on the iris backend at `/mcp`. End
  users add iris to Claude Desktop / Cursor by pasting the URL into
  the connector UI — no Python, no uv, no git, no JSON config edit.
  Stdio transport (ADR-131) remains the option for offline/local use.
- **iris-mcp standalone service** (ADR-134): the production MCP
  endpoint runs as its own Render web service alongside the iris
  backend. Splits the MCP SDK's memory footprint off the iris-api
  dyno (which OOM'd on the 512 MB free tier when MCP was embedded).
  The embedded mount stays in the codebase, opt-in via
  `IRIS_EMBEDDED_MCP=1` for one-process local dev. Bare `/mcp`
  requests no longer 307-redirect to `/mcp/` — some MCP clients drop
  POST bodies on chase, fixed by a path-normalising middleware.

### Changed
- `POST /api/ai/files/extract` no longer requires a JWT — it now uses
  `get_optional_user`, matching the other AI endpoints under ADR-123.
  Anonymous callers are subject to the existing `anon_ai` rate-limit
  bucket.
- Root `pyproject.toml` declares a uv workspace with members
  `iris-client`, `cli`, `mcp`. Backend stays outside the workspace for
  now.

### Deploy notes
- No new env vars required to run; optional tuning via
  `IRIS_RATE_LIMIT_PAT` (default 60/min) and `IRIS_RATE_LIMIT_ANON`
  (default 30/min).
- Supabase deployments pick up the new `personal_access_tokens` table
  automatically via `m042_personal_access_tokens.sql` (idempotent; RLS
  enabled, owner-only policies).

## [4.3.0] - 2026-04-22

### Added
- **AI "Create Diagram" extended beyond DoView to four more notations (ADR-132).** The layered-prompt framework built for DoView (ADR-094) has been scaled out: AI-assisted creation now supports Simple (component, roadmap, free-form), UML (sequence, class), ArchiMate (process), and C4 (deployment) — seven new notation × diagram-type bundles in addition to DoView's outcomes_map and overview. The notation dropdown in the Ask-AI "Create Diagram" tab is now registry-driven (no pre-selected default — user picks from DoView, Simple, UML, ArchiMate, or C4). A second diagram-type dropdown appears for non-DoView notations, populated from `GET /api/registry/creation-catalogue`. DoView's creation flow is unchanged — its own Stage 0–3 prompt still drives outcomes_map/overview branching internally. Eleven new prompt rows are seeded via SQLite migration `m040` and Supabase migration `m041`; existing DoView rows are untouched. See SPEC-132-A (prompt authoring) and SPEC-132-B (selector UI contract).
- **Location picker now lets you pick Collection → Set → Package** when generating AI diagrams without a pinned Set. Closes a pre-existing gap where `POST /api/ai/sets//create-diagram/apply` 404'd when no Set was selected on the `/ask` page.
- **UML sequence diagrams materialise correctly.** AI-generated `{nodes, edges}` for `diagram_type=sequence` are translated in `create_diagrams_from_ai` into the `{participants, messages, activations}` shape the dedicated sequence renderer expects, so the canvas populates on first paint.

### Changed
- Creation-mode system prompt now prepends a "User selection" preamble when both notation and diagram_type are known, and each non-DoView notation prompt skips Stage 0 when sufficient context (Set content, attached files, docref, prior chat) is present — reduces redundant "which diagram type?" / "describe the system" rounds.

## [4.2.1] - 2026-04-22

### Fixed
- **Settings now visible in the sidebar for anonymous visitors.** The Theme, Default Notation, and Visual Toggles sections of `/settings` are all localStorage-backed and meaningful to everyone — no reason to hide them behind sign-in. Moved `/settings` from the authenticated-only nav list to the public nav list; the page itself hides the Change Password form for anonymous users (no account to change a password on). Every signed-in role including **Viewer** has always had access to `/settings`; this fix extends that to anonymous browsing so theme and notation preferences can be set without creating an account.

## [4.2.0] - 2026-04-21

### Added
- **Comprehensive user guide (`/guide`).** The guide has been expanded from 10 thin sections to 16 deep sections covering every user-facing capability — not just the read-only surface. Six new sections: **Canvas Editing** (lock UI, edit-mode, add/link element, connect mode, undo/redo, save, fullscreen); **Notations** (Simple / Component / UML / ArchiMate / C4 / Sequence / DoView / Roadmap reference); **Comments** (per-diagram and per-element threads); **Imports & Data** (Sparx EA, PowerPoint, DocRef legislation, recycle bin, version history & rollback); **Roadmap (Scenia)**; **Themes & Accessibility** (theme switching, per-element theming, WCAG 2.2 AA). Existing nine sections were rewritten with deeper detail. Sign-in-only material is called out inline with a "Sign in to use this" blockquote — anonymous visitors can discover every feature Iris offers even before authenticating (SPEC-122-A amended).
- **Social preview card when Iris URLs are shared.** Pasting an Iris URL into LinkedIn, Slack, Teams, WhatsApp, or any platform that reads Open Graph / Twitter Card metadata now renders a rich card: the user's dashboard screenshot at `frontend/static/iris-preview.png`, the title *Iris — Integrated Repository for Information & Systems*, and a short description. Metadata lives in `src/app.html` (not `<svelte:head>`) because Iris is a static SPA and social scrapers don't execute JS; tags are templated at build time via `%sveltekit.env.PUBLIC_SITE_URL%` so the same build works for every deploy. Declared in `render.yaml` as `PUBLIC_SITE_URL`, `sync: false` (ADR-126).
- **Eye favicon.** The favicon has been replaced from the default Svelte logo to a hand-written eye SVG (almond shape + blue iris + dark pupil + white catch-light) reflecting the Iris name. Single-file change under `frontend/src/lib/assets/favicon.svg`.

### Changed
- Screenshot generator (`frontend/tests/screenshots/generate.spec.ts`) now produces six new shots (`imports.png`, `recycle-bin.png`, `admin-banner.png`, `admin-users.png`, `admin-audit.png`, `admin-locks.png`) alongside the existing ten. Re-run via `npm run screenshots` whenever the UI changes meaningfully.

### Deploy notes
- Set the new `PUBLIC_SITE_URL` environment variable in the Render frontend service for each environment (e.g. `https://iris-uat.chrisbarlow.nz`). Without it, social-preview URLs resolve as relative paths, which work on some platforms but not all.

## [4.1.3] - 2026-04-21

### Fixed
- **Supabase search SQL placeholder bug — this is the actual reason search returned zero results on UAT.** `_search_postgres` used `%s` (psycopg-style) inside the `ts_rank(...)` subexpression of every SELECT while the rest of the query used `?` (SQLite-style). The Iris DB adapter converts `?` to asyncpg's `$N` but leaves `%s` as literal text, so queries sent to Postgres had an un-bound `%s` token — Postgres either errored or the query silently returned nothing. Converted all five entity queries (elements, diagrams, packages, sets, collections) to consistent `?` placeholders. Placeholder/parameter counts now match exactly. This complements v4.1.2's schema migration (which was necessary but not sufficient — the schema was right, the Python call site was broken).
- Verify on UAT: typing `msd` on the dashboard should now return the MSD package + related diagrams. No re-migration needed; v4.1.2's `m040` still applies.

### Changed
- **User Guide moved to the header; keyboard shortcuts merged in; `/help` route deleted.** The "Guide" sidebar entry has been replaced by a "User Guide" link in the header (replacing the old "Help" link) so docs sit consistently with the other session-level actions (Sign in/Sign out, theme). The Keyboard Shortcuts section previously on `/help` is now a section of the User Guide (`/guide/keyboard-shortcuts`), expanded with the full sidebar shortcut list. The old `/help` route has been removed; any bookmarks pointing there should be updated to `/guide`.

## [4.1.2] - 2026-04-21

### Fixed
- **Search parity on Supabase** — on the Supabase/PostgreSQL backend (production/UAT), the search endpoint only queried `elements` and `diagrams` — packages/sets/collections had no `search_vector` columns and no trigger functions, so admin-created packages like "NZ Ministry of Social Development (MSD) DoView Strategy Diagram" were invisible to search even though they existed in the database. Additionally, the existing `BEFORE INSERT OR UPDATE` triggers on `elements`/`diagrams` read from `*_versions` tables at trigger time, but services insert the version row *after* the parent row — so the parent's `search_vector` was empty on initial create and only populated on subsequent updates. Fix ships in two pieces (ADR-125):
  - **New migration `m040_search_all_entities.sql`** — adds `search_vector` columns + GIN indexes + trigger functions for `packages`, `sets`, `collections`. Adds chain-triggers on `element_versions`, `diagram_versions`, `package_versions` that re-fire the parent's BEFORE trigger after the version row is committed, closing the INSERT-ordering gap. Backfills every existing row in all five entity tables.
  - **`_search_postgres` extended** — now queries all five entity types to match `_search_sqlite` feature-for-feature. Scope filters (set/collection) apply uniformly; deep links point to `/packages/<id>`, `/sets`, `/collections` consistently with the SQLite path.
- Requires manual application of `m040` to the UAT Supabase instance (via Supabase SQL Editor or `scripts/supabase-migrate.sh`) — Render does not run migrations automatically.

## [4.1.1] - 2026-04-21

### Added
- **System notification banner** — admins can post a system-wide message from Admin → Settings that renders as a sticky top strip on every page for every visitor (anonymous included). Dismissible per-message per-browser-session; a new admin-posted message re-appears even if the previous one was dismissed. Reuses the existing `settings` key-value table under `notification_banner_message`; the admin write path is the existing admin-gated `PUT /api/settings/{key}` (DRY). A focused public `GET /api/notifications/banner` lets anonymous visitors see the message without auth. Plain-text only — no HTML, no Markdown, Svelte's default `{expression}` escaping is the XSS defence (ADR-124, SPEC-124-A).

### Fixed
- **Cleaner AI provider error messages** — the previous "LLM provider error" 502s surfaced the raw `httpx` error including the provider URL (e.g. "Server error '502 Bad Gateway' for url 'https://api.agentics.org.nz/...'"). New `app/ai/error_mapper.py` classifies provider exceptions (timeout, network/connect, 429 rate-limit, 401/403 auth, 5xx upstream, 4xx client, generic) and returns a concise user-facing message. Stack traces still go to server logs for operators. Applies to both `POST /api/ai/ask` / `POST /api/ai/sets/{id}/ask` and the admin "Test" button on each provider. Raw URLs never leak to users (regression-tested).

### Notes
- The AI provider health badge (red/green dot in the model picker) already exists in `SetQA.svelte` via the `_run_ping_check` infrastructure from earlier releases — no change needed. The system banner is the right channel for admins to explain a known outage.

## [4.1.0] - 2026-04-21

### Added
- **User guide at `/guide`** — hand-written Markdown documentation with a left-hand navigation bar covering Getting Started, Dashboard, Collections & Sets, Packages & Diagrams, Knowledge Graph, Search, Ask AI, Bookmarks, and Admin. Markdown rendered through `marked` + DOMPurify (protocol #7). Screenshots generated on demand via `npm run screenshots` (new Playwright project) and served from `static/guide/` so the deployed app has them without rebuilding. Nav entry added to AppShell for both anonymous and authenticated users (ADR-122, SPEC-122-A, closes #15).
- **Anonymous read-only mode** — visitors can now browse every collection, set, package, diagram, element, knowledge graph, and run searches without signing in. Ask AI is also available to anonymous callers with a stricter per-IP rate limit (default 10 requests/hour, env `IRIS_RATE_LIMIT_ANON_AI`). Writes and admin routes remain authenticated. Backend gains a `get_optional_user` dependency; frontend `+layout.svelte` no longer redirects unauthenticated users to `/login`, with a new `admin/+layout.svelte` gate preserving admin privacy. A "Sign in" button replaces "Sign out" in the header when anonymous (ADR-123, SPEC-123-A, closes #18).

### Fixed
- **Dashboard search silently filtered by a stale set id** — typing "msd" on the dashboard at `/` with no visible filter returned zero results when a previously-viewed set id was cached in sessionStorage. The counts panel legitimately restored the last set (visible in the header), but the search bar does not display its scope, so a remembered filter read as "search is broken". Fix: split `searchSetId`/`searchCollectionId` deriveds that read URL params only; counts panel unchanged. Deep-linked scoped search via `?set_id=…` still works (ADR-121, closes #16 and #17).
- **Packages, sets, and collections were not indexed for search on create/update/delete** — only the startup `rebuild_search_index` populated their FTS5 tables, so any entity created or imported after the server started was invisible to search until the next restart. This is the deeper root cause behind "search is broken" on UAT where "NZ Ministry of Social Development (MSD) DoView Strategy Diagram" (a package) is expected to match `msd`. Fix: added per-operation `index_package`/`index_set`/`index_collection` and `remove_*_index` calls in all three services, mirroring the existing elements/diagrams pattern. Bug surfaced the first time newly-created entities failed to appear in search — no reindex needed for existing data because startup rebuild still runs.

## [4.0.4] - 2026-04-21

### Fixed
- **Knowledge graph radial hierarchy ordering** — on UAT-scale single-collection data (711 nodes, 11 sets × 60 packages × 639 diagrams) packages were consistently settling *outside* their own diagrams (mean package-radius ≈ 170–190 px vs mean diagram-radius ≈ 140–150 px; 0/11 sets radially ordered correctly), inverting the expected `collection → set → package → diagram → element` visual flow. Root cause: every diagram has both a set_membership edge (distance 120) and a hierarchy edge (distance 25); the N short hierarchy links collectively yanked each package outward through its own children. Fix: per-galaxy radial layer force (`d3.forceRadial`-style inline loop) pinning each node type to a prescribed radius from its collection centroid — Collection=0, Set=120, Package=240, Diagram=360, Element=480, all scaled by `link_length × node_spacing`. Inter-galaxy separation is now radius-aware (`target = 2·R_total + padding`) instead of centroid-only `1/dist²`. The SPEC-119-A inner-layer `1/dist²` calls at the set and root-package layers are superseded (ADR-120, SPEC-120-A).
- **Same-tier label overlap** — two labels at the same hierarchy tier (e.g. two packages, two diagrams) could visually overlap because the label overlap-suppression loop only compared against higher-precedence tiers (`b.tier < ti`). Now compares against every already-drawn label; same-tier draw order is sorted by `relationship_count` descending, so the most-connected label wins the space.

## [4.0.3] - 2026-04-20

### Fixed
- **"Direct diagram links" toggle no longer collapses the knowledge graph** — turning off this visibility toggle previously removed the set→diagram edges from the force simulation entirely, not just the visual rendering, which deleted the link force (distance 120 px) that blooms each set's diagrams into a visible petal around their set node. Without that force, the galaxy-style separation between collections (ADR-119 / SPEC-119-A) collapsed into a compressed cluster near the graph centre. Fix: use force-graph's `linkVisibility` callback to hide these edges visually while keeping them in the physics — the toggle is now a pure display control (ADR-119, SPEC-119-A follow-up). Also relaxes the ADR-118 regression test's inter-collection monotonicity assertion from strict step-wise (`mid ≥ low ∧ high ≥ mid`) to endpoint-only (`high > low`) — with ungated inner-layer 1/dist² repulsion the individual step-wise comparison is noisier than the full-sweep invariant.

## [4.0.2] - 2026-04-20

### Fixed
- **Knowledge graph collections now repel each other as whole clusters** — restores the "galaxy" effect where each collection (with all its sets, packages, diagrams, and elements) acts as a cohesive mass repelling other collections through every tier of its member hierarchy. ADR-118's gating confined cross-collection separation to the centroid-level collection layer only, so collection bboxes could still visually mingle when inner clusters were wide. ADR-119's first cut kept that gating; this follow-up ungates the inner `1/dist²` layers so set- and package-level repulsion fires across collections as well as within. Self-decay at `1/dist²` and linear spread scaling keep the added cross-layer force from compounding into the pre-ADR-118 "loses the plot at spread=3" explosion (ADR-119, SPEC-119-A)

## [4.0.1] - 2026-04-20

### Fixed
- **Knowledge graph cluster collapse on large single-collection datasets** — at UAT scale (observed on "DoView Strategy Models": 11 sets × 60 packages × 639 diagrams, 711 nodes) the bidirectional target-distance separator at the set and root-package layers introduced by ADR-118 compressed all per-set diagram clusters to within ±100 px of the graph centre, because a fixed target distance of `150 × spread` px assumed a cluster density that dense data violates. Reverted the force shape at the set and root-package layers to self-decaying `1/dist²` pure repulsion — cluster equilibrium radius is now set by charge balance, so the layout adapts to whatever density the data has (5 members or 500). Collection layer keeps its bidirectional pull-back (anchors the orphan-set contract). Regression captured as a Playwright page.route fixture of the real UAT /api/graph response so the test is fast, deterministic, and CI-friendly (ADR-119, SPEC-119-A)

## [4.0.0] - 2026-04-20

### Added
- **Multi-entity knowledge graph** — interactive force-directed graph on the dashboard showing elements, diagrams, and packages as colour-coded nodes with all relationship types (element relationships, package relationships, diagram links, diagram→element canvas refs, diagram→package refs, hierarchy containment); includes settings panel to toggle each node and edge type on/off, responsive side-by-side layout with diagram hierarchy on wide screens, and hover-to-zoom from hierarchy to graph (ADR-116)
- **Graph settings: physics sliders and admin defaults** — label density, node spacing, size contrast, and link length sliders with real-time graph updates; admin-configurable defaults per global/collection/set scope stored in database; user overrides via localStorage with "Reset to defaults" button; cascading settings: hard-coded → admin DB → user localStorage (ADR-117)
- **Graph data API** — `GET /api/graph?set_id=X` endpoint returning elements, diagrams, and packages as nodes with 6 edge types in a single optimised call, with collection-scope support; `GET/PUT /api/graph/settings` endpoints for admin-default graph settings (ADR-116, ADR-117)
- **Diagram-level AI context scoping** — Diagram dropdown on the Ask AI Context tab filters AI context to a specific diagram and its elements, bypassing MNEMOS for precise scoped queries; dropdown populates from selected sets and follows Collection dropdown styling
- **Session file upload for AI context** — upload files (PDF, DOCX, XLSX, PPTX, CSV, text) on the Ask AI Context tab as session-scoped AI context; text extracted server-side via stateless endpoint, held in browser state, and included alongside sets and legislation in chat requests; supports drag-and-drop, 5 MB limit, and files-only conversations (ADR-115)
- **Advanced provider parameters** — collapsible Advanced Settings section in the AI provider edit modal exposing top_p, top_k, min_p, frequency_penalty, presence_penalty, and stop sequences; parameters are provider-aware with unsupported ones silently omitted (ADR-114)
- **Model selector in Ask AI** — compact dropdown in the chat toolbar allowing users to choose which AI provider to use per conversation, with a new lightweight `GET /api/ai/providers/active` endpoint (ADR-114)
- **DocRef legislation integration** — optional extension for importing NZ legislation documents from legislation.docref.nz as AI context; browse and import chunked CSVs with progress indicators, select imported legislation alongside sets and collections on the Ask AI page, with hourly background index refresh (ADR-112)
- **MNEMOS semantic retrieval** — optional MNEMOS extension for AI-powered semantic context retrieval, replacing naive token-budget truncation with question-aware ranking across sets; managed via admin Extensions tab with graceful fallback to direct retrieval when unavailable (ADR-111)
- **RetrievalPort abstraction** — protocol-based retrieval strategy allowing pluggable context backends; `DirectRetrieval` wraps existing `context.py`, `SemanticRetrieval` uses MNEMOS (ADR-111)
- **Bulk DoView PPTX import** — upload multiple .pptx files in one operation via `POST /api/import/pptx/batch`, all grouped under a single set with per-file error reporting and partial success support (ADR-108)
- **Package-level AI context** — Ask AI set selector now supports drilling down into packages within each set, constraining AI context to specific packages for more focused responses (ADR-109)
- **Scenia cloud deployment** — Scenia roadmapping app added as a third Render Blueprint service, pulling from the external fork as a static site with CORS and cross-service URL configuration (ADR-110)
- **Collection-scoped filtering** — clicking a collection card now filters sets, diagrams, elements, and search results across dashboard and list pages

### Changed
- **Ask AI tabbed layout** — split Ask AI page into Context and Request tabs; context selectors on first tab, expanded chat dialogue on second tab with selected dataset summary (ADR-113)

### Fixed
- **AI discuss crash** — added missing `mode` and `thread_id` columns to `ai_conversations` table (SQLite migration m033)
- **Knowledge graph spread slider on multi-collection views** — replaced the cubic `spread³` cluster force with a bidirectional target-distance separator, gated set- and root-package-level separation to within a single collection, and removed the inverse-spread cohesion decay; the `node_spacing` slider now behaves predictably across its full 0.2–3.0 range instead of "losing the plot" at the extremes (ADR-118)
- **Knowledge graph orphan-set drift** — sets with no collection (e.g. the "default" set) now participate in the collection-layer force under a synthetic `__orphan_<sid>` group, so the bidirectional separator pulls them back when farther than target. Previously these nodes had no collection-layer force at all and ratcheted outward under charge repulsion each time the spread slider rose (ADR-118, SPEC-118-A)

## [3.0.0] - 2026-03-25

### Added
- **Extensions framework** — database-backed extension registry with admin settings tab for installing, enabling, and disabling optional integrations; all extension state persists across restarts (ADR-103)
- **Scenia roadmapping integration** — open-source roadmapping tool integrated as the first Iris extension, with full CRUD for strategies, programmes, initiatives, assets, applications, milestones, resources, and dependencies (ADR-104)
- **Scenia React embedding** — full Scenia React app mounted at `/scenia` via `createRoot`, with pluggable db adapter replacing IndexedDB with Iris API calls (ADR-106, fork: cgbarlow/waylonkenning_scenia)
- **Roadmap data view** (`/roadmap`) — Iris-native tabular view of all Scenia entities with "View in Scenia" links and set selector
- **Scenia bulk data API** — atomic read/write endpoints (`GET/PUT /api/scenia/data`) matching Scenia's `getAppData()`/`saveAppData()` interface
- **Scenia-specific tables** — timeline settings, version snapshots, asset categories, and application statuses with set-scoped data isolation
- **Extension gating** — FastAPI dependency that gates all Scenia routes on extension availability; returns 404 when extension is not installed or disabled
- **Scenia seed data** — full demo data (6 strategies, 6 programmes, 40 assets incl. GEANZ catalog, 40 initiatives, 8 applications, 30 app segments, 14 milestones, 9 dependencies, 6 resources) seeded on extension install
- **10 interlinked diagrams** — Strategic Overview, 6 Programme Roadmaps, Asset Landscape, Dependency Map, Resource Allocation — all with entity-backed nodes and inter-diagram links
- **Cross-links (Iris ↔ Scenia)** — "View in Scenia" buttons on element detail pages and canvas panel; "View in Iris" links from Scenia
- **Conditional Roadmap navigation** — sidebar shows "Roadmap" nav item only when Scenia extension is enabled
- **DoView PPTX import** — import DoView models from .pptx files with structural compliance validation, shape classification (overview tiles, final outcomes, outcome boxes, causal arrows), column-based causal link inference, cross-diagram navigation linking, and colour preservation (ADR-107)

## [2.7.4] - 2026-03-25

### Added
- **Collections** — higher-level grouping for Sets with full CRUD, thumbnails, dashboard stats card (4-column layout), collection-scoped filtering on Elements/Diagrams pages, and `Iris / Collection / Set` header breadcrumb (ADR-102)
- **Multi-set AI context** — Ask AI now supports selecting multiple Sets (with or without a Collection) as context for Discuss and Create Diagram workflows via new `POST /api/ai/ask` endpoint
- **Collection pill on Sets page** — Sets belonging to a Collection display the collection name as a pill badge
- **Linked Diagram property editor** — set, change, or clear a node's linked diagram directly from the edit sidebar (ADR-099)

## [2.7.2] - 2026-03-23

### Added
- **Visual Toggles** settings section — user-controlled display preferences for diagram nodes (ADR-101)
- **Element count badge** — optional top-right badge on nodes showing how many diagrams each element is used in, toggled via Settings → Visual Toggles
- **Hide description toggle** — `hideDescription` theme rendering option; DoView defaults to hidden, per-node override in edit sidebar

### Changed
- **DoView element-backed nodes** — all DoView diagram nodes are now created as proper elements with `entityId` linkage, and all causal links as relationships with `relationshipId`, enabling cross-diagram element reuse and diagram-entity relationship tracking (ADR-100)
- AI diagram creation (`create_diagrams_from_ai`) now materialises element and relationship records for every node and edge

### Fixed
- Double borders on DoView nodes — removed duplicate `visualStyle` application from DoviewRenderer wrapper
- Stale seed test assertions for diagram count (35 → 39) after DoView diagrams were added in v2.6.0
- Seed test setup missing migrations m028 (AI creation prompts) and m029 (sequence order)

## [2.7.1] - 2026-03-22

### Added
- **Diagram sequence order** — user-controllable ordering of diagrams and packages in the navigation hierarchy tree (ADR-098, Issue #7)
- `PUT /api/diagrams/reorder` endpoint for reordering diagrams/packages within a parent group
- Drag-and-drop reordering in the dashboard hierarchy tree with visual drop indicators
- `sequence_order` field on diagrams and packages tables (migration m029/m032)

### Fixed
- Entity-to-entity relationships not displayed in diagram Relationships tab — field name mismatch `elementId` → `entityId` in relationship query (ADR-097, Issue #4)
- Diagram relationships endpoint crash on SQLite — replaced unsupported `async for` cursor iteration with `fetchall()`
- DoView seed builder functions missing positional arguments — startup crash on fresh database

## [2.6.0] - 2026-03-21

### Added
- **DoView notation** — fifth notation in Iris for outcomes-based theory of change diagrams (ADR-094)
- DoView entity types: `outcome_box`, `final_outcome`, `overview_tile`, `source_reference`
- DoView relationship type: `causal_link` (grey arrow, 2px)
- DoView diagram types: `outcomes_map` (left-to-right causal flow) and `overview` (navigation tiles)
- `doview` notation added to registry with `free_form` cross-notation mapping
- DoView default theme (`doview-default`) with 10-color palette (yellow, pink, blue, green, beige, lavender, peach, cyan, grey, white)
- `DoviewRenderer.svelte` — node renderer for all DoView entity types with color overrides
- `DoviewEdgeRenderer.svelte` — causal link edge renderer with grey arrow styling
- Dynamic dispatch: `DynamicNode`/`DynamicEdge` route `doview` notation and DoView entity types
- DoView notation detection in `notation_detection.py`
- Entity dialog and diagram creation dialog support for DoView
- Seed example DoView diagrams: DoView Overview (navigation tiles) and Outcomes Map (4-column causal flow)
- Migration m027 for notation, diagram types, mappings, and DoView theme
- **AI Diagram Creation system** — layered system prompt composition for AI-guided diagram creation (ADR-094-B)
- `ai_creation_prompts` table with layered prompt architecture: base / notation / diagram_type / override (migration m028)
- `build_creation_system_prompt()` — composes layered prompts; override layer replaces all others
- `create_diagrams_from_ai()` — materialises AI-generated JSON into Iris canvas diagrams with `linkedDiagramIndex` resolution
- Admin creation prompts endpoint: `GET /api/ai/creation-prompts`, `PUT /api/ai/creation-prompts/{id}`
- Apply creation endpoint: `POST /api/ai/sets/{set_id}/create-diagram/apply`
- Creation mode toggle in Ask AI chat — switches to DoView creation mode with notation selector
- "Create Diagrams" action button appears when AI outputs a valid diagram JSON block
- Admin Creation Prompts editor in `/admin/ai/` — table of layered prompts with full-text edit modal
- Seeded default prompts: base output format, DoView methodology (guided 8-question conversation), outcomes_map layout rules, overview layout rules
- **Optional Supabase/Render deployment** (ADR-094, ADR-096) — cloud deployment path alongside the default SQLite self-hosted mode
- `DatabasePort` protocol with `SqliteAdapter` (aiosqlite passthrough) and `SupabaseAdapter` (asyncpg with automatic `?` → `$N` placeholder conversion)
- `IRIS_DB_BACKEND` env var (`sqlite` default, `supabase` for cloud mode)
- PostgreSQL migrations (`backend/app/migrations/supabase/`) — 30 SQL files covering all schema including FTS via `tsvector`/GIN indexes and triggers
- Supabase migration m028: DoView notation, diagram types, notation-type mappings, and DoView default theme (Supabase equivalent of SQLite m027)
- Supabase migration m029: `ai_creation_prompts` table and 4 seeded layered prompts (Supabase equivalent of SQLite m028)
- `profiles` table in Supabase mode: maps `auth.users` UUIDs to Iris roles; auto-created by trigger on user creation
- Supabase Auth JWT validation (`app/auth/supabase_service.py`) — HS256, no aud verification
- `GET /api/auth/me` endpoint (both modes) — returns authenticated user profile
- Dual search: FTS5 for SQLite, `tsvector`/`to_tsquery` for PostgreSQL (`app/search/service.py`)
- `render.yaml` Blueprint with static site (frontend) and web service (backend) definitions
- `VITE_API_BASE_URL` env var — configurable backend URL for cross-origin Render deployment (empty default preserves self-hosted mode)
- `frontend/src/lib/config.ts` — runtime config from `VITE_DB_BACKEND`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`
- `frontend/src/lib/supabase.ts` — conditional Supabase JS client (null when not configured)
- Supabase mode frontend auth: `onAuthStateChange` token sync, `supabase.auth.signInWithPassword()` login, `supabase.auth.refreshSession()` token refresh
- Login page: email field and Supabase sign-in in Supabase mode; setup/request-account/forgot-password views hidden (managed via Supabase Dashboard)
- `.env.example` documenting all environment variables for both deployment modes
- `docs/deployment-render-supabase.md` — step-by-step Render + Supabase deployment guide
- Optional backend dependency: `asyncpg==0.31.0` (install with `uv sync --extra supabase`)

### Security
- **Row Level Security** enabled on all 34 Supabase tables with deny-all strategy (ADR-095) — blocks `anon` and `authenticated` roles from direct PostgREST table access while backend (`postgres` role) bypasses RLS as table owner

### Changed
- Seed data bumped to v7 with Iris System DoView (39 diagrams, 66 elements, 63 relationships)
- `build_edge_visual()` returns `None` (not `{}`) when no visual overrides are present — consistent with `build_node_visual()`
- `DatabaseManager` now accepts `AppConfig` (preferred) or `DatabaseConfig` (backward-compatible)
- All service functions: `db` parameter type updated from `aiosqlite.Connection` to `DatabasePort` (no runtime change in SQLite mode)
- `app/auth/dependencies.py`: `get_current_user` branches on `db_backend` — SQLite checks `users` table, Supabase checks `profiles` table
- `app/auth/router.py`: login/refresh/setup/change-password return 404 in Supabase mode; setup/status always returns `needs_setup: false` in Supabase mode
- `app/users/router.py`: list/update users reads from `profiles` table in Supabase mode; create user returns 501 (use Supabase Dashboard)
- `app/middleware/audit.py`: JWT decoded with correct secret per mode; username resolved from `profiles` (Supabase) or `users` (SQLite)
- `frontend/src/lib/utils/api.ts`: `tryRefresh()` delegates to Supabase SDK in Supabase mode
- `frontend/src/lib/stores/auth.svelte.ts`: `clearAuth()` calls `supabase.auth.signOut()` in Supabase mode

## [2.5.0] - 2026-03-19

### Added
- AI model management module (`backend/app/ai/`) — DB-backed provider registry, client abstraction, admin CRUD, Set-scoped Q&A (ADR-093)
- `ai_providers`, `ai_conversations`, `ai_usage_log` tables (migration m026)
- `AIClient` ABC with `OpenAICompatibleClient` (openai, ollama, lmstudio, openrouter, custom) and `AnthropicClient`
- Retry logic: exponential backoff on network/5xx errors; no retry on timeouts or 4xx auth (translated from machine-dream_ag patterns)
- `build_set_context()` — structured text context builder from Set elements, relationships, diagrams with token-budget truncation
- Provider CRUD API (`GET/POST/PUT/DELETE /api/ai/providers`), test endpoint, set-default endpoint
- Set Q&A endpoint (`POST /api/ai/sets/{set_id}/ask`) with SSE streaming support
- Conversation history endpoint (`GET /api/ai/sets/{set_id}/conversations`)
- Usage log endpoint (`GET /api/ai/usage`) for admin visibility
- Admin AI Providers page (`/admin/ai`) — provider list, add/edit modal with password input for API keys, test connection, set default, delete
- Brain icon for AI Providers in sidebar navigation (Phosphor Brain)
- Dedicated **Ask AI** page (`/ask`) with Set selector — accessible from main navigation between Dashboard and Sets
- Chat-style Q&A component with SSE streaming responses, animated thinking indicator, markdown rendering (`marked` + DOMPurify), copy-to-clipboard, and clear conversation
- Inline error display on provider test results (no hover required)
- AI module seed data: 4 new elements (AI Service, AI Client, Provider Registry, Context Builder), 8 relationships, and "AI Module Architecture" diagram under Simple Notation
- AI Module navigation tile on Iris Navigation overview
- `dev.sh` now sources `.env` file for API keys and env var overrides

### Changed
- API keys stored directly in DB (not env var names) — enterable via admin UI password field
- Set detail page links to `/ask` instead of embedding inline Q&A panel
- Seed data bumped to v5 with AI module additions (34 diagrams, 59 elements, 58 relationships)

### Security
- API keys stored in DB, never returned by API (`has_api_key: bool` in responses)
- Admin-only provider CRUD via existing `_require_admin()` pattern
- DOMPurify sanitization on all AI-generated content rendered via `{@html}` (Protocol 7)
- Input length cap: 4000 chars on question field via Pydantic `max_length`
- Context token budget (default 8000 tokens) prevents excessive LLM costs
- All AI calls logged to `ai_usage_log` + `iris_audit.db`

## [2.4.2] - 2026-03-19

### Added
- Title/description font controls in NodeStylePanel (separate colour, size, bold, italic for title vs description)
- Icon colour picker in NodeStylePanel
- Theme-aware fallback chain (per-element → theme → CSS fallback) in NodeStylePanel

### Changed
- NavigationCellNode refactored for faithful EA card rendering
- NodeStylePanel split into Node, Title Font, and Description Font sections
- Import service auto-detects navigation-cell-dominated diagrams as `free_form/simple`
- iris-default-simple theme seeds navigation_cell element defaults

### Fixed
- Parent package validation on diagram creation (clears invalid parent_package_id)
- ArchiMate/UML renderer visual override propagation
- Sequence viewport edge case

## [2.4.1] - 2026-03-09

### Added
- Comments sidebar — comments moved from page bottom to toggleable right sidebar with badge count
- Comments button visible in browse mode (windowed and fullscreen), hidden in edit mode
- Live preview of element edits on canvas (name, description, type reflect instantly while editing)
- ElementEditPanel component for inline element editing in the canvas sidebar
- NodeStylePanel wired into diagram page edit-mode sidebar alongside ElementEditPanel
- Unsaved changes confirmation dialog when switching from edit to browse mode
- Diagram relationships API endpoint (`GET /api/diagrams/{id}/relationships`) including diagram links
- Diagram link deletion endpoint (`DELETE /api/diagram-relationships/{id}`)
- Diagram links migration (`m025_diagram_links`)
- Hierarchy sidebar in fullscreen mode (browse and edit) with search and filter
- Hierarchy sidebar scroll position preserved across navigation
- Sidebar toggle button in fullscreen mode overlay
- Relationship indicator dot on Relationships tab when relationships exist
- Comment author username display (resolved via LEFT JOIN on users table)
- Relative timestamp formatting for comments ("just now", "5m ago", "3h ago", "2d ago")
- Themes link in admin navigation sidebar
- `areThemesLoaded()` helper in themeStore for conditional eager loading

### Changed
- Canvas height uses `calc(100vh - 317px)` to align bottom edge with hierarchy sidebar
- Canvas area extends to fill space freed by removing bottom comments section
- Page content shifts with `margin-right: 316px` when any sidebar is open (entity detail or comments)
- No page scrollbar when all content fits viewport (negative bottom margin technique)
- Entity detail sidebar and comments sidebar are mutually exclusive
- Sequence toolbar uses inline SVG icons matching SvelteFlow Controls styling
- ThemeSelector groups themes by notation with current notation first
- `discardChanges()` reloads diagram from API to guarantee clean state
- `parseCanvasData()` deep-clones diagram data to prevent edit mutations
- New canvas nodes default to `width: 200` for consistent sizing
- FocusView accepts `hideExit` prop to suppress exit button when sidebar is open
- Browse-mode canvas uses `panX` to shift viewport when sidebar opens

### Fixed
- Comments displayed user GUID instead of username — backend now JOINs users table
- Comment timestamps displayed raw ISO format — now shows friendly relative time
- Canvas spilling off bottom of screen — aligned with hierarchy sidebar via precise offset calculation
- Page scrollbar appearing despite content fitting — cancelled parent padding overflow

## [2.4.0] - 2026-03-09

### Added
- C4 hybrid visual notation with canonical colours and inline SVG type glyphs (ADR-092)
- C4TypeGlyph and C4TypePicker components for rich C4 type selection
- `borderStyle` support in theme system (NodeVisualOverrides, visualStyles, themeStore)
- C4 default theme seed with canonical colours (green person, blue system, red external) and dashed borders
- NotationPills component — clickable pill notation selector replacing dropdowns
- Version history restore/rollback UI with confirmation for elements and diagrams
- Diagram rollback API endpoint (`POST /api/diagrams/{id}/rollback`)
- Eager theme loading to prevent flash on diagram page

### Changed
- C4Renderer uses inline SVG glyphs instead of Lucide icons
- NodeStylePanel uses C4TypePicker for C4 notation nodes
- EntityDialog renamed "Create Entity" → "Create Element", uses NotationPills and C4TypePicker
- DiagramDialog uses NotationPills instead of notation dropdown
- Element detail page uses C4TypePicker in edit mode, C4TypeGlyph in view mode
- Edit mode badge styling: dark bg with white text (light theme), inverted for dark theme
- Center-to-center edge connections default to straight line routing
- Smoothstep edges use borderRadius=20, bezier edges use curvature=0.4
- Connection handle dots hidden in browse mode

### Fixed
- Theme loading flash on diagram page initial load
- ThemeSelector no longer lazy-loads themes (loaded eagerly by page)

## [2.3.6] - 2026-03-08

### Added
- Node resizing via drag handles in edit mode using SvelteFlow NodeResizer (ADR-091-A)
- NodeStylePanel wired into diagram page — select a node in edit mode to style it (ADR-091-A)
- Node resize changes persisted to visual overrides (width/height) on save (ADR-091-A)
- Lucide icon library (`lucide-svelte`) with 100+ curated architecture modelling icons (ADR-091-B)
- `IconRef` type and `NodeVisualOverrides.icon` field for per-node icon storage (ADR-091-B)
- Icon registry (`iconRegistry.ts`) resolving `IconRef` to Lucide Svelte components (ADR-091-B)
- `IconDisplay.svelte` component for rendering icons at any size from an `IconRef` (ADR-091-B)
- Semantic icon matcher (`icon_matcher.py`) — matches EA element names/stereotypes to Lucide icons via keyword similarity (ADR-091-B)
- Set-wide icon consistency: same element name always resolves to same icon across all diagrams in an import (ADR-091-B)
- NavigationCellNode renders matched Lucide icons when `visual.icon` is set, falls back to NID SVGs (ADR-091-B)
- Icon picker modal (`IconPicker.svelte`) with search, category filters for browsing and selecting icons (ADR-091-C)
- Icon section in NodeStylePanel — add, change, or remove node icons via the picker (ADR-091-C)
- Icon tag index (`iconTags.json`) shared between frontend search and backend matching (ADR-091-B)

## [2.3.5] - 2026-03-07

### Fixed
- All 144 diagrams now have correct node background colors — EA default white (#FFFFFF) emitted when Backcolor is unset (ADR-090)
- All 40 diagrams with unstyled edges now have explicit black line color — EA default #000000 emitted when LineColor is unset (ADR-090)
- 3 edges with stereotype but no name now display stereotype text as label with guillemets (ADR-090)

### Added
- Iterative visual audit framework (ea-audit.mjs) with comparison tracking across iterations (ADR-090)

## [2.3.4] - 2026-03-07

### Fixed
- All 149 diagrams now render edges correctly — unified handle IDs between backend and frontend (ADR-089)
- Node content no longer clipped — switched from fixed `height` to `min-height` for EA-imported nodes (ADR-089)
- Long text in fixed-width nodes truncated with ellipsis instead of hidden (ADR-089)
- All node types (UML, ArchiMate, C4, Boundary) now have dual source+target handles at every position (ADR-089)

### Added
- Comprehensive automated diagram audit script (`frontend/audit-diagrams.mjs`) covering 14 check categories (ADR-089)

## [2.3.3] - 2026-03-07

### Fixed
- Note "Feature Properties" no longer duplicates title in body — label prefix stripped from description (ADR-088)
- Attribute text in abstract classes renders upright — `font-style: normal` blocks italic inheritance (ADR-088)
- Node widths match EA dimensions exactly — `fixedSize` mode with `overflow: hidden` (ADR-088)
- Composition/aggregation edges show both diamond source marker and open arrow target marker (ADR-088)
- Diamond markers extend outward from node — `refX=0` instead of `18` (ADR-088)
- Edges auto-route via geometrically optimal handles when EA specifies auto-routing (ADR-088)
- Edge cardinality and role labels positioned per EA's stored LLB/LLT/LRT/LRB coordinates (ADR-088)
- Diagram frame zooms and pans with canvas — converted from absolute-positioned SVG to SvelteFlow node (ADR-088)
- Fixed-size node content no longer clipped — UML icons hidden and compact padding/line-height applied (ADR-088 R3)
- Package nodes now appear on diagrams — no longer skipped during import (ADR-088 R3)
- Diagram frame type label shows mapped type ("class", "pkg") instead of raw EA type ("Logical", "Package") (ADR-088 R3)

### Added
- Dual-type handles on UML nodes — each side accepts both source and target connections (ADR-088)
- `compute_auto_handles()` backend function for geometry-based handle selection (ADR-088)
- `DiagramFrameNode.svelte` component for canvas-integrated diagram frames (ADR-088)
- EA label position parsing (LLB/LLT/LRT/LRB) from `t_diagramlinks.Geometry` (ADR-088)

## [2.3.2] - 2026-03-06

### Added
- Diagram frame/title block for imported EA diagrams — shows `[type] [name]` tab with border (ADR-087)
- Attribute sort option (`pos` or `alpha`) in view config for canvas (ADR-087)
- EA connector `Start_Edge`/`End_Edge` mapped to SvelteFlow handles for explicit connection points (ADR-087)
- EA orthogonal routing via `t_diagramlinks.Path` waypoints rendered as polyline edges (ADR-087)
- EA absolute connection points (`PtStartX/Y`, `PtEndX/Y`) override auto-computed handle positions (ADR-087)

### Fixed
- Abstract class `«abstract»` stereotype text no longer shown when EA theme active — italic-only conveys abstract (ADR-087)
- UML class name labels properly centered in node header (ADR-087)
- Abstract class names render as italic-only (not bold+italic) when EA theme active (ADR-087)
- Note elements use original EA dimensions — fixes overlap with adjacent elements (ADR-087)
- Theme selector dropdown now overrides diagram's preferred theme when explicitly changed (ADR-087)
- Note background and border colors respect theme configuration via CSS variables (ADR-087)
- SVG markers (diamonds/arrows) visible at all zoom levels with `overflow: visible` (ADR-087)

### Changed
- `ThemeRenderingConfig` extended with `hideTypeStereotypes` and `abstractBoldOverride` fields (ADR-087)

## [2.3.1] - 2026-03-06

### Added
- UML class attributes rendered in compartments on canvas nodes (imported and user-created) (ADR-086)
- UML visibility prefixes (+/-/#/~) from EA Scope field on attributes (ADR-086)
- SVG marker definitions for UML arrowheads: filled diamond, open diamond, closed triangle, open arrow (ADR-086)
- Cardinality labels at edge endpoints, controlled by view config (ADR-086)
- Role name labels at edge endpoints, controlled by view config (ADR-086)
- Edge style panel for editing cardinality, roles, stereotype after creation (ADR-086)
- Relationship dialog extended with cardinality, role, stereotype fields for UML notation (ADR-086)
- Edit lock integration: lock acquired on edit, conflict banner, heartbeat, auto-release (ADR-080, ADR-086)
- POST lock release endpoint for sendBeacon compatibility (ADR-086)

### Fixed
- Attributes from EA import not appearing on canvas class nodes
- UML edges rendered without arrowheads/diamonds
- Edit mode not acquiring lock per ADR-080 specification
- sendBeacon lock release using non-existent endpoint
- UML class nodes showing description text causing massive overflow — now hidden on compartment types (ADR-086)
- Node height forced to EA pixel value clipping content — now uses min-height for natural sizing (ADR-086)
- EA orthogonal route style (Auto Route) incorrectly mapped to bezier — now maps to step routing (ADR-086)

## [2.3.0] - 2026-03-05

### Added
- Per-element visual overrides — nodes and edges carry optional `visual` properties (bgColor, borderColor, fontColor, width, height, lineColor, lineWidth, dashArray) applied as inline styles (ADR-085)
- Theme system — `themes` table with CRUD API (`GET/POST /api/themes`, `GET/PUT/DELETE /api/themes/{id}`), notation-linked visual profiles with element defaults, stereotype overrides, and edge defaults (ADR-085)
- Seed themes: "Iris Default UML" (white/black), "Sparx EA Default UML" (yellow class boxes with stereotype colours for feature/DataType/CodeList/XSDsimpleType/choice), "Iris Default Simple" (ADR-085)
- Style cascade: per-element visual > stereotype override > element type default > global theme default > renderer hardcoded defaults (ADR-085)
- EA import colour preservation — reads ObjectStyle, Backcolor, Fontcolor, Bordercolor from t_object and t_diagramobjects; builds visual override dicts via `build_node_visual()` and `build_edge_visual()` (ADR-085)
- EA import explicit dimensions — imported element width/height from EA coordinates now stored in `data.visual.width/height` and applied as inline styles, overriding CSS min-width defaults (ADR-085)
- EA import stereotype threading — element Stereotype stored in `node_data["stereotype"]` for theme resolution (ADR-085)
- Theme selector dropdown in diagram toolbar — shows available themes for the current notation (ADR-085)
- NodeStylePanel — per-element style editor with colour pickers, border width, font size, bold/italic toggles, and "Reset to theme defaults" button (ADR-085)
- Admin Themes page — CRUD for themes grouped by notation, with JSON config editor (ADR-085)
- Themes link on admin dashboard page (ADR-085)

### Changed
- All renderers (UML, Simple, ArchiMate, C4, BaseNode, BaseEdge) apply `data.visual` overrides as inline styles (ADR-085)
- DynamicNode computes effective visual by merging active theme defaults with per-element overrides before passing to renderers (ADR-085)
- EA import reader reads additional columns: ObjectStyle (t_diagramobjects), Backcolor/Fontcolor/Bordercolor/BorderWidth (t_object), LineColor/IsBold/LineStyle (t_connector) (ADR-085)

## [2.2.0] - 2026-03-05

### Added
- Support for importing Sparx EA .eap (JET4/MDB) files via mdbtools conversion (ADR-084)
- Artifact element type mapping for SparxEA import (maps to component)

### Fixed
- Import API now returns `packages_skipped` and `diagrams_skipped` fields (were missing from response)
- SparxEA diagram type mapper updated to use registry-compatible types with correct notation assignment (ADR-079)
- Gallery thumbnails now render for all diagram types, not just the original five

## [2.1.0] - 2026-03-05

### Added
- Notation filter dropdown on diagrams and elements list pages
- ADR-083: Comprehensive seed diagrams covering all 31 diagram-type/notation permutations
- Seed hierarchy reorganised by notation (Simple, UML, ArchiMate, C4 packages) with 32 diagrams, 55 elements, and 50 relationships
- ~40 new seed elements across UML, ArchiMate, and C4 notations describing the Iris system
- Use Case and State Machine diagram types for UML notation (ADR-082)
- System Context and Container diagram types for C4 notation (ADR-082)
- Motivation and Strategy diagram types for ArchiMate notation (ADR-082)
- ArchiMate notation mapping added to Roadmap diagram type, C4 mapping added to Sequence (ADR-082)
- Element type filtering by diagram type in canvas EntityDialog — shows only relevant types per diagram (ADR-082)
- "Show all types" override toggle in EntityDialog to bypass diagram-type filtering (ADR-082)
- Default notation user setting in Settings page — stored in localStorage, choose Simple/UML/ArchiMate/C4 (ADR-081)
- Elements carry notation field (`notation` column) — displayed in browse mode popup and element detail page (ADR-081)
- Diagram Type and Notation Registry — separates structural diagram type (component, sequence, class, deployment, process, roadmap, free_form) from visual notation (simple, uml, archimate, c4) via database registry tables with many-to-many mapping (ADR-079)
- Registry API endpoints: `GET /api/registry/diagram-types`, `GET /api/registry/notations`, `PUT /api/registry/diagrams/{id}/notation` (ADR-079)
- Auto-detection of notations present on canvas — scans node entity types and stores detected notations per diagram (ADR-079)
- Notation dropdown in DiagramDialog — two-step selection: pick diagram type, then pick notation (filtered by valid pairs, default pre-selected) (ADR-079)
- Notation and detected_notations display on diagram detail page, list view, and gallery view (ADR-079)
- Edit Locking System — pessimistic advisory locks with 15-minute timeout, heartbeat extension, and lazy expiry cleanup for diagrams, elements, and packages (ADR-080)
- Lock API endpoints: `POST /api/locks`, `GET /api/locks/check`, `PUT /api/locks/{id}/heartbeat`, `DELETE /api/locks/{id}`, `GET /api/locks`, `DELETE /api/admin/locks/{id}` (ADR-080)
- Lock manager composable (`locks.svelte.ts`) with auto-heartbeat and beforeunload release (ADR-080)
- Admin Locks page for viewing and force-releasing active edit locks (ADR-080)
- Cascade delete for packages — deleting a package soft-deletes all descendant packages and diagrams with a shared group ID (ADR-078)
- Descendant count warning — delete confirmation dialog shows exact count of child packages and diagrams before deletion (ADR-078)
- Recycle bin page — browse, restore, and permanently delete soft-deleted items with grouped restore for cascade deletions (ADR-078)
- Recycle bin navigation item in sidebar
- Set filtering on bookmarks page — uses the same SetSelector pattern as other list pages (ADR-078)
- Restore capability for packages, diagrams, and elements — creates version record with `change_type='restore'` (ADR-078)
- Diagram hierarchy tree on dashboard when a set is selected — reuses existing TreeNode component (ADR-076)
- C4 System Context diagram in example seed showing Iris with external actors and systems (ADR-077)
- Seed auto-migration from v1 flat format to v2 package hierarchy (ADR-077)
- Hierarchy sidebar on package detail page — reuses TreeNode component from diagram view
- Shared VersionHistory component for consistent card-style version display across all detail pages

### Changed
- Locks admin nav icon changed from sliders to padlock (ADR-083)
- Bookmarks moved above Import in sidebar navigation order
- DiagramDialog now shows Notation first, filtering available diagram types by selected notation (ADR-081)
- EntityDialog shows visible Notation dropdown for entity type filtering, onsave includes notation (ADR-081)
- Simple notation streamlined to 5 domain types + 2 universal types (removed package, queue entity types and composes, implements relationship types) — Phase C of ADR-079
- EntityDialog now filters available entity types by current diagram notation (simple, uml, archimate, c4) (ADR-079)
- Diagram type filter dropdown on diagrams list page updated to reflect registry types (component, sequence, class, deployment, process, roadmap, free_form) (ADR-079)
- Example seed uses explicit notation values per diagram (ADR-079)
- Example seed reorganized into 4-package hierarchy with 7 diagrams demonstrating
  package nesting, parent_package_id, modelrefs, and C4 notation (ADR-077)
- Set gallery thumbnail now uses client-side DiagramThumbnail component (DRY with diagram gallery)
- Package detail page layout matches diagram detail page (tab bar, spacing, button styles)
- Parent package field displays name instead of GUID

### Fixed
- Dashboard now reads active set from global store when no URL parameter is present, ensuring hierarchy tree loads after set selection on Sets page
- Sets page list and gallery views no longer constrain width with max-width, matching other pages
- C4 diagrams now render SVG thumbnails in diagram gallery view
- ArchiMate and C4 node description text legibility on coloured backgrounds

## [2.0.0] - 2026-03-04

### Changed
- **BREAKING:** Entity → Element rename throughout: database tables (`elements`, `element_versions`, `element_tags`), API routes (`/api/elements/`), frontend routes (`/elements/`), types, and UI labels (ADR-071)
- **BREAKING:** Model → Diagram + Package split: `models` table split into `diagrams` and `packages` tables with dedicated API routes (`/api/diagrams/`, `/api/packages/`), frontend routes (`/diagrams/`), and UI labels (ADR-071)
- **BREAKING:** Model relationships → Package relationships: `model_relationships` table renamed to `package_relationships` with API route `/api/packages/{id}/relationships` (ADR-071)
- Canvas architecture: single DynamicNode/DynamicEdge with notation-aware rendering replaces 30+ separate node/edge components (ADR-068)
- Elements render according to diagram notation — same element appears differently on UML vs ArchiMate vs C4 diagrams
- Migration m016: renames tables, splits models into diagrams + packages, rebuilds FTS5 indexes, migrates all foreign keys (ADR-071)
- Migrations m002-m015 now skip safely on re-init after m016 has run
- UnifiedCanvas split into separate browse/edit SvelteFlow instances to fix Svelte 5 duplicate attribute error
- Canvas node browse-mode links updated: `/entities/` → `/elements/`, `/models/` → `/diagrams/`
- Import summary shows Packages count instead of Sparx Diagrams count
- Sets thumbnail source accepts both "model" and "diagram" values for backward compatibility

### Added
- BaseNode/BaseEdge shared components eliminating code duplication across all canvas components (ADR-068)
- Type equivalence map for cross-notation element compatibility (ADR-068)
- SparxEA connector direction, cardinality, roles, stereotypes, and routing now imported (ADR-070)
- UML-correct arrow markers on edges (open arrow, closed triangle, filled/open diamond)
- Cardinality and role name labels at edge endpoints
- Stereotype display as `<<name>>` on edges
- Edge properties panel for editing metadata on user-created edges
- Package as first-class concept with dedicated `packages` and `package_versions` tables
- `backend/app/elements/` module (renamed from `entities/`)
- `backend/app/diagrams/` module (renamed from `models_crud/`)
- `backend/app/packages/` module (new, for package CRUD)
- `backend/app/package_relationships/` module (renamed from `model_relationships/`)
- Backward-compatible type aliases in `api.ts`: `Entity = Element`, `Model = Diagram`, etc.
- `DiagramDialog`, `DiagramPicker`, `DiagramThumbnail`, `ElementPicker` frontend components
- Package metadata enrichment: import captures ea_guid, Status, Stereotype, Version, Scope, Author, Complexity, Phase, dates, and tagged values from SparxEA (ADR-072)
- Package detail page (`/packages/[id]`) with Overview, Details, and Extended accordion sections displaying all enriched metadata and tagged values
- Import idempotency: re-importing the same .qea file skips existing packages, elements, and diagrams matched by ea_guid (ADR-073)
- Import summary shows skip counts for packages and diagrams on the import results page
- Force-delete set now cascades packages and package_relationships
- C4 model support: Person, Software System, Container, Component, Code Element, Deployment Node, Infrastructure Node, Container Instance element types with level badges and C4 colour scheme (ADR-074)
- C4 relationship type with label and technology annotation
- C4Renderer and C4EdgeRenderer for notation-aware canvas rendering
- Type equivalences extended with C4 mappings (component→c4_component, actor→person)
- Admin-configurable Views: named profiles controlling UI feature visibility — toolbar element/relationship types, metadata sections, canvas options (ADR-075)
- Two default views: Standard (simplified, hides advanced features) and Advanced (full functionality)
- Views REST API: GET/POST/PUT/DELETE on `/api/views` with default view protection
- View selector dropdown in top navigation for switching active view
- Admin views page (`/admin/views`) for creating, editing, and deleting views
- Global view store with localStorage persistence of active view selection

### Fixed
- Class nodes render correctly in browse mode (ADR-068)
- Note and Boundary nodes render in UML edit mode (ADR-068)
- SparxEA Note elements import with content-derived labels instead of "Unknown" (ADR-069)
- Canvas nodes from import always include `description` field (ADR-069)

### Removed
- ModelCanvas, FullViewCanvas, BrowseCanvas and 30+ individual node/edge components (replaced by DynamicNode/DynamicEdge + renderers) (ADR-068)
- `backend/app/entities/` module (replaced by `elements/`)
- `backend/app/models_crud/` module (replaced by `diagrams/` and `packages/`)
- `backend/app/model_relationships/` module (replaced by `package_relationships/`)
- `ModelDialog`, `ModelPicker`, `ModelThumbnail`, `EntityPicker` frontend components
- Old frontend routes: `/entities/`, `/models/`

## [1.8.0] - 2026-03-03

### Added
- Inline "Edit Metadata" on model detail page — replaces popup dialog with in-place editing of Name, Description, Tags, and Template toggle (ADR-065, SPEC-065-A)
- Inline "Edit Metadata" on entity detail page — replaces popup dialog with in-place editing of Name, Description, and Tags
- Entity detail page accordion layout with Summary, Details, and Extended groups matching model page pattern
- Entity clone button on detail page header
- Extended metadata display for entities: scope, abstract, persistence, author, complexity, phase, EA created/modified dates, gen_type, tagged values table
- SparxEA import: 9 additional element fields (Scope, Abstract, Persistence, Author, Complexity, Phase, CreatedDate, ModifiedDate, GenType)
- SparxEA import: 6 additional attribute fields (Notes, Default, LowerBound, UpperBound, Stereotype, Scope)
- Enriched attribute import format — attributes imported as structured objects (name, type, notes, default, bounds, stereotype, scope) instead of flat strings
- 7 new backend tests for extended import fields (4 reader, 3 import)
- ADR-065: Inline Edit, Entity Detail Revamp, Extended Import
- SPEC-065-A: Inline Edit, Entity Detail Revamp specification
- First-class model relationships: `model_relationships` DB table, REST API (`POST/GET /api/models/{id}/relationships`, `DELETE /api/model-relationships/{id}`), and Relationships tab on model detail page (ADR-066, SPEC-066-A)
- `note` and `boundary` entity types for SparxEA Note/Boundary elements — previously skipped during import
- NoteNode canvas component: yellow background, folded corner CSS, DOMPurify-sanitized HTML content
- BoundaryNode canvas component: dashed border, transparent background
- `note_link` relationship type with NoteLinkEdge canvas component (dotted line)
- Self-referencing relationship support with SelfLoopEdge canvas component (cubic bezier loop)
- SparxEA import: Package-to-Package dependencies imported as model relationships
- Import change summary in version history — entities show "Imported from SparxEA (Class)", models show "Imported from SparxEA (PackageName)"
- Migration m015 for `model_relationships` table with unique constraint and cascade indexes
- Create entity and model relationships from Relationships tab with multi-step picker flow (ADR-067, SPEC-067-A)
- "Add to canvas?" prompt after creating relationships from the Relationships tab
- Canvas modelref-to-modelref connections auto-create backend `model_relationships` records
- Node removal dialog (`NodeDeleteDialog`): "Remove from this model" or "Delete entity and all relationships"
- Cascade entity deletion (`DELETE /api/entities/{id}?cascade=true`) removes entity from all model canvases and soft-deletes all relationships
- "Remove" button in canvas toolbar when a node is selected in edit mode
- 7 new model relationship backend tests, 4 new cascade delete tests, 5 new import tests
- ADR-066: Import All Skipped Items
- SPEC-066-A: Import All Skipped Items specification
- ADR-067: Unified Relationship Management & Entity Removal
- SPEC-067-A: Unified Relationships & Entity Removal specification

### Fixed
- Smart tab default on model detail page: `userSelectedTab` now resets when navigating between models, ensuring empty models default to Details tab and populated models default to Canvas

### Changed
- Model detail tab renamed from "Overview" to "Details"
- SparxEA attribute import format changed from strings to objects (backward-compatible in canvas nodes)
- Model and entity detail accordion changed from multiple to single selection mode
- "Edit Metadata" button renamed to "Edit Details" on model and entity detail pages
- Accordion "Summary" group renamed to "Overview" on model and entity detail pages
- Entity editing from model canvas now navigates to entity detail page in edit mode (via `?edit=true`)
- SparxEA import no longer skips Note, Boundary, NoteLink, self-references, or Package-to-Package dependencies
- `SKIP_OBJECT_TYPES` reduced to `{Text, UMLDiagram, Constraint}`; `SKIP_CONNECTOR_TYPES` is now empty
- `create_entity()` and `create_model()` accept optional `change_summary` parameter for initial version
- `EntityPicker` and `ModelPicker` accept optional `title`/`subtitle` props for reuse in different contexts
- Canvas Delete/Backspace key now opens confirmation dialog instead of direct node removal
- `CanvasEdgeData` includes optional `modelRelationshipId` field

## [1.7.2] - 2026-03-03

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
