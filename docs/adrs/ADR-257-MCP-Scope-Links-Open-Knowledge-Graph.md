# ADR-257: MCP Links to Sets and Collections Open the Knowledge Graph

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-257 |
| **Initiative** | "Open collection X" from an MCP client lands on the knowledge graph |
| **Proposed By** | Product owner (2026-09-27) |
| **Date** | 2026-09-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the MCP server's `web_url` decoration (ADR-175 and
`mcp/src/iris_mcp/links.py`), which gives the model a link to quote for every
entity, and the prompt preamble in `prompts.py`, which built its own copy of
the same URL,

**facing** links for sets and collections that pointed at their info pages
(`/sets/<id>` and `/collections/<id>`). When a user asks an MCP client to
"open collection X", they expect the knowledge graph view
(`/?collection_id=<id>` or `/?set_id=<id>`). The web UI itself already uses
that view when you navigate into a scope,

**we decided to** make `web_url_for` return `<base>/?set_id=<id>` for sets and
`<base>/?collection_id=<id>` for collections. `prompts.py` now calls
`web_url_for` instead of keeping its own URL builder (protocol §13). Diagrams,
elements and packages keep their `/<path>/<id>` links,

**and neglected** (a) returning two fields (`web_url` for the graph and an
`info_url` for the info page). Rejected: the model would have to choose between
them, and the requirement is that the MCP always opens the graph. The info
page can be reached from the graph view; (b) telling the model in the server
instructions to rewrite the URL. Rejected: models copy `web_url` verbatim, so
the only reliable fix is to change the value,

**to achieve** MCP links to sets and collections that always open the
knowledge graph view,

**accepting that** an MCP client can no longer link straight to a scope's info
page.

---

## Consequences

- MCP only. No backend, CLI or frontend change, so surface parity is
  unaffected.
- This refines ADR-175's link targets for two kinds of entity. ADR-175 itself
  is unchanged.

## Dependencies

- ADR-175 (web_url decoration), ADR-152 / ADR-154 (MCP prompts preamble).

## References

- Implementation spec: [SPEC-257-A](./specs/SPEC-257-A-MCP-Scope-Links-Open-Knowledge-Graph.md)
