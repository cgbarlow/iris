# DoView Book Set — `mcp_system_context` content

Canonical paste-ready content for the **MCP system context** field on the DoView Book Set (`/sets/33032180-d77a-4ce4-88cf-b49cd643e093`).

This pointer is what an MCP client model (Claude Desktop / Claude Code) sees when it calls `mcp__iris__get_set` on the DoView Book Set. It is intentionally short — it orients the model to the response-format workflow without trying to encode formatting rules in tool data (those live in the layered response_format prompts seeded by SQLite m051 / Supabase m055, fetched at runtime via `iris_get_response_prompt`).

Per ADR-156 (`mcp_system_context` semantics) and ADR-157 (response_format layered prompts).

## Content

Paste the following into the **MCP system context** textarea on the DoView Book Set edit page:

```text
This set hosts Dr Paul Duignan's DoView Planning and Outcomes Theory Handbook.

For formal outcomes-theory analyses, fetch the response format via:
  iris_get_response_prompt(notation='markdown', diagram_type='doview_analysis')

Then compose the response using:
  - mcp__iris__search to find relevant tool pages in this set
  - mcp__iris__get_diagram to retrieve mermaid blocks from data.content

To persist the analysis as a doview_analysis diagram in Iris:
  iris_save_doview_analysis(set_id, name, content)
(requires IRIS_TOKEN on the MCP server.)

Discover what other response formats are available:
  list_response_format_types
```

## Why this content (and not the strict format rules)

- The DoView Book Set is one scope; the response_format rules are universal to any `(notation=markdown, diagram_type=doview_analysis)` conversation regardless of scope. They belong in the layered prompts table (admin-editable, central), not duplicated into per-scope passthrough fields. ADR-157 establishes this split.
- Embedding the strict Prompt-C rules directly in `mcp_system_context` would:
  - Trigger prompt-injection treatment (the client model sees scope tool data as untrusted; long directive content in tool data is treated as informational, not authoritative).
  - Duplicate content that's already in the response_format prompt rows.
  - Make the rules un-editable from a central admin surface.
- The fetch step (`iris_get_response_prompt`) is a deliberate model action — the response_format cascade body arrives as the response to a tool call the model chose to make. That's a stronger trust signal than scope tool data.

## Smoke test after pasting

In a fresh Claude Desktop conversation with Iris MCP connected:

> "Give me an outcomes-theory analysis of siloing program steps in the DoView Book Set."

Expected flow:
1. Claude calls `mcp__iris__get_set` → sees the pointer.
2. Claude calls `mcp__iris__get_response_prompt('markdown', 'doview_analysis')` → fetches the cascade (~300 lines of Prompt C rules).
3. Claude calls `mcp__iris__search` + `mcp__iris__get_diagram` to gather handbook material.
4. Claude composes a three-section formal response (Summary + Full + Diagrams with verbatim mermaid blocks + raw handbook URLs).
5. Claude offers to save via `iris_save_doview_analysis`.

If Claude doesn't reach for `iris_get_response_prompt` reliably, sharpen this content's signal (e.g. lead with "For outcomes-theory questions about this set, **always** call iris_get_response_prompt…"). The current phrasing is intentionally conservative; tighten if real usage shows under-triggering.

## See also

- [ADR-156](../adrs/ADR-156-MCP-System-Context-Data-Passthrough.md) — what `mcp_system_context` is for (per-scope context, data passthrough).
- [ADR-157](../adrs/ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — where the response_format rules live (universal layered prompts, admin-editable).
- [SPEC-157-A](../adrs/specs/SPEC-157-A-Response-Format-Prompts.md) — schema and endpoint shapes for the response_format mechanism.
- [`doview-book-prompt-c-iris.md`](./doview-book-prompt-c-iris.md) — the source content from which the seeded response_format prompts (`response-format-base-v1`, `response-format-doview-notation-v1`, `response-format-doview-analysis-v1`) were derived.
