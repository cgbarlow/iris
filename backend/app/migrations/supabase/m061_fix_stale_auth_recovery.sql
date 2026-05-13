-- Migration 061: rewrite the AUTH RECOVERY + WORKFLOW GUIDANCE
-- sections of the live `mcp_server_instructions` singleton row to
-- remove references to the v6.0.0-removed `iris_authenticate` tool
-- (issue #115 follow-up, v6.0.3).
--
-- Mirrors SQLite m057. Surgical REPLACE() preserves admin
-- customisations elsewhere in the body. Idempotent.

UPDATE public.ai_creation_prompts
SET prompt_text = REPLACE(
  REPLACE(
    prompt_text,
    -- Stale WORKFLOW GUIDANCE sentence (v5.18.0):
    'Each tool''s description carries its own workflow. For diagram creation, see `create_diagram` (it explains the full discover → fetch creation cascade → guided conversation → confirm destination → save flow). For authentication, see `iris_authenticate`.',
    -- v6.0.0 replacement:
    'Each tool''s description carries its own workflow. For diagram creation, see `create_diagram` (it explains the full discover → fetch creation cascade → guided conversation → confirm destination → save flow).'
  ),
  -- Stale AUTH RECOVERY paragraph (v5.18.0):
  'Write tools that return error="auth_required" can be unblocked by the iris_authenticate flow — never tell the user to restart their MCP client.',
  -- v6.0.0 replacement:
  'If a write tool returns error="auth_required" (HTTP transport), advise the user to configure OAuth in their MCP client''s connector settings (e.g. claude.ai → Connectors → Iris → Configure → enable OAuth). The browser opens a consent screen, the user signs in to Iris, and writes work from then on. Don''t call any auth-related tool yourself — the OAuth handshake is between the MCP client and Iris, not via tool calls.'
)
WHERE purpose = 'mcp_server_instructions';
