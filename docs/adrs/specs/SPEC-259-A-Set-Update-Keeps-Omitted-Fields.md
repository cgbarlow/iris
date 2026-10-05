# SPEC-259-A: Updating a Set Keeps the Fields the Caller Left Out

Implements **[ADR-259](../ADR-259-Set-Update-Keeps-Omitted-Fields.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `mcp/src/iris_mcp/tools.py` | `_update_set` drops a caller-supplied `collection_id`, then merges with `_SET_UPDATE_FIELDS`, so the current `collection_id` goes back in the PUT body. `_SET_METADATA_FIELDS` removed. Tool description reworded. |
| `cli/src/iris_cli/main.py` | One `_SET_UPDATE_FIELDS` list, shared by `update set` and `move set`. It includes `collection_id` and the three sort and tab-default fields. `_SET_METADATA_FIELDS` removed. |
| `backend/app/sets/router.py` | `PUT /api/sets/{id}` passes only the fields in `body.model_fields_set` for the six keep-when-omitted fields (`_KEEP_WHEN_OMITTED`). |
| `backend/app/sets/service.py` | `update_set` defaults those six parameters to `UNSET`. It reads the current row and keeps the stored value for each `UNSET` parameter. `None` still clears. |
| `backend/app/sets/models.py` | `SetUpdate` docstring states the contract. |

## 2. Field contract for `PUT /api/sets/{id}`

| Field | Key missing | `null` |
|-------|-------------|--------|
| `name` | 422 (required) | 422 |
| `description`, `thumbnail_source`, `thumbnail_diagram_id`, `collection_id`, `system_prompt`, `mcp_system_context` | unchanged | cleared |
| `hierarchy_sort`, `package_tab_default`, `view_tab_default`, `element_tab_default` | unchanged | unchanged (as before) |

The uploaded thumbnail image is cleared when the resulting `thumbnail_source`
is not `image`. With `thumbnail_source` missing, the stored source is used, so
an uploaded image survives a metadata edit.

## 3. Tests (TDD)

- `backend/tests/test_sets/test_crud.py::TestUpdateSetOmittedFields`: a PUT
  without `collection_id` keeps the collection; `null` un-groups; a value
  moves; the same missing-versus-null pairs for description, prompts and
  thumbnail fields, including an uploaded image.
- `mcp/tests/test_update_tools.py::TestUpdateSet`: the PUT body carries the
  current `collection_id`, for a grouped and an ungrouped set, and a
  caller-supplied `collection_id` is ignored.
- `cli/tests/test_write_commands.py`: `update set` sends the current
  `collection_id`, and sends `--hierarchy-sort` / `--view-tab-default`.
- `cli/tests/test_integration_smoke.py::TestSetUpdateEndToEnd`: MCP
  `update_set`, `update_collection` and `move_set` against a real backend, no
  mocked responses.

## 4. Acceptance criteria

- `update_set` with only a name or description never changes `collection_id`.
- `move_set` with `collection_id: null` still un-groups a set.
- Both are covered by a test that runs the real merge against the real
  backend.
