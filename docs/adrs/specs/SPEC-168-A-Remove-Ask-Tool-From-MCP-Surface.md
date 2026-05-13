# SPEC-168-A: Remove the `ask` tool from the MCP surface

ADR: [ADR-168](../ADR-168-Remove-Ask-Tool-From-MCP-Surface.md)

## Summary

Drop the `ask` MCP tool definition and dispatch handler from iris-mcp. Keep `iris_client.IrisClient.ask(...)` intact (used outside MCP). Strengthen the orient wrapper in `links.py` to steer the model to do analysis + cross-scope question-answering itself via the read-only MCP tools, rather than looking for a delegated AI tool. Update the canonical paste-doc for the Outcomes Theory Book menu to drop the obsolete `mcp__iris__ask` reference and the `→ call create_diagram` implementation tag.

## MCP changes

### `mcp/src/iris_mcp/tools.py`

Remove the `Tool(name="ask", ...)` entry from `tool_definitions()` (the v6.0.0 entry that exposed `c.ask(...)`). Remove the `_ask(c, args)` handler function. Replace the deleted block with a comment explaining the removal so future readers don't reintroduce it.

Rewrite the description of the adjacent `apply_diagram_creation` tool — the v6.0.0 wording referenced "Use after calling `ask` with mode='creation'". The new description reflects the local-AI-as-author model:

> "Apply a local-AI-generated diagram bundle to a set. The client drafts the diagrams JSON (one entry per diagram, matching the creation_format cascade returned by `get_response_prompt(purpose='creation_format', notation=..., diagram_type=...)`) and posts it here for persistence. Prefer `create_diagram` for single-diagram creation; this tool is for batch saves."

### `mcp/src/iris_mcp/links.py`

Append two paragraphs to the orient-wrapper text inside `_orient_wrapper`, after the existing "step 3" menu-verbatim guidance:

1. "Cross-package, cross-set, or cross-collection questions are answered by YOUR reasoning over data you read via the read-only MCP tools (search, get_diagram, get_element, get_package, get_set, get_collection, list_*, package_hierarchy). There is no 'ask Iris AI' tool — it has been removed (v6.0.8). Walk the data yourself."
2. "DoView outcomes-theory analyses and visual outcomes_map diagrams are drafted by YOU using your own reasoning, following the creation cascade from `get_response_prompt(purpose='creation_format', notation=..., diagram_type=...)`. Persist the result by calling `create_diagram` (single) or `apply_diagram_creation` (batch). Do NOT look for a separate AI-analysis tool — none exists."

### `docs/prompts/doview-book-mcp-system-context.md`

Update the paste-ready menu:

| Before (v6.0.7) | After (v6.0.8) |
|---|---|
| Option 2: "Ask a cross-package question via Iris AI (e.g. ... — uses mcp__iris__ask)." | Option 2: "Ask a cross-package, cross-set, or cross-collection question about the material (e.g. ...)." |
| Option 3: "Generate ... outcomes_map → call create_diagram." | Option 3: "Generate a new DoView outcomes-theory analysis or a new visual DoView outcomes_map." |

Add a "v6.0.8 menu changes (paste required)" subsection explaining that admins must re-paste from the doc into the set's `mcp_system_context` field. TTL refresh (v6.0.5) propagates to claude.ai within 60 s.

## Tests

### `mcp/tests/test_tools.py`

Replace the v5.x `TestAsk` class with `TestAskRemoved` (2 cases):

```python
class TestAskRemoved:
    def test_ask_not_in_tool_definitions(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert "ask" not in names

    async def test_ask_dispatch_returns_unknown_tool_error(
        self, client: IrisClient,
    ) -> None:
        result = await tools.dispatch("ask", client, {"question": "?"})
        assert result[0].text.startswith("ERROR: unknown tool")
```

### `mcp/tests/test_links_orient_wrapper.py`

Update the existing `test_wrapper_demands_character_by_character_menu_copy` to assert `mcp__iris__ask` is **not** in the wrapper text. Add `test_wrapper_steers_analysis_to_local_ai` asserting "YOU do the work, not a separate AI", "drafted by YOU using your own reasoning", "creation_format", and "Do NOT look for a separate AI-analysis tool".

## Versioning

`mcp/pyproject.toml`: 6.0.7 → 6.0.8. Patch — tool surface shrinks but every previous caller of `ask` is steered to a working substitute (local reasoning + read-only tools). `frontend/package.json` matched.

## Acceptance criteria

- [ ] `ask` is not in `tools.tool_definitions()`. Dispatching to `"ask"` returns the standard unknown-tool error.
- [ ] `apply_diagram_creation` description no longer references `ask`.
- [ ] Orient wrapper output contains the two new "YOU do the work" paragraphs.
- [ ] Canonical `doview-book-mcp-system-context.md` reflects the v6.0.8 menu wording.
- [ ] 163/163 MCP tests pass.
- [ ] After deploy + admin paste: claude.ai → open the Outcomes Theory Book → menu reads the new wording, no `mcp__iris__ask` / `→ call create_diagram`. Pick option 3 ("Generate analysis") — local model drafts the analysis itself, never calls a separate AI tool.
