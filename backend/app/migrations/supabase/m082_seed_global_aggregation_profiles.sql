-- Migration 082: seed five global aggregation profiles (ADR-212).
-- Mirrors SQLite m077. Idempotent via ON CONFLICT (id) DO NOTHING.

INSERT INTO public.aggregation_profiles (
    id, name, description, set_id, is_global, profile_data,
    is_default_for_set, created_by, created_at, updated_at
) VALUES
    ('f0f2f8e8-345c-590b-a4f3-7ed320a9c8da',
     'Shopping list',
     'Sum ingredient quantities across the recipes referenced by a meal-plan diagram. Scales by per-meal diner count divided by the recipe''s `data.servings`. Groups output by aisle (the ingredient''s package_name). Pairs with the ''Quantified item'' element template (ADR-211).',
     NULL, TRUE,
     '{"traversal": {"outer": {"collect_token_type": "diagram", "multiplier": {"from_attribute_override": "attributes/Diners/type", "divisor_from_diagram_data": "data.servings", "default_multiplier": 1}}, "inner": {"collect_token_type": "element", "value_attribute_path": "attributes/Quantity/type", "bucket_attribute_path": "attributes/Unit/type", "skip_blank_values": true}}, "output": {"group_by": "element.package_name", "sort_groups": "alpha", "sort_items_within_group": "alpha", "aggregation_fn": "sum", "line_format": "- [{element.name}](iris://element/{element.id}) — {sum_value}{bucket_spaced}", "show_per_source_breakdown": true, "breakdown_format": " ({sources_joined})"}}'::jsonb,
     FALSE, NULL, NOW(), NOW()),
    ('8a41b9cb-41f0-54b8-a1eb-51e09340baf1',
     'Sprint points rollup',
     'Sum story-points across the stories referenced by a sprint backlog diagram. Groups by element.package_name (commonly the team). Pairs with the ''Sized story'' template (ADR-211).',
     NULL, TRUE,
     '{"traversal": {"outer": {"collect_token_type": "diagram"}, "inner": {"collect_token_type": "element", "value_attribute_path": "attributes/Points/type", "bucket_attribute_path": null, "skip_blank_values": true}}, "output": {"group_by": "element.package_name", "sort_groups": "alpha", "sort_items_within_group": "alpha", "aggregation_fn": "sum", "line_format": "- [{element.name}](iris://element/{element.id}) — {sum_value}{bucket_spaced}", "show_per_source_breakdown": false, "breakdown_format": " ({sources_joined})"}}'::jsonb,
     FALSE, NULL, NOW(), NOW()),
    ('fae0ac43-0be7-5a01-b6ab-30e959c5ce13',
     'Time tracker rollup',
     'Sum logged hours across the daily-log diagrams referenced by a period-of-time diagram. Groups by element.package_name (commonly the client or project). Pairs with the ''Logged work'' template (ADR-211).',
     NULL, TRUE,
     '{"traversal": {"outer": {"collect_token_type": "diagram"}, "inner": {"collect_token_type": "element", "value_attribute_path": "attributes/Hours/type", "bucket_attribute_path": null, "skip_blank_values": true}}, "output": {"group_by": "element.package_name", "sort_groups": "alpha", "sort_items_within_group": "alpha", "aggregation_fn": "sum", "line_format": "- [{element.name}](iris://element/{element.id}) — {sum_value}{bucket_spaced}", "show_per_source_breakdown": false, "breakdown_format": " ({sources_joined})"}}'::jsonb,
     FALSE, NULL, NOW(), NOW()),
    ('834d031f-95cb-5e39-8730-a42fd3e4b318',
     'Expense report',
     'Sum expense amounts across the receipt diagrams referenced by a reporting-period diagram. Bucketed by currency, grouped by element.package_name (commonly the category). Pairs with the ''Line item'' template (ADR-211).',
     NULL, TRUE,
     '{"traversal": {"outer": {"collect_token_type": "diagram"}, "inner": {"collect_token_type": "element", "value_attribute_path": "attributes/Amount/type", "bucket_attribute_path": "attributes/Currency/type", "skip_blank_values": true}}, "output": {"group_by": "element.package_name", "sort_groups": "alpha", "sort_items_within_group": "alpha", "aggregation_fn": "sum", "line_format": "- [{element.name}](iris://element/{element.id}) — {sum_value}{bucket_spaced}", "show_per_source_breakdown": false, "breakdown_format": " ({sources_joined})"}}'::jsonb,
     FALSE, NULL, NOW(), NOW()),
    ('5c6b2c26-1ae3-55d6-aa65-e001546ffda2',
     'Reading log rollup',
     'Sum pages read across the reading-log diagrams in a reading period. Groups by author (a structured element attribute). Pairs with the ''Read entry'' template (ADR-211).',
     NULL, TRUE,
     '{"traversal": {"outer": {"collect_token_type": "diagram"}, "inner": {"collect_token_type": "element", "value_attribute_path": "attributes/Pages/type", "bucket_attribute_path": null, "skip_blank_values": true}}, "output": {"group_by": "element.attributes.Author/type", "sort_groups": "alpha", "sort_items_within_group": "alpha", "aggregation_fn": "sum", "line_format": "- [{element.name}](iris://element/{element.id}) — {sum_value}{bucket_spaced}", "show_per_source_breakdown": false, "breakdown_format": " ({sources_joined})"}}'::jsonb,
     FALSE, NULL, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;
