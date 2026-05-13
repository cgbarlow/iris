# DoView / Outcomes-Theory Set — `mcp_system_context` content

Canonical paste-ready content for the **MCP system context** field on the Outcomes Theory Set (`/sets/33032180-d77a-4ce4-88cf-b49cd643e093`, previously named "DoView Book"). The same content flows through both `get_set` and (since v5.14.0 / ADR-159) `search` results, so an MCP client model sees this orient sheet the moment the set is matched.

**Scope only.** The generic ORIENT-FIRST protocol and DISCOVERY catalogue have moved to the server-wide MCP `instructions` field (v5.18.0 / ADR-163); this scope content only carries what's specific to the DoView handbook.

## Content (paste this into the field on UAT)

```text
This set is the visual companion to Dr Paul Duignan's outcomes-theory body of work and DoView outcomes-mapping methodology.

Structural overview call: package_hierarchy(set_id=<this-set>) — lists Part A through Part J with one-line descriptions.

MENU (verbatim, all four):
  1. Pull up a specific chapter or diagram from the handbook (e.g. J06 — Mathematization of Outcomes Theory).
  2. Ask a cross-package question via Iris AI (e.g. "What are the recurring causal-link conventions?" — uses mcp__iris__ask).
  3. Generate a new DoView outcomes-theory analysis OR a new visual DoView outcomes_map → call create_diagram.
  4. Browse a particular chapter's diagrams in detail.
```

## Why this works

- **The orient-first protocol is universal, not scope-specific.** v5.18.0 (ADR-163) lifted it into the MCP server `instructions` field — see [`mcp-server-instructions.md`](./mcp-server-instructions.md). Every authored scope automatically gets the "describe, call structural overview, present menu verbatim" behaviour. This scope content just supplies the specifics.
- **DISCOVERY catalogue is universal too.** Also lifted to server instructions.
- **Diagram-creation workflow lives in the `create_diagram` tool description.** v5.17.0 (ADR-162). Not duplicated here.

## Revision history

- **v5.18.0 (this revision).** Stripped ORIENT-FIRST protocol and DISCOVERY catalogue — now in server-wide MCP instructions (ADR-163). Down from ~30 lines (v5.17.0) to ~12.
- **v5.17.0.** Stripped diagram-creation workflow — now in `create_diagram`'s tool description (ADR-162).
- **v5.14.0.** Trimmed from ~140 lines to ~50. Surfaced through search results too (ADR-159).
- **v5.13.3.** Made the four-option menu mandatory and verbatim.
- **v5.13.2.** Restored orient-first / offer-menu pattern.
- **v5.13.0.** Mention `iris_package_hierarchy` (ADR-158).
- **v5.12.0.** Save-options offer added.

## See also

- [`mcp-server-instructions.md`](./mcp-server-instructions.md) — the universal orient-first protocol + discovery catalogue (v5.18.0).
- [ADR-156](../adrs/ADR-156-MCP-System-Context-Data-Passthrough.md) — what `mcp_system_context` is for.
- [ADR-159](../adrs/ADR-159-Scope-Context-In-Search-Results.md) — search results carry `mcp_system_context`.
- [ADR-162](../adrs/ADR-162-Generic-MCP-Diagram-Creation-Workflow.md) — generic `create_diagram` + workflow-in-tool-descriptions.
- [ADR-163](../adrs/ADR-163-Centralised-MCP-Server-Instructions.md) — server-wide instructions channel.
