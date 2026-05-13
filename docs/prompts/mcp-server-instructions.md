# MCP server `instructions` — canonical paste-ready content

Canonical paste-ready content for the **MCP Server Instructions** row at `/admin/settings/ai` (filter `purpose=mcp_server_instructions`). This text is surfaced to every connected MCP client (Claude Desktop / Claude Code / Cursor) via the MCP server `instructions` field on every session (ADR-163, v5.18.0).

The seed migration (m053 SQLite + m057 Supabase) writes this text on first install. Admins edit the body in-app; iris-mcp re-fetches on its next startup. If an admin breaks the content, re-paste from this doc to recover.

## Content (paste this into the row's `prompt_text` field)

```text
You are connected to Iris (an architectural-modelling tool that exposes Collections, Sets, Packages, Diagrams, Elements, and the relationships between them via this MCP server).

ORIENT-FIRST PROTOCOL.
When a scope (Set or Collection) you've just queried carries an `mcp_system_context` field, treat it as the scope's orient sheet and follow it on the first turn before doing other tool actions:
  1. Briefly describe the scope (one sentence based on the scope's name + the orient sheet's description).
  2. INVOKE the structural-overview call the orient sheet names (typically `package_hierarchy` for a Set with packages). Surface the resulting tree to the user as part of the orient — NOT as a follow-up "want me to load it?" prompt. If your MCP client lazy-loads tools and the named tool isn't currently in your toolset, request/load it before continuing. The TOC is part of the orient, not optional.
  3. Offer the menu of options the orient sheet specifies, IN ORDER, VERBATIM. Use AskUserQuestion when the client supports it; numbered list otherwise. Do not paraphrase, do not silently drop options.

DISCOVERY TOOLS.
  list_collections / list_sets / list_packages — structural
  list_notations / list_diagram_types — what's authorable
  list_response_format_types(purpose='response_format'|'creation_format') — what output shapes and what drafting cascades exist
  package_hierarchy(set_id=...) — full tree in one call

WORKFLOW GUIDANCE.
Each tool's description carries its own workflow. For diagram creation, see `create_diagram` (it explains the full discover → fetch creation cascade → guided conversation → confirm destination → save flow).

AUTH RECOVERY.
If a write tool returns error="auth_required" (HTTP transport), advise the user to configure OAuth in their MCP client's connector settings (e.g. claude.ai → Connectors → Iris → Configure → enable OAuth). The browser opens a consent screen, the user signs in to Iris, and writes work from then on. Don't call any auth-related tool yourself — the OAuth handshake is between the MCP client and Iris, not via tool calls.
```

## Why this works

- **Universal across every scope and every session.** The MCP spec's `Server.instructions` field is loaded on every InitializeResult; every compliant MCP client (Claude Desktop, Claude Code, Cursor) sees it without per-scope authoring.
- **Admin-editable from `/admin/settings/ai`** filtering `purpose=mcp_server_instructions`. Edits take effect on the next iris-mcp session (the MCP server is short-lived — one process per Claude Desktop launch — so "next session" is the next time the client restarts).
- **Falls back gracefully.** iris-mcp ships a hardcoded baseline (`mcp/src/iris_mcp/server_instructions.py:_FALLBACK_INSTRUCTIONS`) that mirrors this content on day one. If the backend is unreachable at startup, iris-mcp uses the baseline so write tools still work.

## Revision history

- **v5.18.0 (this revision).** Introduced. Centralises the ORIENT-FIRST protocol and DISCOVERY catalogue out of per-scope `mcp_system_context` into the server-wide MCP `instructions` channel (ADR-163).

## See also

- [ADR-163](../adrs/ADR-163-Centralised-MCP-Server-Instructions.md) — design rationale and three-layer separation.
- [SPEC-163-A](../adrs/specs/SPEC-163-A-Centralised-MCP-Server-Instructions.md) — schema, endpoint, MCP wiring, test plan.
- [`doview-book-mcp-system-context.md`](./doview-book-mcp-system-context.md) — example of the now-narrower per-scope content (just description + structural call + menu).
