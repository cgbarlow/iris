-- Migration 028: DoView notation, diagram types, mappings, and theme (Supabase equivalent of SQLite m027).
-- Inserts data into tables already created by m020 (registry) and m024 (themes).

-- 1. DoView notation
INSERT INTO notations (id, name, description, display_order)
VALUES ('doview', 'DoView', 'DoView outcomes-based theory of change notation', 4)
ON CONFLICT (id) DO NOTHING;

-- 2. DoView diagram types
INSERT INTO diagram_types (id, name, description, display_order)
VALUES ('outcomes_map', 'Outcomes Map', 'Left-to-right causal outcomes flow', 7)
ON CONFLICT (id) DO NOTHING;

INSERT INTO diagram_types (id, name, description, display_order)
VALUES ('overview', 'Overview', 'High-level overview with navigation tiles', 8)
ON CONFLICT (id) DO NOTHING;

-- 3. Notation–diagram-type mappings
INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('outcomes_map', 'doview', TRUE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('overview', 'doview', TRUE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('free_form', 'doview', FALSE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

-- 4. DoView default theme (upsert)
INSERT INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at)
VALUES (
    'doview-default',
    'DoView Default',
    'Official DoView 10-color palette — DoViewPlanning.org',
    'doview',
    '{"element_defaults": {"outcome_box": {"bgColor": "#FFF2CC", "borderColor": "#D6B656", "fontColor": "#333333", "borderWidth": 2}, "final_outcome": {"bgColor": "#FFFFFF", "borderColor": "#CCCCCC", "fontColor": "#333333", "borderWidth": 2}, "overview_tile": {"bgColor": "#DAE8FC", "borderColor": "#6C8EBF", "fontColor": "#333333", "borderWidth": 2}, "source_reference": {"bgColor": "#F5F5F5", "borderColor": "#666666", "fontColor": "#333333", "borderWidth": 1}}, "stereotype_overrides": {"page_yellow": {"bgColor": "#FFF2CC", "borderColor": "#D6B656"}, "page_pink": {"bgColor": "#F8CECC", "borderColor": "#B85450"}, "page_blue": {"bgColor": "#DAE8FC", "borderColor": "#6C8EBF"}, "page_green": {"bgColor": "#D5E8D4", "borderColor": "#82B366"}, "page_beige": {"bgColor": "#FFF4E6", "borderColor": "#D4A574"}, "page_lavender": {"bgColor": "#E1D5E7", "borderColor": "#9673A6"}, "page_peach": {"bgColor": "#FFE6CC", "borderColor": "#D79B00"}, "page_cyan": {"bgColor": "#D4E1F5", "borderColor": "#7EA6E0"}, "page_grey": {"bgColor": "#F5F5F5", "borderColor": "#666666"}, "page_white": {"bgColor": "#FFFFFF", "borderColor": "#CCCCCC"}}, "edge_defaults": {"causal_link": {"lineColor": "#C8C8C8", "lineWidth": 2}}, "global": {"defaultBgColor": "#FFF2CC", "defaultBorderColor": "#D6B656", "defaultFontColor": "#333333"}, "rendering": {"hideIcons": false, "borderRadius": 4}}',
    TRUE,
    'system',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;
