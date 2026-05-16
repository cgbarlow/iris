-- Migration 069: Dynamic List diagram type (ADR-186, issue #147).
--
-- Mirrors SQLite m065. Registers ``dynamic_list`` under the existing
-- ``markdown`` notation. Idempotent.

INSERT INTO public.diagram_types (id, name, description, display_order)
VALUES ('dynamic_list', 'Dynamic List',
        'Auto-generated markdown bullet list', 16)
ON CONFLICT (id) DO NOTHING;

-- Postgres `is_default` is boolean (Supabase schema); SQLite uses 0.
INSERT INTO public.diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('dynamic_list', 'markdown', FALSE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;
