-- Migration 045: Text diagram subclass + Markdown notation (ADR-137).
-- Supabase equivalent of SQLite m044_text_diagram_class.py.

-- 1. Markdown notation
INSERT INTO notations (id, name, description, display_order)
VALUES ('markdown', 'Markdown', 'Markdown text documents (Text diagram subclass)', 6)
ON CONFLICT (id) DO NOTHING;

-- 2. Text diagram type
INSERT INTO diagram_types (id, name, description, display_order)
VALUES ('text', 'Text Document', 'Markdown-backed text document with TOC navigation', 15)
ON CONFLICT (id) DO NOTHING;

-- 3. Mapping (text defaults to markdown)
INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('text', 'markdown', TRUE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

-- 4. AI creation prompt
INSERT INTO ai_creation_prompts (id, name, description, layer, notation, diagram_type, prompt_text, display_order, is_active, created_by)
VALUES (
    'markdown-notation',
    'Markdown Text Prompt',
    'Guidance for generating markdown content for Text diagrams',
    'notation',
    'markdown',
    NULL,
    $md$Text diagrams hold structured markdown content rather than a graph canvas. Use standard markdown for headings (#, ##, ###), lists, code fences, and links. To link to other Iris models from inside the markdown, use the iris:// URL scheme: [Some Diagram Name](iris://diagram/<id>) or [Some Element](iris://element/<id>). These render as in-app navigation — clicking takes the reader to the target. Headings drive the TOC drawer; sub-headings auto-indent by depth. Output the document as a single string assigned to data.content. Do NOT output canvas nodes/edges — text diagrams have no graph.$md$,
    100,
    TRUE,
    'system'
)
ON CONFLICT (id) DO UPDATE SET prompt_text = EXCLUDED.prompt_text, updated_at = NOW();
