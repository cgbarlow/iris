-- Migration 044: BPMN 2.0 notation, diagram types, mappings, theme, and AI prompts.
-- Supabase equivalent of SQLite m043_bpmn_notation.py.
-- ADR-136. Reuses the existing 'process' diagram_type from m020;
-- adds 'collaboration' and 'choreography' as BPMN-specific diagram types.

-- 1. BPMN notation
INSERT INTO notations (id, name, description, display_order)
VALUES ('bpmn', 'BPMN', 'Business Process Model and Notation 2.0', 5)
ON CONFLICT (id) DO NOTHING;

-- 2. New BPMN-specific diagram types
INSERT INTO diagram_types (id, name, description, display_order)
VALUES ('collaboration', 'Collaboration', 'BPMN — multiple pools exchanging messages', 13)
ON CONFLICT (id) DO NOTHING;

INSERT INTO diagram_types (id, name, description, display_order)
VALUES ('choreography', 'Choreography', 'BPMN — interaction sequence between participants', 14)
ON CONFLICT (id) DO NOTHING;

-- 3. Notation–diagram-type mappings
INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('process', 'bpmn', FALSE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('collaboration', 'bpmn', TRUE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('choreography', 'bpmn', TRUE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('free_form', 'bpmn', FALSE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

-- 4. BPMN default theme (Camunda-inspired neutral palette)
INSERT INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at)
VALUES (
    'bpmn-default',
    'BPMN Default',
    'Camunda-inspired neutral palette mirroring bpmn-js styling',
    'bpmn',
    '{"element_defaults": {"task": {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 2}, "subprocess": {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 2}, "call_activity": {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 4}, "event_start": {"bgColor": "#E0F2D6", "borderColor": "#3BA51F", "fontColor": "#202931", "borderWidth": 1}, "event_intermediate": {"bgColor": "#F4F4F4", "borderColor": "#A88B0F", "fontColor": "#202931", "borderWidth": 1}, "event_end": {"bgColor": "#FBE3E3", "borderColor": "#C03434", "fontColor": "#202931", "borderWidth": 4}, "event_boundary": {"bgColor": "#FFFFFF", "borderColor": "#A88B0F", "fontColor": "#202931", "borderWidth": 1}, "gateway": {"bgColor": "#FFFFFF", "borderColor": "#A88B0F", "fontColor": "#202931", "borderWidth": 2}, "pool": {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 2}, "lane": {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 1}, "data_object": {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 1}, "data_store": {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 1}, "group": {"bgColor": "transparent", "borderColor": "#666666", "fontColor": "#202931", "borderWidth": 1}, "text_annotation": {"bgColor": "transparent", "borderColor": "transparent", "fontColor": "#202931", "borderWidth": 0}}, "edge_defaults": {"sequence_flow": {"lineColor": "#202931", "lineWidth": 2}, "sequence_flow_default": {"lineColor": "#202931", "lineWidth": 2}, "sequence_flow_conditional": {"lineColor": "#202931", "lineWidth": 2}, "message_flow": {"lineColor": "#202931", "lineWidth": 2}, "association": {"lineColor": "#666666", "lineWidth": 1}, "data_association": {"lineColor": "#666666", "lineWidth": 1}}, "global": {"defaultBgColor": "#FFFFFF", "defaultBorderColor": "#202931", "defaultFontColor": "#202931"}, "rendering": {"hideIcons": false, "borderRadius": 6, "wrapLabels": true, "textAlign": "center"}}',
    TRUE,
    'system',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- 5. AI creation prompts (notation-level + per-diagram-type guidance)
INSERT INTO ai_creation_prompts (id, name, description, layer, notation, diagram_type, prompt_text, display_order, is_active, created_by)
VALUES (
    'bpmn-notation',
    'BPMN Notation Prompt',
    'BPMN 2.0 element catalogue and structural rules',
    'notation',
    'bpmn',
    NULL,
    $bpmn$BPMN 2.0 (Business Process Model and Notation) is a left-to-right flow notation for business processes. Element categories: Activities (Task, Subprocess, Call Activity), Events (Start/Intermediate/End/Boundary, with trigger variants — none/message/timer/signal/conditional/error/escalation/compensation/link/terminate), Gateways (Exclusive/Inclusive/Parallel/Event-Based/Complex), Swimlanes (Pool, Lane), Data (Data Object, Data Store), Artifacts (Group, Text Annotation). Connecting Objects: Sequence Flow (within a process), Message Flow (between pools), Association, Data Association.

Hard rules: a Sequence Flow must NOT cross pool boundaries — use a Message Flow instead. Every process should start with a Start Event and end with at least one End Event. Gateways branch and merge — every diverging gateway should have a corresponding converging gateway. Lanes belong inside a Pool.

Use the entity-type discriminator fields on `data` to select shape variants: data.taskType for Task markers, data.gatewayType for gateway inner marker, data.eventTrigger + data.eventDirection (catch/throw) for event variants, data.boundaryInterrupting (true=solid border, false=dashed) for boundary events, data.subprocessKind for subprocess variants, data.dataKind for data variants.$bpmn$,
    100,
    TRUE,
    'system'
)
ON CONFLICT (id) DO UPDATE SET prompt_text = EXCLUDED.prompt_text, updated_at = NOW();

INSERT INTO ai_creation_prompts (id, name, description, layer, notation, diagram_type, prompt_text, display_order, is_active, created_by)
VALUES (
    'bpmn-process',
    'BPMN Process Prompt',
    'BPMN-specific guidance for process diagrams',
    'diagram_type',
    'bpmn',
    'process',
    'BPMN Process diagrams model the flow of work within a single organisation or system. Use one Pool implicitly (no need to draw it for a single-participant process). Lanes partition responsibilities. Keep flow left-to-right or top-to-bottom; don''t mix.',
    100,
    TRUE,
    'system'
)
ON CONFLICT (id) DO UPDATE SET prompt_text = EXCLUDED.prompt_text, updated_at = NOW();

INSERT INTO ai_creation_prompts (id, name, description, layer, notation, diagram_type, prompt_text, display_order, is_active, created_by)
VALUES (
    'bpmn-collaboration',
    'BPMN Collaboration Prompt',
    'BPMN-specific guidance for collaboration diagrams',
    'diagram_type',
    'bpmn',
    'collaboration',
    'BPMN Collaboration diagrams model interactions between two or more Pools. Each Pool is a participant. Sequence Flows stay inside their Pool; Message Flows cross between Pools. Black-box pools (no internal flow) represent external participants.',
    100,
    TRUE,
    'system'
)
ON CONFLICT (id) DO UPDATE SET prompt_text = EXCLUDED.prompt_text, updated_at = NOW();

INSERT INTO ai_creation_prompts (id, name, description, layer, notation, diagram_type, prompt_text, display_order, is_active, created_by)
VALUES (
    'bpmn-choreography',
    'BPMN Choreography Prompt',
    'BPMN-specific guidance for choreography diagrams',
    'diagram_type',
    'bpmn',
    'choreography',
    'BPMN Choreography diagrams model the message exchange sequence between participants without a controlling pool. Each Choreography Task names two participants and the message between them.',
    100,
    TRUE,
    'system'
)
ON CONFLICT (id) DO UPDATE SET prompt_text = EXCLUDED.prompt_text, updated_at = NOW();
