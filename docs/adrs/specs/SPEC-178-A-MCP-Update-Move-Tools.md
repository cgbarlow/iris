# SPEC-178-A: MCP `update_*` and `move_*` tool surface

ADR: [ADR-178](../ADR-178-MCP-Update-Move-Tools.md)

## Summary

Add eight new MCP tools wrapping existing backend PUT endpoints. Five update tools for metadata mutation, three move tools for in-scope re-parenting. Drop the cross-set move fallback from the cascade destination chooser prompt.

## Tool signatures

### Update tools

```python
update_collection(collection_id: str,
                  name: str | None = None,
                  description: str | None = None,
                  system_prompt: str | None = None,
                  mcp_system_context: str | None = None,
                  thumbnail_source: str | None = None,
                  thumbnail_diagram_id: str | None = None)
  → backend PUT /api/collections/{collection_id}

update_set(set_id: str,
           name: str | None = None,
           description: str | None = None,
           system_prompt: str | None = None,
           mcp_system_context: str | None = None,
           thumbnail_source: str | None = None,
           thumbnail_diagram_id: str | None = None)
  → backend PUT /api/sets/{set_id}
  Note: collection_id intentionally NOT in this tool — moves are via move_set.

update_package(package_id: str,
               name: str | None = None,
               description: str | None = None,
               metadata: dict | None = None)
  → backend PUT /api/packages/{package_id}

update_diagram(diagram_id: str,
               name: str | None = None,
               description: str | None = None,
               data: dict | None = None,
               metadata: dict | None = None,
               change_summary: str | None = None)
  → backend PUT /api/diagrams/{diagram_id}
  Versioned — every successful update increments current_version.

update_element(element_id: str,
               name: str | None = None,
               description: str | None = None,
               data: dict | None = None)
  → backend PUT /api/elements/{element_id}
```

All five return the updated entity dict decorated with `web_url` via `with_web_url`.

### Move tools

```python
move_diagram(diagram_id: str,
             parent_package_id: str | None)
  → backend PUT /api/diagrams/{diagram_id}/parent
    body: {"parent_package_id": parent_package_id or None}
  parent_package_id=null → moves diagram to the root of its current set.

move_package(package_id: str,
             parent_package_id: str | None)
  → backend PUT /api/packages/{package_id}/parent
    body: {"parent_package_id": parent_package_id or None}
  Backend cycle-checks.

move_set(set_id: str,
         collection_id: str | None)
  → backend PUT /api/sets/{set_id}
    body: {"collection_id": collection_id}
  collection_id=null → un-groups the set.
```

All three return the updated entity dict (a "result" envelope for the /parent endpoints; the full SetResponse for move_set) decorated with `web_url`.

## Error handling

All eight tools:
- Wrap `IrisAuthError` → `_auth_required_payload(action)` matching the existing `create_*` pattern.
- Pass through 4xx errors as JSON in the response payload (backend's existing detail field).

## Cascade prompt update

Migration `m062_drop_phase1_move_fallback.py` + Supabase mirror UPDATE `creation-cascade-destination-v1` to drop the cross-set move fallback. Replacement guidance:

```
- When the user picks "Somewhere else" or "Browse" at Q-Dest2 and the
  chosen destination differs from the current set: if the destination
  is an *existing* set, save into the current set and then call
  `move_diagram` / `move_package` to relocate; if the destination is
  a *new* set under a different collection, call `create_set` first
  (in the target collection) and then save the bundle into the
  newly-created set directly.
```

The seed file's `CASCADE_DESTINATION_PROMPT` constant is updated in lockstep.

## Tests

### `mcp/tests/test_update_tools.py` (new)

- `test_inventory` — all 5 update tools registered.
- `test_update_collection_happy` — respx-mock PUT, dispatch, assert response has expected fields + web_url.
- `test_update_set_happy` + `test_update_set_excludes_collection_id` (collection_id field should NOT be in the input schema — it's a move concern).
- `test_update_package_happy`.
- `test_update_diagram_happy` (with both name and data).
- `test_update_element_happy`.
- `test_401_returns_auth_required_payload` (parametrised across all 5).

### `mcp/tests/test_move_tools.py` (new)

- `test_inventory` — 3 move tools registered.
- `test_move_diagram_happy` — respx-mock PUT /api/diagrams/{id}/parent.
- `test_move_diagram_to_root` — `parent_package_id=null` sends null in body.
- `test_move_package_happy`.
- `test_move_package_to_root`.
- `test_move_set_happy` — PUT /api/sets/{id} with collection_id.
- `test_move_set_uncollect` — `collection_id=null`.
- `test_401_returns_auth_required_payload` (parametrised across all 3).

### `backend/tests/test_migrations/test_phase3_move_actuation_schema.py` (new)

- Migration m062 file exists, registered in startup, REPLACEs the Phase-1 move fallback.
- Supabase m066 mirror has same REPLACE.
- Seed file no longer contains the old move-fallback string but contains the new move-tool guidance.
- Canonical doc `creation-cascade-destination.md` aligned.

## Versioning

`mcp/pyproject.toml`: 6.2.0 → 6.3.0.
`frontend/package.json`: matched 6.3.0.

## CHANGELOG

`[6.3.0]` Added: 5 MCP update tools + 3 MCP move tools. Changed: cascade destination drops the move fallback.

## Acceptance criteria

- [ ] `pytest mcp/tests/test_update_tools.py test_move_tools.py` green.
- [ ] `pytest backend/tests/test_migrations/test_phase3_move_actuation_schema.py` green.
- [ ] Inventory: `tool_definitions()` returns 5 update + 3 move tools.
- [ ] Each tool decorates its response with `web_url`.
- [ ] Each tool maps 401 → `_auth_required_payload`.
- [ ] Manual UAT: cascade saves to wrong set → user asks to move → `move_diagram` succeeds.
