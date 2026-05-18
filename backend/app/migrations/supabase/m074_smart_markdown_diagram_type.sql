-- Migration 074: Smart Markdown diagram type (ADR-205, issue #185).
--
-- Mirrors SQLite m070. Registers ``smart_markdown`` under the existing
-- ``markdown`` notation (ADR-137). No new tables — source markdown
-- lives in ``diagrams.data.markdown_source`` JSON; resolved content is
-- synthesised on read into ``diagrams.data.content``.
--
-- Idempotent via ON CONFLICT DO NOTHING.

INSERT INTO public.diagram_types (id, name, description, display_order)
VALUES (
    'smart_markdown',
    'Smart Markdown',
    'Markdown with inline references to Iris entity fields',
    17
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES (
    'smart_markdown',
    'markdown',
    FALSE
)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;
