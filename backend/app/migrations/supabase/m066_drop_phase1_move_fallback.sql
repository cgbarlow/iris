-- Migration 066: drop Phase-1 cross-set move fallback (ADR-178, v6.3.0).
--
-- Issue #133 Phase 3. Mirrors SQLite m062.

UPDATE public.ai_creation_prompts
SET prompt_text = REPLACE(
    prompt_text,
    $marker$- If the user picks "Somewhere else" or "Browse" at Q-Dest2 and the
  chosen destination differs from the current set, respond: "I can
  draft the bundle and save it into the current set now, then move it
  to your chosen destination after v6.3.0 ships move_* tools. Or I
  can describe what I'd save without actually saving, and you can
  re-run after v6.3.0." Then offer AskUserQuestion with these two
  fallbacks.$marker$,
    $replacement$- When the user picks "Somewhere else" or "Browse" at Q-Dest2 and the
  chosen destination differs from the current set: if the destination
  is an EXISTING set, save the bundle into the current set and then
  call `move_diagram` / `move_package` to relocate; if the destination
  is a NEW set under a different collection, call `create_set` first
  (in the target collection) and save the bundle directly into the
  newly-created set. Move tools cycle-check and are scope-limited to
  in-set re-parenting; cross-set moves require a `create_set` +
  re-save round trip.$replacement$
)
WHERE id = 'creation-cascade-destination-v1';
