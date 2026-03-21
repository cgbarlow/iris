-- Migration 023: New diagram types and notation mappings (ADR-082).
-- Adds 6 new diagram types and additional notation mappings.

-- ── New diagram types ─────────────────────────────────────────────────────────

INSERT INTO diagram_types (id, name, description, display_order) VALUES
    ('use_case',      'Use Case',      'User goals and system interactions',     7),
    ('state_machine', 'State Machine', 'State transitions and lifecycles',       8),
    ('system_context','System Context','C4 Level 1 — systems and actors',        9),
    ('container',     'Container',     'C4 Level 2 — containers within a system',10),
    ('motivation',    'Motivation',    'ArchiMate motivation viewpoint',         11),
    ('strategy',      'Strategy',      'ArchiMate strategy viewpoint',           12)
ON CONFLICT (id) DO NOTHING;

-- ── New notation mappings ─────────────────────────────────────────────────────

INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default) VALUES
    -- use_case
    ('use_case',      'simple',    FALSE),
    ('use_case',      'uml',       TRUE),
    -- state_machine
    ('state_machine', 'simple',    FALSE),
    ('state_machine', 'uml',       TRUE),
    -- system_context
    ('system_context','simple',    FALSE),
    ('system_context','c4',        TRUE),
    -- container
    ('container',     'simple',    FALSE),
    ('container',     'c4',        TRUE),
    -- motivation
    ('motivation',    'archimate', TRUE),
    -- strategy
    ('strategy',      'archimate', TRUE),
    -- Quick-win: archimate on roadmap (default stays simple)
    ('roadmap',       'archimate', FALSE),
    -- Quick-win: c4 on sequence (default stays uml)
    ('sequence',      'c4',        FALSE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;
