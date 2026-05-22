-- Migration 080: seed five global element-template stamps (ADR-211).
--
-- Mirrors SQLite m075. Inserts the canonical "Quantified item / Sized
-- story / Logged work / Line item / Read entry" stamps as global
-- element_templates with deterministic UUIDs (matching m075's UUIDv5
-- computation: uuid5(ns="c1f5b6e0-1b4e-4f1c-9a2d-211211211211",
-- "global-stamp:<name>")).
--
-- Idempotent via ON CONFLICT (id) DO NOTHING.

INSERT INTO public.element_templates (
    id, name, description,
    set_id, is_global,
    source_element_id, included_fields, template_data, markdown_stamp,
    created_by, created_at, updated_at
)
VALUES
    (
        'ea8829e5-6e3f-5cf6-b1cc-a5ad92312dbf',
        'Quantified item',
        'Element with a numeric quantity + unit (groceries, parts, stock items, line items in a list with totals). Pairs with the ''Shopping list'' / sum-by-unit aggregation profile.',
        NULL, TRUE,
        NULL,
        '["element_type", "notation", "data"]'::jsonb::text,
        '{"element_type":"class","notation":"simple","data":{"attributes":[{"name":"Quantity","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""},{"name":"Unit","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""}]}}',
        '{{self:attr:attributes/Quantity/type=}} {{self:attr:attributes/Unit/type}} {{self:name}}',
        NULL,
        NOW(), NOW()
    ),
    (
        '08f53b8a-3876-5af5-bd9d-5b6959fea660',
        'Sized story',
        'Work item with story points. Pairs with the ''Sprint points rollup'' aggregation profile.',
        NULL, TRUE,
        NULL,
        '["element_type", "notation", "data"]'::jsonb::text,
        '{"element_type":"class","notation":"simple","data":{"attributes":[{"name":"Points","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""}]}}',
        '{{self:attr:attributes/Points/type=}} pts — {{self:name}}',
        NULL,
        NOW(), NOW()
    ),
    (
        '7fd2b6d1-4cd7-5322-ae72-c753bbea649f',
        'Logged work',
        'Work-log entry with hours. Pairs with the ''Time tracker rollup'' aggregation profile.',
        NULL, TRUE,
        NULL,
        '["element_type", "notation", "data"]'::jsonb::text,
        '{"element_type":"class","notation":"simple","data":{"attributes":[{"name":"Hours","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""}]}}',
        '{{self:attr:attributes/Hours/type=}}h — {{self:name}}',
        NULL,
        NOW(), NOW()
    ),
    (
        'afd69eab-832b-5ee5-a885-ec745b2e3b22',
        'Line item',
        'Expense / billing line item. Pairs with the ''Expense report'' aggregation profile.',
        NULL, TRUE,
        NULL,
        '["element_type", "notation", "data"]'::jsonb::text,
        '{"element_type":"class","notation":"simple","data":{"attributes":[{"name":"Amount","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""},{"name":"Currency","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""}]}}',
        '{{self:attr:attributes/Currency/type}}{{self:attr:attributes/Amount/type=}} — {{self:name}}',
        NULL,
        NOW(), NOW()
    ),
    (
        '7a17859b-838e-58ed-aff0-a3f5c94284be',
        'Read entry',
        'Reading-log entry. Pairs with the ''Reading log rollup'' aggregation profile.',
        NULL, TRUE,
        NULL,
        '["element_type", "notation", "data"]'::jsonb::text,
        '{"element_type":"class","notation":"simple","data":{"attributes":[{"name":"Pages","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""},{"name":"Author","type":"","scope":"Public","notes":"","lower_bound":"","upper_bound":""}]}}',
        '{{self:attr:attributes/Pages/type=}} pages — "{{self:name}}" by {{self:attr:attributes/Author/type}}',
        NULL,
        NOW(), NOW()
    )
ON CONFLICT (id) DO NOTHING;
