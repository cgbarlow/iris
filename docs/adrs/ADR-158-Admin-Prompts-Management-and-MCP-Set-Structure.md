# ADR-158: Admin AI prompts management redesign + MCP set-structure overview

Status: Accepted (2026-05-12)
Extends: [ADR-094-B](ADR-094-B-AI-Creation-Service.md), [ADR-132](ADR-132-Layered-Creation-Prompts.md), [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md)

## Context

Two unrelated-but-coincident pain points emerged from real UAT usage of v5.12.x.

### Problem 1 — Admin prompts management

The `ai_creation_prompts` table grew from 4 seeded rows in v5.8.0 to 18 in v5.12.0 (15 creation_format + 3 response_format under ADR-157). The admin AI page (`/admin/settings/ai`) showed all rows in a flat list with no filtering, no status toggle, no add, no delete, and edit only updated `prompt_text`. Adding new prompts via API was possible only by direct DB writes. Authoring at scale was painful.

A secondary UX concern: rows like "ArchiMate Process Layout" have `notation=NULL` (intentional under ADR-132's cascade — the row applies to ANY notation that has the `process` diagram_type), but the UI showed `notation: —`, leaving authors to guess what the row actually applies to.

### Problem 2 — MCP set-structure overview

When asked to "jump into the doview book set", Claude Desktop listed top-level chapters E-J but missed A-D. Root cause: `iris-client.list_packages()` didn't expose pagination, so the MCP handler always got the first 50 packages ordered by `updated_at DESC`. Older chapters (A-D — seeded first, never updated) sorted to page 2+. `get_set` returned no `package_count`, no top-level summary, no hint that more existed. The backend already had `/api/packages/hierarchy?set_id=X` returning the complete tree — just not exposed via MCP.

The intended outcome:
- Admins can find, filter, toggle, add, edit, and delete prompts from the GUI with conflict detection.
- The cascade behaviour is visible in the UI ("Any notation × Process diagrams" instead of "notation: —").
- MCP clients see complete set structure without paginating, and know when pagination is needed when they do use it.

Mnemos was considered as a primitive for set-structure summaries and **rejected**. ADR-111's MNEMOS extension is a semantic retrieval layer (ChromaDB vector index for Ask AI), not a hierarchy primitive. No package indexing, no rollups, no scope-level summary API. Different concern entirely.

## Decision

### Part A: Admin prompts management

1. **Extend the existing `/api/ai/creation-prompts` API** with full CRUD:
   - `POST /api/ai/creation-prompts` (admin) — creates a new row. Body: `{name, description, purpose, layer, notation?, diagram_type?, prompt_text, display_order?, is_active?}`. Auto-generates a slug-based `id` with collision suffix.
   - `DELETE /api/ai/creation-prompts/{id}` (admin) — hard delete (no FKs).
   - `PUT /api/ai/creation-prompts/{id}` extended (admin) to accept `name`, `description`, `notation`, `diagram_type`, `display_order` updates (previously only `prompt_text` and `is_active`).
   - **Conflict detection** on `(purpose, layer, notation, diagram_type)` for `is_active=true` rows: POST returns 409; PUT returns 409 if a column change would conflict. Inactive rows can coexist on the same tuple (lets admins stage a replacement before disabling the current).

2. **Rewrite the prompts section of `/admin/settings/ai/+page.svelte`** with:
   - Filter row above the table (purpose / layer / notation / diagram_type / status / search / sort / reset) mirroring `/views/+page.svelte`'s inline pattern. URL-state for `purpose` and `layer` only (matches `/views` scope-filter convention). Other filters session-only.
   - New "Purpose" column with badge.
   - New "Applies to" column resolving the cascade clearly — e.g. `(layer=diagram_type, notation=NULL, diagram_type=process)` renders as **"Any notation × process diagrams"**. Addresses the user's "ArchiMate Process Layout has no notation" confusion.
   - "Status" column becomes a toggle (single-click `PUT {is_active: <new>}`).
   - "Actions" column gains Delete (with confirm dialog).
   - "+ Add prompt" button opens an inline create form with live conflict-check (Save disables when the tuple already has an active row, with an inline note naming the conflicting prompt).
   - Edit modal extended to allow editing name / description / notation / diagram_type (purpose and layer remain immutable post-create — delete-and-recreate to move between).

3. **No filter-bar component extraction** — `/views` doesn't have one and a third screen isn't on the horizon. Avoid over-engineering.

### Part B: MCP set-structure overview

4. **Add `package_count` and `package_count_root` fields to `SetResponse`.** Computed inline in `app/sets/service.py:get_set` and `list_sets` via cheap `COUNT(*)` queries. Lets MCP clients see structural breadth upfront.

5. **Extend `iris-client.list_packages()` with pagination** (`page`, `page_size`, `parent_package_id`). The backend endpoint already supported these — the iris-client signature just didn't expose them.

6. **Add `iris-client.package_hierarchy(set_id, root_id=None)`** wrapping the existing `GET /api/packages/hierarchy` endpoint. Returns a typed list of `PackageHierarchyNode`. Fix a latent bug where the prior misnamed method `package_hierarchy` actually hit `/api/diagrams/hierarchy` — renamed to `diagram_hierarchy` (no prior callers).

7. **New MCP tool `package_hierarchy`** wrapping the new iris-client method. Tool description prefers this over `list_packages` for structural overview. The primary fix — one call returns every chapter regardless of count or update-time ordering.

8. **Extend the `list_packages` MCP tool** with `page`, `page_size`, `parent_package_id` schema. Update the description to flag pagination explicitly so client models know they may need to paginate big sets or prefer `package_hierarchy` for a single-call overview.

## Why a `purpose`/`layer`/`notation`/`diagram_type` tuple conflict for `is_active=true` only

- **Inactive rows must coexist for the staging workflow.** A v5.13.0 admin wants to draft a replacement, review it, then swap it in by toggling the active flag — without deleting their working text or going through a rename dance.
- **Active rows must be unique on the tuple** because the composer cascade is deterministic — two active rows with the same tuple would be a non-deterministic merge that nobody asked for.
- **The conflict message names the offending row** so admins can quickly find and disable it.

## Why the new "Applies to" column instead of renaming seed rows

Renaming "ArchiMate Process Layout" → "Process Layout (any notation)" would lose the original authoring intent (the prompt body still naturally reads as ArchiMate-flavoured for that layout) and rewrite history for no real win. Surfacing the cascade in a dedicated column makes the intent visible at a glance for any row, including future authored ones. Same data, better UI.

## Why `package_hierarchy` as a new MCP tool rather than embedding the tree in `get_set`

- **Predictability of tool-data size.** `get_set` is called everywhere; the response shape matters for context budgets. Big sets (hundreds of packages) would inflate every `get_set` payload. A separate `package_hierarchy` tool is opt-in — the model calls it only when it wants a tree.
- **The breadth signal stays cheap.** `get_set` gains two scalar fields (`package_count`, `package_count_root`) so the model knows whether to bother calling `package_hierarchy` at all.
- **Discoverability via tool description.** `list_packages` and `get_set` descriptions both cross-reference `package_hierarchy` as the preferred structural-overview tool.

## Why fix the latent `package_hierarchy` → `/api/diagrams/hierarchy` bug now

The bug had no callers (zero usages of the iris-client method across the codebase), so the rename is non-breaking. Better to fix while the surface is in flux for ADR-158 than to add a second method `package_hierarchy_tree` alongside the misnamed one. The renamed `diagram_hierarchy` still works for anyone who knew about the old behaviour.

## Consequences

- No DB migrations. The `is_active` column already exists; no new schema needed.
- Backend: 1 new POST endpoint, 1 new DELETE endpoint, extended PUT, two new fields on `SetResponse`, conflict-detection helper.
- iris-client: extended `list_packages` signature with optional pagination + filter; new `package_hierarchy` method; renamed broken `package_hierarchy` to `diagram_hierarchy`; new `PackageHierarchyNode` model.
- MCP: 1 new tool (`package_hierarchy`), extended `list_packages` tool schema.
- Frontend: prompts section of `/admin/settings/ai` rewritten with filter row, status toggle, add/delete, "Applies to" column, conflict check.
- 34 new tests across backend, iris-client, MCP, frontend.
- `docs/prompts/doview-book-mcp-system-context.md` updated to mention `iris_package_hierarchy` as the preferred chapter-list tool.

## Out of scope (deferred)

- **Filter-bar component extraction**: deferred until a third screen wants the same pattern.
- **Soft-delete on creation_prompts**: hard delete with `is_active=false` as the soft alternative is sufficient.
- **Renaming existing seed rows**: covered by the new "Applies to" column.
- **Cascade preview** (showing the full composed system content for a given selector): nice future addition.
- **Server-side pagination on the admin prompts table**: row count is bounded (~50 today, ~200 max), client-side `$derived` is sufficient.
- **Multi-tenant prompt scoping**: ADR-157 already addresses scope-specific overrides via `mcp_system_context`.
- **Embedding the package tree in `get_set`**: explicit `package_hierarchy` tool is the right boundary.
- **Auto-application** of response_format prompts in the Ask Iris pipeline (still deferred per ADR-157).

## See also

- [ADR-094-B](ADR-094-B-AI-Creation-Service.md) — AI diagram creation service.
- [ADR-111](ADR-111-MNEMOS-Semantic-Retrieval.md) — Mnemos extension (considered and rejected for this).
- [ADR-132](ADR-132-Layered-Creation-Prompts.md) — the cascade this PUT extends.
- [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — the `purpose` discriminator and `doview_analysis` artefact this admin GUI now manages.
- [SPEC-158-A](specs/SPEC-158-A-Admin-Prompts-Management-and-MCP-Set-Structure.md) — schema (none), endpoint shapes, MCP wiring, frontend wiring, test plan.
- `docs/prompts/doview-book-mcp-system-context.md` — references `iris_package_hierarchy` as the preferred chapter-list tool.
