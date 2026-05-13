# ADR-175: Decorate create_* tool responses with `web_url`

Status: Accepted (2026-05-13)
Extends: [ADR-126](ADR-126-Web-URL-Link-Decoration.md) (the v5.6.1 entity-link-decoration design), [ADR-161](ADR-161-MCP-Entity-Creation-and-Destination-Flow.md)

## Context

`iris-mcp`'s read tools (`get_set`, `get_collection`, `get_diagram`, `list_*`, `search`, `package_hierarchy`) all decorate their responses with a `web_url` field that resolves the entity to a clickable URL on the iris frontend. The decoration is centralised in `mcp/src/iris_mcp/links.py` (`with_web_url` / `with_web_urls_list` / `with_web_urls_search` / `with_web_urls_tree`) and triggered when `IRIS_WEB_URL` is configured.

The **create_*** tools — `create_collection`, `create_set`, `create_package`, `create_diagram` — return the new entity's full dict from iris-api but **skip the decoration**. The model gets back an id and a name but no link.

User-visible failure during v6.0.14 end-of-issue-#119 testing:

> User: `make a new set in iris called 'claude test'`
> Claude: *creates the set, returns the id*
> User: `link me to it`
> Claude: `https://iris.chrisbarlow.nz/sets/df7aa9df-…` ← **wrong host** (should be `iris-uat.chrisbarlow.nz`)

The model had to guess the host (and got the subdomain wrong). The right answer was already known to iris-mcp via the `IRIS_WEB_URL` env var — the create_* handlers just weren't using it.

## Decision

Wrap each create_* handler's return value with `with_web_url(json, kind)` so the response shape matches the corresponding `get_*` tool. Four handlers in `mcp/src/iris_mcp/tools.py`:

```python
# Before:
return result.model_dump_json()

# After:
return with_web_url(result.model_dump_json(), "<kind>")
```

| Handler | `<kind>` |
|---|---|
| `_create_collection` | `"collection"` |
| `_create_set` | `"set"` |
| `_create_package` | `"package"` |
| `_create_diagram` | `"diagram"` |

`with_web_url` already does the right thing for write-tool responses: it adds `web_url` when `IRIS_WEB_URL` is set, strips `system_prompt` per ADR-151 (sensitive-key strip), and is a no-op when the entity has no `id` or the env var is unset. It also runs `wrap_orient` — a no-op on freshly-created entities because they have no `mcp_system_context` content yet, but the safety still applies.

`apply_diagram_creation` is **not** changed in this ADR. Its response shape is a batched `{diagram_ids: [...], primary_diagram_id: ...}` of bare id strings, not entity dicts — decoration would need a different shape (e.g. `{diagram_ids: [...], web_urls: [...]}`) and a per-entity batch helper. Out of scope; defer to a follow-up.

## Why not also resolve `iris://` deep-links in the response

Considered: turn the entity's `iris://` URI (used inside markdown bodies) into a frontend URL in the response. Rejected as a separate concern — `iris://` is for the markdown rendering path and the existing `with_web_url` covers the explicit `web_url` field, which is what the model uses to link.

## Consequences

- 4 one-line changes to `tools.py` (`_create_collection`, `_create_set`, `_create_package`, `_create_diagram` now wrap their returns).
- 5 new regression tests in `tests/test_create_tools_web_url_decoration.py`:
  - Each create_* tool's response includes a correctly-shaped `web_url`.
  - When `IRIS_WEB_URL` is unset (dev), responses pass through unchanged (no `web_url` key) — behaviour parity with the read tools.
- The existing 19 `test_tools_create.py` cases stay green — they don't assert on `web_url` absence, so adding it doesn't break them.
- Version bump v6.0.14 → v6.0.15. Patch-level — UX fix, no API surface change.

## Verification

- After deploy, `create_set` from claude.ai → response includes `web_url`. The model surfaces the real frontend URL when the user asks "link me to it"; no more host-guessing.
- 173/173 MCP tests pass.

## See also

- [ADR-126](ADR-126-Web-URL-Link-Decoration.md) — v5.6.1 origin of the link-decoration pattern.
- [ADR-161](ADR-161-MCP-Entity-Creation-and-Destination-Flow.md) — the v5.16.0 introduction of these create_* tools.
- [ADR-167](ADR-167-Orient-Directive-In-Tool-Response.md) — the v6.0.6/7 orient wrapper that piggybacks on the same `with_web_url` helper.
- [SPEC-175-A](specs/SPEC-175-A-Web-URL-Decoration-On-Create-Tools.md).
