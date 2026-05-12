# SPEC-158-A: Admin AI prompts management + MCP set-structure overview

ADR: [ADR-158](../ADR-158-Admin-Prompts-Management-and-MCP-Set-Structure.md)

## Database

**No schema changes.** `is_active`, `purpose` (added in m051), `notation`, `diagram_type` columns on `ai_creation_prompts` are sufficient. `packages.parent_package_id`, `packages.is_deleted`, `packages.set_id` already exist.

## Backend

### `/api/ai/creation-prompts` CRUD (admin-only, ADR-158, v5.13.0)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/ai/creation-prompts` | Admin | Create new prompt; 409 on `(purpose, layer, notation, diagram_type)` conflict for `is_active=true` rows |
| `DELETE` | `/api/ai/creation-prompts/{id}` | Admin | Hard delete |
| `PUT` | `/api/ai/creation-prompts/{id}` (extended) | Admin | Now accepts name/description/notation/diagram_type/display_order in addition to prompt_text/is_active. Re-validates conflict tuple on column changes for active rows. |
| `GET` | `/api/ai/creation-prompts?purpose=` | Admin (existing) | unchanged from v5.12.0 |

**Models** (`backend/app/ai/models.py`):
- `CreationPromptCreate` — new. `name`, `description?`, `purpose: Literal['creation_format', 'response_format']`, `layer: Literal['base', 'notation', 'diagram_type', 'override']`, `notation?`, `diagram_type?`, `prompt_text`, `display_order=0`, `is_active=True`.
- `CreationPromptUpdate` — extended with `name?`, `description?`, `notation?`, `diagram_type?`, `display_order?`. `purpose` and `layer` remain immutable.

