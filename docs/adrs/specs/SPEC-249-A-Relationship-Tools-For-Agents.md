# SPEC-249-A: Relationship Create / Update / List / Delete for MCP and CLI Agents

Implements **[ADR-249](../ADR-249-Relationship-Tools-For-Agents.md)** (issue #298).
Extends [SPEC-003-A](./SPEC-003-A-Entity-Domain-Model.md) (relationship CRUD) and
follows the batch pattern of ADR-200.

## 1. Role-name convention

| Tool / API field | Stored at | Written today by |
|------------------|-----------|------------------|
| `source_role` | `relationship.data.sourceRole` | Sparx importer (`import_sparx/service.py`), canvas edge `data.sourceRole` |
| `target_role` | `relationship.data.targetRole` | same |

`app.relationships.service.apply_role_fields(data, source_role=, target_role=)`
returns a copy of `data`: `None` leaves the key as sent, `""` removes it, any
other string sets it (an explicit role wins over a stale `data` key). Every
relationship response carries derived `source_role` / `target_role` (string
or `null`) read back from `data`.

## 2. Backend

| File | Change |
|------|--------|
| `backend/app/relationships/service.py` | `SOURCE_ROLE_KEY` / `TARGET_ROLE_KEY`; `apply_role_fields`; `RelationshipValidationError(ValueError)`; `validate_new_relationship(db, source_element_id=, target_element_id=)` — raises for source = target ("self-referencing relationships are not allowed"), a missing or deleted endpoint ("source/target element X not found"), or different `set_id`s ("cross-set relationships are not allowed: …"). Not called by `create_relationship`. Get/list share one `_SELECT_RELATIONSHIP` + `_row_to_relationship` (positional reads). `list_relationships(..., set_id=, relationship_type=)`: `set_id` matches when the source OR target element is in the set (`IN (SELECT id FROM elements WHERE set_id = ?)`); ordering `updated_at DESC, id`. `update_relationship(..., relationship_type=None)`: updates `relationships.relationship_type`; when it changes and no `change_summary` is given, the new version's summary is `relationship_type: <old> -> <new>`. |
| `backend/app/relationships/models.py` | `RelationshipUpdate` gains `relationship_type: str \| None` (`min_length=1`), `source_role`, `target_role`. `RelationshipResponse` gains `source_role`, `target_role`. |
| `backend/app/relationships/router.py` | `GET /api/relationships` accepts `set_id`, `relationship_type`. `PUT` passes `relationship_type` and `apply_role_fields(body.data, …)`. |
| `backend/app/batch/models.py` | `BatchRelationshipCreateItem` (all fields optional at the model so bad rows fail per item) and `BatchRelationshipsCreate` (`relationships`, 1–100). |
| `backend/app/batch/service.py` | `batch_create_relationships(db, items, user=)`: per item → required fields → `validate_new_relationship` → `assert_write_allowed(collection_of_element(source))` (403 detail becomes the item error) → `create_relationship(data=apply_role_fields(...))`. Errors are `"Relationship at index <i>: <reason>"`. |
| `backend/app/batch/router.py` | `POST /api/batch/relationships/create` → `BatchResultWithIds`. |
| `backend/app/seed/creation_prompts.py` | MCP server instructions WORKFLOW GUIDANCE names the relationship tools and the `data.relationshipId` edge reuse; AUTH RECOVERY says `list_relationships` / `get_relationship` need sign-in. |
| `backend/app/diagrams/service.py` | Edge auto-create: before the source/target dedup, an edge whose `data.relationshipId` names a non-deleted relationship whose `{source_element_id, target_element_id}` equals the edge's two element ids (either direction) is skipped. A `relationshipId` for other elements is ignored. |

Unchanged on purpose: `create_relationship` (canvas, importers, diagram-edge
auto-create, AI creation) and `POST /api/relationships` — reflexive and
cross-set relationships remain possible there.

## 3. Shared client, MCP, CLI

| File | Change |
|------|--------|
| `iris-client/src/iris_client/client.py` | `create_relationships(items)`, `list_relationships(element_id=, set_id=, relationship_type=, page=, page_size=)` (returns the envelope), `get_relationship(id)`, `update_relationship(id, relationship_type=, source_role=, target_role=, label=, description=, data=, change_summary=)` (GET → merge → PUT with `If-Match: current_version`; `data` replaces stored data except `sourceRole` / `targetRole`, which carry over unless a role is passed), `delete_relationship(id)` (GET version → DELETE with `If-Match`). |
| `mcp/src/iris_mcp/tools.py` | Tools `create_relationships` (typed item schema, `minItems` 1 / `maxItems` 100), `update_relationship`, `list_relationships` (requires `element_id` or `set_id`; otherwise returns `{"success": false, "error": "missing_scope"}`), `get_relationship`, `delete_relationship`. Auth errors return the shared `auth_required` payload; other HTTP errors surface via `dispatch` as `ERROR: HTTP <status>: <detail>`. |
| `mcp/src/iris_mcp/server_instructions.py` | Fallback body mirrors the seed change. |
| Tool descriptions | `create_relationships` states the edge direction (source node = `source_element_id`); `list_relationships` / `get_relationship` state they need sign-in (the REST reads use `get_current_user`). |
| `cli/src/iris_cli/main.py` | `iris relationships list|get`; `iris create relationship` (one-item batch; exits 1 with the item error when rejected); `iris create relationships --from-json`; `iris update relationship`; `iris delete relationship`. |
| `scripts/check_surface_parity.py` | `relationship` ∈ `_KNOWN_ENTITIES`; `_normalise_entity` maps plural names; `_batch_route_op` attributes `POST /<entities>/{create,update,delete}` on the batch router (clone/set/tags ignored). |

## 4. Tests (TDD)

Written first and seen failing (404 on the batch route; missing client
methods / tools / commands; parity checker attributes), then green:

- `backend/tests/test_relationships/test_agent_relationship_surface.py` —
  batch create + ids; roles → `data.sourceRole/targetRole`; explicit role
  beats `data`; self-reference, cross-set, missing and deleted endpoints and
  missing fields fail per item without sinking the batch; >100 and empty →
  422; 401 without auth; UI-created and batch-created list with identical
  shape; scoped user gets a per-item write-scope error outside scope;
  `relationship_type` update, auto change summary, omit keeps, `""` → 422;
  role fields merge / clear on PUT; `set_id`, `relationship_type`,
  either-direction `element_id`, pagination; items carry roles, `data` and
  element names; edge `relationshipId` reuse creates no duplicate, including
  on an edge drawn target → source, while a `relationshipId` for other
  elements doesn't suppress the create; the single
  POST still accepts a reflexive relationship; seed instructions mention the
  tools and that relationship reads need sign-in.
- `backend/tests/test_scripts/test_surface_parity.py` — known entity, batch
  route attribution, plural normalisation, and relationship
  create/update/delete present on backend, MCP and CLI with no hard
  violations.
- `iris-client/tests/test_relationships.py`, `mcp/tests/test_relationship_tools.py`,
  `cli/tests/test_relationships.py` — request shapes, `If-Match`, partial
  merge, role carry-over, 409 / 401 handling, output.
- `cli/tests/test_integration_smoke.py::TestRelationshipToolsEndToEnd` — the
  MCP tools against a real backend: batch create with self/cross-set
  rejections, list by element and set, partial update, `update_diagram` edge
  reuse without duplicates, delete.

## 5. Acceptance criteria (issue #298)

- Relationships created via MCP are stored like UI/import-created ones
  (same table and `data` keys; counts, Relationships tab and queries match).
- Returned ids work as `relationshipId` in `update_diagram` edges with no
  duplicate relationship.
- Cross-set and self-referencing relationships are rejected with a clear
  per-item error on the agent path.
- `list_relationships` returns roles and `data` for each relationship.
- Batch create reports per-item errors without failing the batch.
- `scripts/check_surface_parity.py` is clean with relationships enforced.
