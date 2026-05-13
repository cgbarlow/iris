# SPEC-175-A: Decorate create_* tool responses with `web_url`

ADR: [ADR-175](../ADR-175-Web-URL-Decoration-On-Create-Tools.md)

## Summary

Wrap each create_* MCP handler's return value with `links.with_web_url(json, kind)` so the response shape matches the corresponding `get_*` tool — `web_url` populated when `IRIS_WEB_URL` is set, absent otherwise.

## MCP changes

### `mcp/src/iris_mcp/tools.py`

Four one-line wrappers:

```python
async def _create_collection(c, args):
    try:
        result = await c.create_collection(...)
    except IrisAuthError:
        return _auth_required_payload("Create collection")
    return with_web_url(result.model_dump_json(), "collection")

async def _create_set(c, args):
    try:
        result = await c.create_set(...)
    except IrisAuthError:
        return _auth_required_payload("Create set")
    return with_web_url(result.model_dump_json(), "set")

async def _create_package(c, args):
    try:
        result = await c.create_package(...)
    except IrisAuthError:
        return _auth_required_payload("Create package")
    return with_web_url(result.model_dump_json(), "package")

async def _create_diagram(c, args):
    try:
        diagram = await c.create_diagram(...)
    except IrisAuthError:
        return _auth_required_payload("Create diagram")
    return with_web_url(diagram.model_dump_json(), "diagram")
```

`with_web_url` is already imported at the top of `tools.py`; no new imports needed.

### Behaviour map (`with_web_url(payload, kind)` recap)

- Parses payload as JSON; no-op on parse failure.
- Strips `system_prompt` per ADR-151 (sensitive-key strip).
- Runs `wrap_orient(item, kind)` — no-op on freshly-created entities (no `mcp_system_context`).
- If `IRIS_WEB_URL` is set and `kind` is in the known-kinds map, adds `web_url` = `<IRIS_WEB_URL>/<path>/<id>`.
- Returns JSON string.

### Out of scope

`apply_diagram_creation` returns `{diagram_ids: [str], primary_diagram_id: str}` — bare id strings, not entity dicts. Decoration would need a separate shape (e.g. `web_urls: list[str]`) and a per-entity batch helper. Defer to follow-up.

## Tests

### `mcp/tests/test_create_tools_web_url_decoration.py` (new)

5 cases, each using `respx` to mock the iris-api response and `tools.dispatch` to exercise the full handler chain:

1. `TestCreateCollectionWebUrl::test_response_includes_web_url` — response body has `web_url == "https://iris-uat.chrisbarlow.nz/collections/<id>"`.
2. `TestCreateSetWebUrl::test_response_includes_web_url` — same for sets; explicit assert that `chrisbarlow.nz` is in the URL (regression on the host-guessing bug).
3. `TestCreatePackageWebUrl::test_response_includes_web_url` — same for packages.
4. `TestCreateDiagramWebUrl::test_response_includes_web_url` — same for diagrams; URL uses the `views` path.
5. `TestNoIrisWebUrlNoDecoration::test_create_set_without_iris_web_url` — when `IRIS_WEB_URL` is unset, response has no `web_url` key; other fields unchanged.

The Package test fixture must include `current_version` (required by the Pydantic Package model).

### Existing tests

`test_tools_create.py` (19 cases) and `test_tools_create_diagram.py` stay green — they don't assert on `web_url` absence, so adding it doesn't break them.

## Versioning

`mcp/pyproject.toml`: 6.0.14 → 6.0.15. Patch — UX fix, no API surface change. `frontend/package.json` matched.

## Acceptance criteria

- [ ] After deploy, claude.ai → `create_set` → response includes `web_url`. The model uses it when the user asks "link me to it" instead of host-guessing.
- [ ] All four create_* tools have `web_url` in the response when `IRIS_WEB_URL` is set.
- [ ] No regression on the existing create_* tool tests.
- [ ] 173/173 MCP tests pass.
