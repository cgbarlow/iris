-- Migration 065: drop Phase-1 docx/pdf fallback (ADR-179, v6.2.0).
--
-- Issue #133 Phase 2. Mirrors SQLite m061. Surgical REPLACE() leaves
-- the cross-set move fallback intact (drops in Phase 3 v6.3.0).

UPDATE public.ai_creation_prompts
SET prompt_text = REPLACE(
    prompt_text,
    $marker$- If the user picks "Chat with downloadable artefacts" and selects
  docx or pdf at Q-Dest3, respond: "Docx and PDF generation ships in
  v6.2.0 (Phase 2 of issue #133). For now I can produce a markdown
  artefact in the chat and create the Iris bundle if you'd like."
  Then offer AskUserQuestion with options "Yes, markdown + Iris save",
  "Just the Iris save", "Cancel and wait for v6.2.0".$marker$,
    $replacement$- When the user picks "Chat with downloadable artefacts" and selects
  one or more formats at Q-Dest3, call the MCP `render_markdown`
  tool once per selected format (markdown / docx / pdf). Each call
  returns `{artefact_id, web_url, mime_type, filename}` — present the
  `web_url` to the user as a clickable download link. For "Both"
  (Iris + artefacts), also create the Iris bundle via the
  destination-specific `create_*` tools.$replacement$
)
WHERE id = 'creation-cascade-destination-v1';
