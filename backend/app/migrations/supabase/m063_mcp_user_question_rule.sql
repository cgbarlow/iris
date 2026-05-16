-- Migration 063: insert ASKING QUESTIONS section into the
-- mcp-server-instructions-v1 singleton body (ADR-177, SPEC-177-A, v6.1.0).
--
-- Issue #133 Phase 1. Mirrors SQLite m059. Surgical REPLACE() of the
-- closing line of ORIENT-FIRST PROTOCOL section to insert the new
-- ASKING QUESTIONS section between it and DISCOVERY TOOLS.
--
-- Preserves admin customisations elsewhere in the body. Idempotent —
-- REPLACE is a no-op if the marker isn't found.

UPDATE public.ai_creation_prompts
SET prompt_text = REPLACE(
    prompt_text,
    $marker$  3. Offer the menu of options the orient sheet specifies, IN ORDER, VERBATIM. Use AskUserQuestion when the client supports it; numbered list otherwise. Do not paraphrase, do not silently drop options.$marker$,
    $replacement$  3. Offer the menu of options the orient sheet specifies, IN ORDER, VERBATIM. Use AskUserQuestion when the client supports it; numbered list otherwise. Do not paraphrase, do not silently drop options.

ASKING QUESTIONS.
Whenever you need the user to choose from a finite set of options, ask via the MCP client's structured user-question tool (AskUserQuestion in Claude Code / Claude Desktop / Cursor). Do not embed multi-option questions in prose. Do not list multiple questions in a single message — one question per turn, wait for the answer, then ask the next. When the client does not expose a user-question tool, fall back to a numbered list with options IN ORDER, VERBATIM (no paraphrasing).
This applies to:
  - the orient menu (already covered in ORIENT-FIRST above),
  - every Stage-0 setup question in a creation cascade,
  - the save-destination chooser,
  - any other choice the model surfaces to the user.
If you ever feel unsure whether a question warrants the tool: it does.$replacement$
)
WHERE purpose = 'mcp_server_instructions';
