# SPEC-167-A: Embed the orient directive in MCP tool responses

ADR: [ADR-167](../ADR-167-Orient-Directive-In-Tool-Response.md)

## Summary

Prepend a hardcoded imperative orient directive to `mcp_system_context` on every set / collection in any iris-mcp tool response. Pre-fill the scope's id in the directive's tool-call signature so the model has the exact `package_hierarchy(set_id="...")` call ready.

## MCP changes

### `mcp/src/iris_mcp/links.py`

Add a marker constant, a wrapper-builder, and an in-place primitive:

```python
_ORIENT_MARKER = "[ORIENT — DO THESE STEPS BEFORE RESPONDING TO THE USER]"

def _orient_wrapper(kind: str, entity_id: str) -> str:
    """Build the imperative prefix. set_id / collection_id pre-filled."""
    if kind == "set":
        id_kw = f'set_id="{entity_id}"'
    elif kind == "collection":
        id_kw = f'collection_id="{entity_id}"'
    else:
        id_kw = f'id="{entity_id}"'
    return (
        f"{_ORIENT_MARKER}\n"
        f"This scope is a {kind} ({id_kw}). The orient sheet below names a "
        f"structural-overview call AND a numbered menu. Before responding "
        f"to the user, you MUST, in order:\n"
        f"  1. Briefly describe the scope (one sentence based on its name "
        f"and description).\n"
        f"  2. INVOKE the structural-overview call named below, passing "
        f"this scope's {id_kw}. The TOC is mandatory, not optional. If the "
        f"named tool is not currently in your toolset, request a tool-load "
        f"first — do NOT skip this step.\n"
        f"  3. Offer the menu options below via AskUserQuestion (if your "
        f"client supports it) or a numbered list, IN ORDER, VERBATIM. "
        f"Do not paraphrase, do not silently drop options.\n"
        f"\n"
        f"Do NOT ask \"want me to load the table of contents?\" — load it "
        f"yourself. Do NOT respond with just the menu and skip the TOC.\n"
        f"\n"
        f"---\n"
        f"\n"
    )

def wrap_orient(item: Any, kind: str) -> None:
    """In-place: prepend orient directive to `item["mcp_system_context"]`
    when the field is set on a set or collection. Idempotent via the
    marker check. No-op on other kinds, missing/empty fields, missing
    ids."""
    if not isinstance(item, dict):
        return
    if kind not in ("set", "collection"):
        return
    ctx = item.get("mcp_system_context")
    if not isinstance(ctx, str) or not ctx.strip():
        return
    if ctx.startswith(_ORIENT_MARKER):
        return  # already wrapped
    entity_id = item.get("id")
    if not isinstance(entity_id, str) or not entity_id:
        return
    item["mcp_system_context"] = _orient_wrapper(kind, entity_id) + ctx
```

### Injection points

Three public surfaces all call `wrap_orient` once per scope-shaped item, **regardless of `IRIS_WEB_URL`** (the wrapper is universal, the web-URL decoration is env-gated):

- `with_web_url(payload, kind)` — single-entity tool response (get_set, get_collection). Calls `wrap_orient(data, kind)` after stripping sensitive keys.
- `with_web_urls_list(payload, kind)` — homogeneous-list tool response (list_sets, list_collections). Iterates the list and calls `wrap_orient(item, kind)` on each.
- `with_web_urls_search(payload)` — search response with heterogeneous result types. For each result with a string `result_type`, call `wrap_orient(r, result_type)`. Diagrams / elements / packages are passed through cleanly because `wrap_orient` no-ops on non-scope kinds.

## Tests

### `mcp/tests/test_links_orient_wrapper.py` (new)

18 cases across five classes:

- `TestWrapOrient` — primitive behaviour: wraps set; wraps collection; no-op on missing field; no-op on empty; no-op on whitespace; idempotent; no-op when id missing.
- `TestSearchResponseWrap` — search response wraps set result; wraps collection result; skips diagram result; skips results without mcp_system_context.
- `TestListResponseWrap` — list response wraps each entry; skips entries without the field.
- `TestSingleEntityWrap` — `with_web_url` wraps a set and a collection.
- `TestWrapperHappensEvenWithoutIrisWebUrl` — wrapper applies when IRIS_WEB_URL is unset.

### `mcp/tests/test_links_passes_mcp_system_context.py` (updated)

The existing v5.11.0 / ADR-156 contract ("`mcp_system_context` survives the links boundary") evolves: the wrapped body must still END with the original admin-authored content. Four cases updated from `assert ctx == "original"` to `assert ctx.startswith(_MARKER) and ctx.endswith("original")`.

## Versioning

`mcp/pyproject.toml`: 6.0.5 → 6.0.6. Patch bump — operator-experience fix for claude.ai compatibility.
`frontend/package.json`: matched 6.0.6.

## CHANGELOG

Add a `[6.0.6]` entry explaining: claude.ai does not surface `Server.instructions` reliably, the orient directive is therefore re-embedded into tool responses where the model definitely reads it, with the scope id pre-filled for an unambiguous tool call.

## Acceptance criteria

- [ ] `wrap_orient(item, "set")` prepends the marker + `set_id="..."` directive to a set with non-empty `mcp_system_context`.
- [ ] Original `mcp_system_context` body is preserved at the tail of the wrapped string.
- [ ] `wrap_orient` is idempotent — running it twice yields the same result.
- [ ] `wrap_orient` no-ops on non-scope kinds, missing/empty fields, or missing ids.
- [ ] Wrapper applies in `with_web_url`, `with_web_urls_list`, and `with_web_urls_search`.
- [ ] Wrapper applies regardless of `IRIS_WEB_URL`.
- [ ] All existing v5.11.0 / ADR-156 / v6.0.5 tests pass after assertion update.
- [ ] Manual smoke after deploy: claude.ai → fresh chat → "open the outcomes theory book" → TOC auto-loads, four-option `AskUserQuestion` widget appears.
