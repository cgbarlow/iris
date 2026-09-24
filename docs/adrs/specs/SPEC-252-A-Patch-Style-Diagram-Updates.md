# SPEC-252-A: Patch-Style Diagram Updates (`patch_diagram`)

Implements **[ADR-252](../ADR-252-Patch-Style-Diagram-Updates.md)** (issue #301).
Extends [SPEC-003-A](./SPEC-003-A-Entity-Domain-Model.md) (diagram CRUD) and
builds on [SPEC-249-A](./SPEC-249-A-Relationship-Tools-For-Agents.md).

## 1. REST contract

`PATCH /api/diagrams/{id}` — auth required; same write-scope gate as `PUT`.

Request headers: `If-Match: <version>` (optional). Body:

```json
{"operations": [ {"op": "...", ...}, ... ], "change_summary": "optional"}
```

`operations`: 1–200 items (`MAX_OPERATIONS`), applied in order.

| `op` | Fields | Behaviour | Result |
|------|--------|-----------|--------|
| `add_node` | `node` (canvas or flat AI shape) | Normalised as ADR-218. Rejects: non-object, empty/missing `id`, duplicate id, `position` without numeric `x` and `y`, `parentId` naming no node, `data.entityId` not a live element in the diagram's set. Appended. | `{id}` |
| `update_node` | `id`; any of `position` (object of numeric `x`/`y`, merged), `width`, `height` (numbers), `type` (non-empty string), `data` (object) | Unknown fields rejected. `data` shallow-merged, `null` deletes the key. A changed `data.entityId` is validated as in `add_node`. | `{id}` |
| `remove_node` | `id`, `cascade_edges` (bool, default `true`) | Rejects a missing node and a node other nodes are nested in (`parentId`). Connected edges are removed with it; with `cascade_edges: false` their presence is an error. | `{id, removed_edges: [...]}` |
| `add_edge` | `edge` (canvas or flat shape) | Rejects: missing `id`/`source`/`target`, duplicate id, source/target not an existing node, a `data.relationshipId` that is not a live relationship whose `{source_element_id, target_element_id}` equals the two nodes' `data.entityId`s (either direction). Appended. | `{id}` |
| `update_edge` | `id`; any of `data` (merged as above), `sourceHandle`, `targetHandle`, `type` (string or null) | Unknown fields (incl. `source`/`target`) rejected. A changed `data.relationshipId` validated as in `add_edge`. | `{id}` |
| `remove_edge` | `id` | Rejects a missing edge. | `{id}` |
| `sync_labels` | `node_ids` (optional list) | For each targeted node with a `data.entityId`: `data.label` ← the element's current name. Nothing else changes. Unknown `node_ids` rejected; nodes whose element is deleted/unknown are skipped. | `{ids: [changed], skipped: [...]}` |

Every result also carries `index` and `op`. Other top-level canvas keys
(`viewport`, …) are preserved. A stored payload with neither `nodes` nor
`edges` but other keys (markdown `{content}`, sequence `{participants}`) is
rejected as a whole (`op_index: null`); an empty payload is an empty canvas.

Responses:

| Status | Body |
|--------|------|
| 200 | `{id, current_version, updated_at, applied, results[]}` |
| 400 | `If-Match` not an integer |
| 401 / 403 | not signed in / outside write-scope |
| 404 | diagram missing or deleted |
| 409 | `detail: {error: "version_conflict", message, current_version, expected_version}` |
| 422 | `detail: {error: "operation_failed" \| "invalid_patch", message, op_index, op}`; or FastAPI validation (0 or >200 operations) |

`message` reads `operations[<i>] (<op>): <reason>`.

## 2. Backend

| File | Change |
|------|--------|
| `backend/app/diagrams/canvas_patch.py` (new) | Pure engine: `MAX_OPERATIONS`, `ElementRef(name, set_id)`, `PatchContext(set_id, elements, relationships)`, `PatchOutcome(data, results)`, `CanvasPatchError(message, op_index=, op=)`, `referenced_ids(data, operations) -> (element_ids, relationship_ids)` (entityIds set by `add_node`/`update_node`; all canvas entityIds only if a `sync_labels` op is present; relationshipIds set by `add_edge`/`update_edge`), `apply_operations(data, operations, ctx) -> PatchOutcome` (deep copy; never mutates input). |
| `backend/app/diagrams/service.py` | `DiagramNotFoundError`, `DiagramVersionConflictError(current_version, expected_version)`, `patch_diagram(db, id, *, operations, change_summary, updated_by, expected_version=None)`: one positional-read query for version, set, name, description, data, metadata → `referenced_ids` → `get_element_names_and_sets` + `get_relationship_endpoints` → `apply_operations` → `update_diagram(expected_version=<read version>, name/description/metadata unchanged)`. Without `expected_version`, a lost compare-and-swap re-reads and re-applies (3 attempts), then 409. `update_diagram`: `UPDATE diagrams … WHERE id = ? AND current_version = ?`; `rowcount == 0` → `None` before any other write. |
| `backend/app/diagrams/models.py` | `DiagramPatch` (`operations` 1–`MAX_OPERATIONS` objects, `change_summary`), `DiagramPatchResponse`. |
| `backend/app/diagrams/router.py` | `PATCH /{diagram_id}`; shared `_if_match_version(request, required=, missing_detail=)` now also used by `PUT`, `DELETE` and rollback (unchanged responses). |
| `backend/app/elements/service.py` | `get_element_names_and_sets(db, ids) -> {id: (name, set_id)}` for live elements, one query per chunk. `get_elements_by_ids` uses the shared chunk size. |
| `backend/app/relationships/service.py` | `get_relationship_endpoints(db, ids) -> {id: (source, target)}` for live relationships, one query per chunk. |
| `backend/app/common/id_chunks.py` (new) | `ID_CHUNK_SIZE = 400`, `id_chunks(ids, size=ID_CHUNK_SIZE)` (distinct, non-empty, first-seen order). `elements.service._ID_CHUNK_SIZE` defaults to it (still monkeypatchable by the ADR-248 tests). |
| `backend/app/main.py` | CORS `allow_methods` includes `PATCH`. |
| `backend/app/seed/creation_prompts.py` | WORKFLOW GUIDANCE: use `patch_diagram` (with `expected_version`) for small edits; `sync_labels`; relationship edges via `add_edge`. |

## 3. Client, MCP, CLI, parity

| File | Change |
|------|--------|
| `iris-client/src/iris_client/client.py` | `patch_diagram(diagram_id, operations, *, expected_version=None, change_summary=None)` → dict; `If-Match` only when `expected_version` is given. |
| `iris-client/src/iris_client/exceptions.py` | `_extract_detail`: an object `detail` with a string `message` yields that message. |
| `mcp/src/iris_mcp/tools.py` | Tool `patch_diagram` (`diagram_id`, `operations` 1–200 with `op` enum, `expected_version` integer, `change_summary`); 409/422 with an object detail → `{"success": false, **detail}`; 401/403 → `auth_required`; success → `with_web_url(..., "diagram")`. `update_diagram` description warns it replaces the whole canvas and points at `patch_diagram`; `create_relationships` mentions the `add_edge` route. |
| `mcp/src/iris_mcp/server_instructions.py` | Fallback mirrors the seed WORKFLOW GUIDANCE. |
| `cli/src/iris_cli/main.py` | `patch_app` (`iris patch`) with `iris patch diagram <id> --from-json FILE|- [--expected-version N] [--change-summary S]`; payload `{"operations": [...]}`; HTTP errors exit 1 with the message. |
| `scripts/check_surface_parity.py` | `@router.patch` (not `/parent`) → verb `patch`; MCP `patch_<entity>` and CLI `@patch_app.command(...)` recognised. |

## 4. Tests (TDD)

Written first and seen failing (import errors for the missing engine,
service and client method; missing MCP tool and CLI command; parity checker
still mapping PATCH to `update`), then green:

- `backend/tests/test_diagrams/test_canvas_patch.py` — the engine: input
  never mutated (also on failure); error names index/op; unknown/malformed
  ops; 0 / 201 / 200 op bounds; in-order application; other canvas keys
  kept; empty canvas; non-canvas data rejected; every op's success and
  rejection cases (duplicate ids, other-set and deleted elements, position
  and parent checks, flat shapes normalised, partial position, `null`
  deletes, unknown fields, relinking validated, cascade vs. no cascade,
  nested children, relationship either-direction / mismatch / unknown /
  unlinked node, endpoints immutable); `sync_labels` changes labels only,
  honours `node_ids`, skips deleted elements; `referenced_ids`; malformed
  flat nodes and id-less legacy nodes don't crash.
- `backend/tests/test_diagrams/test_patch_diagram.py` — through the route:
  patch vs. equivalent full `PUT` store equal `data` and equal side effects
  (relationships, description, metadata, detected notations); reversed
  `relationshipId` edge creates no duplicate; response shape, one version
  per patch, `change_summary` stored; failing op → 422 with index and
  nothing written (versions, data, relationships); non-canvas diagram → 422;
  `If-Match` mismatch → 409 with `current_version`, nothing written; match
  applies; bad `If-Match` → 400; `update_diagram` compare-and-swap loses to
  an interleaved write; patch without `expected_version` retries onto the
  interleaved write; with it, no retry (conflict); other-set element
  rejected and not moved; deleted element rejected; relationship mismatch;
  op-count limits; 404; 401; `sync_labels` after a rename leaves everything
  else byte-identical; scoped user 403 outside scope, 200 inside; seed
  instructions mention `patch_diagram`.
- `backend/tests/test_scripts/test_surface_parity.py` — PATCH → `patch`;
  `("patch", "diagram")` on all three surfaces; no hard violations.
- `iris-client/tests/test_patch_diagram.py`, `mcp/tests/test_patch_diagram_tool.py`,
  `cli/tests/test_patch_diagram.py` — request shape, `If-Match` only with
  an expected version, structured 409/422, auth handling, `web_url`,
  schema, descriptions, fallback instructions.
- `cli/tests/test_integration_smoke.py::TestPatchDiagramEndToEnd` — MCP
  `patch_diagram` against a real backend: add node + reversed relationship
  edge + `sync_labels` in one version, no duplicate relationship, failing
  op writes nothing, stale `expected_version` → `version_conflict`.
