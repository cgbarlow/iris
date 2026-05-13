-- Migration 057: seed the MCP server-instructions singleton row
-- (ADR-163, SPEC-163-A, v5.18.0).
--
-- Mirrors SQLite m053. One row in `ai_creation_prompts` with the new
-- `purpose='mcp_server_instructions'` discriminator value. iris-mcp
-- fetches this at startup via GET /api/ai/server-instructions and
-- passes the body to the MCP SDK Server(instructions=...) constructor.
--
-- Idempotent (ON CONFLICT DO NOTHING on id).

INSERT INTO public.ai_creation_prompts
    (id, name, description, purpose, layer, notation, diagram_type, prompt_text, display_order, is_active)
VALUES (
    'mcp-server-instructions-v1',
    'MCP Server Instructions',
    'Universal orient-first protocol + discovery catalogue surfaced by iris-mcp via the MCP server `instructions` field (ADR-163, v5.18.0). One singleton row at layer=base.',
    'mcp_server_instructions',
    'base',
    NULL,
    NULL,
    $body$You are connected to Iris (an architectural-modelling tool that exposes Collections, Sets, Packages, Diagrams, Elements, and the relationships between them via this MCP server).

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
Each tool's description carries its own workflow. For diagram creation, see `create_diagram` (it explains the full discover → fetch creation cascade → guided conversation → confirm destination → save flow). For authentication, see `iris_authenticate`.

AUTH RECOVERY.
Write tools that return error="auth_required" can be unblocked by the iris_authenticate flow — never tell the user to restart their MCP client.
$body$,
    0,
    TRUE
)
ON CONFLICT (id) DO NOTHING;
