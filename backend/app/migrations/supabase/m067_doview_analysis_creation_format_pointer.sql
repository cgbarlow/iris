-- Migration 067: backstop creation_format pointer to response_format
-- for (markdown, doview_analysis) — v6.6.2 regression fix.
--
-- Mirrors SQLite m063. Adds a creation_format row at
-- (layer='diagram_type', diagram_type='doview_analysis') that tells
-- the model to also fetch the response_format cascade when creating a
-- doview_analysis via create_diagram.
--
-- Idempotent (ON CONFLICT DO NOTHING).

INSERT INTO public.ai_creation_prompts
    (id, name, description, purpose, layer, notation, diagram_type, prompt_text, display_order, is_active)
VALUES (
    'creation-format-doview-analysis-pointer-v1',
    'DoView Analysis — response_format pointer (creation cascade)',
    'Backstop instruction telling the model to fetch and apply the response_format rules when creating a (markdown, doview_analysis) via the creation cascade. Single source of truth for the actual rules stays on the response_format side per DRY. ADR-157 + ADR-180 follow-up, v6.6.2.',
    'creation_format',
    'diagram_type',
    NULL,
    'doview_analysis',
    $body$## CRITICAL: doview_analysis output structure rules

This diagram's markdown content (`data.content`) MUST follow the
output-structure rules defined in the corresponding response_format
cascade. Those rules are the single source of truth for the
doview_analysis output shape (required opening sentence, three
standalone sections — Summary / Full / Diagrams — outcomes-theory
framing, outcomes-system definition, tool URLs, full handbook
reference at the end).

Before composing the markdown body, fetch and apply:

  get_response_prompt(
    notation='markdown',
    diagram_type='doview_analysis',
    purpose='response_format'
  )

The body returned by that call contains the full set of rules. The
markdown you generate for `data.content` must comply with every one.
Without this fetch, the doview_analysis you produce will not match
the expected output structure and will fail content review.

This pointer exists because the creation_format cascade and
response_format cascade are separate code paths (purpose-discriminated
since ADR-157 / v5.12.0). Cascade-driven creation needs to know that
for (markdown, doview_analysis) the content rules live on the OTHER
purpose. Single source of truth (response_format) preserved; this row
is a pointer, not duplicated content.
$body$,
    0,
    TRUE
)
ON CONFLICT (id) DO NOTHING;
