-- Migration 083: register the `aggregation_list` diagram type (ADR-213).
--
-- Mirrors SQLite m078. Same two-table pattern as m074 (smart_markdown).

INSERT INTO public.diagram_types (id, name, description, display_order)
VALUES (
    'aggregation_list',
    'Aggregation list',
    'Synth-on-read aggregation of a source smart-markdown diagram',
    99
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES (
    'aggregation_list',
    'markdown',
    FALSE
)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;
