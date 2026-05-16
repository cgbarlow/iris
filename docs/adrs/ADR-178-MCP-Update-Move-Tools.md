# ADR-178: MCP `update_*` and `move_*` tool surface

Status: Accepted (2026-05-16)
Extends: [ADR-161](ADR-161-MCP-Entity-Creation-and-Destination-Flow.md)

## Context

The MCP surface before Phase 3 of issue #133 was: read tools (search / list / get / package_hierarchy) + the `create_*` tools shipped in v5.16.0–v5.17.0 (ADR-161, ADR-162) + the export / render tools shipped in v6.2.0 (ADR-179). No way to **edit** existing entity metadata; no way to **re-parent** entities once placed.

The first end-to-end UAT of the v6.0.15 DoView creation cascade (issue #133) surfaced two concrete needs:

- **Turn 12** — content landed in the wrong Set because the destination chooser didn't yet exist. Phase 1 fixed the prompt; Phase 3 needs the recovery path so the model can actually relocate a misplaced bundle.
- **Turn 13** — a metadata-edit need: rename the new set, fix a description, change the `mcp_system_context` orient sheet.

The broader review (Class B feedback) also flagged that **CLI ↔ API ↔ MCP parity has drifted** — the backend has `PUT /collections/{id}`, `PUT /sets/{id}`, `PUT /packages/{id}`, `PUT /diagrams/{id}`, `PUT /elements/{id}` plus `/parent` re-parenting endpoints, none of which the MCP exposes.

## Decision

Add eight new MCP tools that wrap existing backend endpoints. Five **update tools** for metadata mutation, three **move tools** for in-scope re-parenting.

### Update tools (wrap existing PUT endpoints)

| Tool | Wraps | Fields |
|---|---|---|
| `update_collection(collection_id, name?, description?, system_prompt?, mcp_system_context?, thumbnail_source?, thumbnail_diagram_id?)` | `PUT /api/collections/{id}` | All Collection metadata. |
| `update_set(set_id, name?, description?, system_prompt?, mcp_system_context?, thumbnail_source?, thumbnail_diagram_id?)` | `PUT /api/sets/{id}` | All Set metadata excluding `collection_id` — that's a move, see `move_set`. |
| `update_package(package_id, name?, description?, metadata?)` | `PUT /api/packages/{id}` | Package metadata + arbitrary metadata blob. |
| `update_diagram(diagram_id, name?, description?, data?, metadata?, change_summary?)` | `PUT /api/diagrams/{id}` | Diagram metadata + canvas `data`. The full diagram body is versioned — every successful update increments `current_version`. |
| `update_element(element_id, name?, description?, data?)` | `PUT /api/elements/{id}` | Element metadata + arbitrary data blob. Same versioning model as diagrams. |

All five decorated with `with_web_url` so the response carries a clickable link to the updated entity in the Iris UI (ADR-175 pattern).

### Move tools (wrap `/parent` endpoints + the set `collection_id` field)

| Tool | Wraps | Scope |
|---|---|---|
| `move_diagram(diagram_id, parent_package_id?)` | `PUT /api/diagrams/{id}/parent` | In-set parent change. `parent_package_id=null` moves the diagram to the root of its current set. |
| `move_package(package_id, parent_package_id?)` | `PUT /api/packages/{id}/parent` | In-set parent change. Same null semantics. Backend already cycle-checks. |
| `move_set(set_id, collection_id)` | `PUT /api/sets/{id}` with `collection_id` body | Cross-collection move. Either `collection_id="<existing-uuid>"` or `collection_id=null` to make the set un-grouped. |

### Cross-set moves are NOT in scope for Phase 3

The backend `/parent` endpoints currently only handle in-set re-parenting — moving a package or diagram between sets requires either a new endpoint (`PATCH /packages/{id}/parent` with `target_set_id`, `PATCH /diagrams/{id}/parent` with `target_set_id`) or a multi-step copy + delete. Phase 3 ships the in-set tools; cross-set moves are deferred to a follow-up ADR. Documented as a known gap in the Phase 6 parity matrix.

The cascade destination chooser handles "I want this in a different set" by **creating** the set in the chosen destination first via `create_set` (existing tool), not by moving an already-created bundle. The move tools cover the "I saved into the wrong place by accident" recovery path within the same scope.

### No element re-parenting

Per the issue #133 plan rewrite Q&A, element re-parenting between diagrams is a non-feature. Elements are owned by their parent diagram and travel with it (`move_diagram` drags them along). Documented here as an invariant — there is no `move_element` tool, now or later.

### Cascade prompt update

The Phase-1 cross-set move fallback in `creation-cascade-destination-v1` is dropped — the cascade now instructs the model to either (a) call `create_set` in the target collection and save directly into it, or (b) save into the current set and then call `move_diagram` / `move_package` to relocate. New migration applies the prompt update; the seed file's `CASCADE_DESTINATION_PROMPT` constant is updated in lockstep.

## Why no new backend endpoints

- The PUT endpoints already exist for every entity type — the gap was on the MCP side, not the API side.
- The `/parent` endpoints already cycle-check (`set_package_parent`, `set_diagram_parent`).
- Cross-set moves are the only genuine backend gap; deferring them keeps Phase 3's scope bounded.

## Why MCP-side wrapping rather than iris-client extension

The MCP tools call the backend via `IrisClient._request` directly rather than adding typed methods to `iris-client`. Two reasons:

- Update / move tools are MCP-side conveniences; the AI runtime and CLI consume the backend directly. Adding typed iris-client methods is incidental, not load-bearing, and bloats the client surface ahead of need.
- Phase 4 (CLI parity) is the right scope for promoting these to typed iris-client methods because the CLI will benefit from typed return values. Phase 3 is "minimum-viable MCP coverage"; Phase 4 promotes the shared client surface.

## Consequences

- 8 new MCP tools registered in `mcp/src/iris_mcp/tools.py`.
- All eight handlers call backend endpoints via `IrisClient._request`.
- All eight responses decorated with `with_web_url` for clickable Iris links.
- All eight responses include the `auth_required` payload mapping on 401 (`_auth_required_payload`).
- New migration `m062_drop_phase1_move_fallback.py` + Supabase mirror updating `creation-cascade-destination-v1`.
- `mcp/src/iris_mcp/server_instructions.py:_FALLBACK_INSTRUCTIONS` WORKFLOW GUIDANCE updated to mention the new tools.
- `mcp/README.md` updated with the new tool list under Capabilities.
- CHANGELOG `[6.3.0]`.
- Version bumps: mcp + frontend 6.2.0 → 6.3.0.

## Verification

- `pytest mcp/tests/test_update_tools.py` green — 8 update tool tests (one per entity type × happy path + auth_required mapping where applicable).
- `pytest mcp/tests/test_move_tools.py` green — 6 move tool tests.
- `pytest backend/tests/test_migrations/test_phase3_move_actuation_schema.py` green — migration + seed alignment for the cascade prompt update.
- Manual UAT: cascade picks "save in current set", model creates bundle, user requests "actually move it to the Banana Studies set" → model calls `move_diagram` / `move_set` → success.

## See also

- [ADR-161](ADR-161-MCP-Entity-Creation-and-Destination-Flow.md) — original create_* surface.
- [ADR-175](ADR-175-Web-URL-Decoration-On-Create-Tools.md) — web_url pattern reused here.
- [SPEC-178-A](specs/SPEC-178-A-MCP-Update-Move-Tools.md) — tool signatures, schemas, tests.
- [`docs/plans/issue-133-doview-mcp-polish.md`](../plans/issue-133-doview-mcp-polish.md) — multi-phase plan; this is Phase 3.
- Issue #133 — UAT and parity feedback.