**Conflict helper** (`backend/app/ai/router.py`): `_ensure_no_active_conflict(db, *, prompt_id, purpose, layer, notation, diagram_type)` raises 409 with a message naming the conflicting prompt. `prompt_id` excluded from the lookup (so PUT on the row itself doesn't self-conflict).

**Slug helper**: id auto-generated as `_slugify(name)` with `-2`, `-3`, … suffix on collision.

### Set responses gain package counts

`backend/app/sets/service.py`:
- `get_set` adds `package_count` (total non-deleted) and `package_count_root` (`parent_package_id IS NULL`) via two cheap `COUNT(*)` queries.
- `list_sets` adds the same per row in its loop.
- `create_set` initialises both to 0 in the synthetic return dict.

`backend/app/sets/models.py`:
- `SetResponse.package_count: int = 0`
- `SetResponse.package_count_root: int = 0`

## iris-client

`iris-client/src/iris_client/client.py`:

```python
async def list_packages(
    self,
    *,
    set_id: str | None = None,
    collection_id: str | None = None,
    parent_package_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[Package]:
    """ADR-158: pagination + parent_package_id filter."""

async def package_hierarchy(
    self, *, set_id: str | None = None, root_id: str | None = None,
) -> list[PackageHierarchyNode]:
    """ADR-158: hits /api/packages/hierarchy. Returns nested tree."""

async def diagram_hierarchy(
    self, *, set_id: str | None = None, root_id: str | None = None,
) -> dict[str, Any]:
    """Renamed from the misnamed pre-v5.13.0 `package_hierarchy` —
    actually hits /api/diagrams/hierarchy. No prior callers."""
```

`iris-client/src/iris_client/models/core.py`:
- `PackageHierarchyNode` — `id`, `name`, `parent_package_id`, `children: list[PackageHierarchyNode]`. Self-referential under `from __future__ import annotations`.

## MCP server

`mcp/src/iris_mcp/tools.py`:

| Tool | New / Extended | Description (truncated) |
|---|---|---|
| `list_packages` | Extended | "Paginated. Sets with more than 50 packages REQUIRE iterating pages, or you will miss content. For a structural overview, prefer `package_hierarchy`." Schema gains `page`, `page_size`, `parent_package_id`, `collection_id`. |
| `package_hierarchy` | New | "Return the complete package tree for a set as nested PackageHierarchyNode objects in a SINGLE call. Prefer this over `list_packages` for structural overview / chapter list / table-of-contents." |

## Frontend

`frontend/src/routes/admin/settings/ai/+page.svelte` — prompts section rewritten:

- **Filter row** (inline, no extracted component, mirrors `/views/+page.svelte` pattern):
  - Purpose dropdown · Layer dropdown · Notation dropdown · Diagram type dropdown · Status dropdown · text search · Sort dropdown · Reset link · result count
  - URL state: `?purpose=`, `?layer=` (other filters session-only)
- **Table columns**: Name (with description), Purpose (badge), Layer, Applies to, Status (toggle button), Actions (Edit + Delete)
- **`appliesToLabel(p)` helper** resolves the cascade for display:
  - `base` → "Any notation × Any diagram type"
  - `notation` (with notation set) → "{notation} × any diagram type"
  - `diagram_type` (notation NULL or empty) → "Any notation × {diagram_type} diagrams"
  - `diagram_type` (notation set) → "{notation} × {diagram_type} diagrams"
  - `override` (with notation) → "Override: {notation} (replaces all layers)"
- **Status toggle**: single click PUTs `{is_active: !current}`.
- **+ Add prompt** button opens an inline create form with live conflict-check ($derived against the loaded list — Save disables when the tuple already has an active row, with an inline note naming the conflict).
- **Delete** uses an inline confirmation dialog (consistent with the providers section's existing pattern in the same file).
- **Edit modal** extended to allow editing name, description, notation, diagram_type alongside prompt_text. Purpose and layer remain immutable in the UI (consistent with backend PUT semantics).
- **Notations + diagram types** sourced from `/api/notations` and `/api/diagram-types` at mount.

`frontend/src/lib/types/api.ts` — no changes (the inline `CreationPrompt` type in the page handles the new `purpose` field; iris-client model updates are independent).

## Tests

| File | Cases | Layer |
|---|---|---|
| `backend/tests/test_sets/test_package_counts.py` | 5 (empty set, root vs nested counts, list_sets propagation, create-response defaults, soft-delete excluded) | backend |
| `backend/tests/test_ai/test_creation_prompts_crud.py` | 12 (POST happy path, POST 409 on conflict, POST allowed when inactive, POST collision suffix, POST requires admin, POST validation, DELETE 204, DELETE 404, PUT name update, PUT 409 on tuple change, PUT self no-conflict, PUT staging workflow) | backend |
| `iris-client/tests/test_packages_pagination.py` | 7 (list_packages defaults, page+page_size, parent_package_id filter; package_hierarchy typed nodes, set_id+root_id, empty; diagram_hierarchy rename) | iris-client |
| `mcp/tests/test_tools_package_hierarchy.py` | 7 (package_hierarchy nested tree, root_id, empty; list_packages pagination passthrough, defaults; tool registration, description mentions pagination) | MCP |
| `frontend/tests/unit/adminPromptsFilters.test.ts` | 15 (`appliesToLabel` 6 cases including the empty-notation-as-NULL coercion; filter logic 6 cases; conflict detection 3 cases) | frontend |

**Total**: 46 new tests for v5.13.0. Combined with v5.8.x → v5.12.x suite, the codebase tests stand at ~430+ green. Pre-existing `test_no_extra_rls_tables` failure (issue 88 Phase 4 TODO) remains the only acceptable failure.

## End-to-end verification (after deploy)

```bash
# 1. NO migration to run — v5.13.0 has no schema changes.

# 2. Admin AI prompts page (browser):
#    Navigate to /admin/settings/ai
#    - Verify filter row at top of "AI Prompts" section
#    - Filter by purpose=response_format → only the 3 ADR-157 rows
#    - Filter by layer=diagram_type → 11+ diagram_type-layer rows
#    - "Applies to" column reads "Any notation × process diagrams" for
#      creation-archimate-process-v1
#    - Click status toggle → row goes muted (opacity 0.55) and shows ○ inactive
#    - Click "+ Add prompt" → inline form opens
#    - Pick (creation_format, diagram_type, NULL, outcomes_map) →
#      "An active prompt already exists for this combination: 'DoView
#      Outcomes Map Layout'. Disable that prompt first or pick a
#      different combination." and Save is disabled
#    - Toggle the existing outcomes_map row to inactive → conflict
#      clears, Save enables
#    - Delete row → confirm dialog → row removed

# 3. MCP set-structure overview (Claude Desktop):
#    Ask: "Give me the complete chapter list for the doview book set"
#    Expected:
#    - Claude sees package_count_root on the set
#    - Calls iris_package_hierarchy('33032180-d77a-4ce4-88cf-b49cd643e093')
#    - Returns all 10 root chapters A-J in a single call
```

## Out of scope (deferred per ADR-158)

- Filter-bar reusable component extraction.
- Server-side pagination on the admin prompts table.
- Renaming existing seed rows.
- Embedding the package tree in `get_set` responses.
- Cascade preview ("show me the full composed system content for X notation/diagram_type").
- Auto-application of response_format prompts in Ask Iris (still deferred per ADR-157).
