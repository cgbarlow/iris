# SPEC-257-A: MCP Links to Sets and Collections Open the Knowledge Graph

Implements **[ADR-257](../ADR-257-MCP-Scope-Links-Open-Knowledge-Graph.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `mcp/src/iris_mcp/links.py` | `set`/`sets` and `collection`/`collections` moved from `_KIND_TO_PATH` into `_SCOPE_KIND_TO_PARAM`. For these kinds, `web_url_for` returns `<base>/?set_id=<id>` or `<base>/?collection_id=<id>`. |
| `mcp/src/iris_mcp/prompts.py` | `_web_base` and `_scope_web_url` removed. The preamble calls `links.web_url_for`. |

Everything that decorates responses goes through `web_url_for`: get, list,
create and update tools, search results and the prompts preamble. They all
pick up the new link.

## 2. Tests (TDD)

- `mcp/tests/test_links.py::TestWebUrlFor::test_scopes_route_to_knowledge_graph`:
  covers all four kind spellings.
- Updated expectations in `test_links.py`, `test_links_strip_system_prompt.py`,
  `test_create_tools_web_url_decoration.py` and `test_prompts_get.py`.
- MCP suite: 290 passed.

## 3. Acceptance criteria

- Every MCP `web_url` (and the prompt preamble link) for a collection is
  `<IRIS_WEB_URL>/?collection_id=<id>`, and for a set is
  `<IRIS_WEB_URL>/?set_id=<id>`.
