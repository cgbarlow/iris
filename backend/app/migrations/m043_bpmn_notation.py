"""Migration 043: BPMN 2.0 notation, diagram types, mappings, and theme (ADR-136).

Adds BPMN as the sixth notation alongside Simple/UML/ArchiMate/C4/DoView.
The existing 'process' diagram_type (m020) is mapped to BPMN as default;
two new BPMN-specific diagram types are added: 'collaboration' and
'choreography'.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


_NOTATION = ("bpmn", "BPMN", "Business Process Model and Notation 2.0", 5)

_DIAGRAM_TYPES = [
    # process already exists from m020 — only adding the new BPMN-specific ones.
    ("collaboration", "Collaboration", "BPMN — multiple pools exchanging messages", 13),
    ("choreography",  "Choreography",  "BPMN — interaction sequence between participants", 14),
]

_MAPPINGS = [
    # process: existing diagram_type — BPMN becomes a non-default option for it.
    ("process",       "bpmn", 0),
    # Collaboration & choreography are BPMN-only; BPMN is their default.
    ("collaboration", "bpmn", 1),
    ("choreography",  "bpmn", 1),
    # free_form gets BPMN as a non-default option.
    ("free_form",     "bpmn", 0),
]

# Camunda-inspired neutral theme — works on both light and dark canvases.
# OMG BPMN 2.0 doesn't standardise colours, but this palette mirrors the
# de-facto bpmn-js / Camunda Modeler styling that practitioners recognise.
_BPMN_THEME_CONFIG = {
    "element_defaults": {
        # Activities — pale grey fill, dark border.
        "task":           {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 2},
        "subprocess":     {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 2},
        "call_activity":  {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 4},
        # Events — colour by position. Start = green, intermediate = neutral, end = red.
        "event_start":        {"bgColor": "#E0F2D6", "borderColor": "#3BA51F", "fontColor": "#202931", "borderWidth": 1},
        "event_intermediate": {"bgColor": "#F4F4F4", "borderColor": "#A88B0F", "fontColor": "#202931", "borderWidth": 1},
        "event_end":          {"bgColor": "#FBE3E3", "borderColor": "#C03434", "fontColor": "#202931", "borderWidth": 4},
        "event_boundary":     {"bgColor": "#FFFFFF", "borderColor": "#A88B0F", "fontColor": "#202931", "borderWidth": 1},
        # Gateway — neutral diamond.
        "gateway":            {"bgColor": "#FFFFFF", "borderColor": "#A88B0F", "fontColor": "#202931", "borderWidth": 2},
        # Swimlanes — light fill, distinct border.
        "pool":               {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 2},
        "lane":               {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 1},
        # Data — paper white.
        "data_object":        {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 1},
        "data_store":         {"bgColor": "#FFFFFF", "borderColor": "#202931", "fontColor": "#202931", "borderWidth": 1},
        # Artifacts.
        "group":              {"bgColor": "transparent", "borderColor": "#666666", "fontColor": "#202931", "borderWidth": 1},
        "text_annotation":    {"bgColor": "transparent", "borderColor": "transparent", "fontColor": "#202931", "borderWidth": 0},
    },
    "edge_defaults": {
        "sequence_flow":             {"lineColor": "#202931", "lineWidth": 2},
        "sequence_flow_default":     {"lineColor": "#202931", "lineWidth": 2},
        "sequence_flow_conditional": {"lineColor": "#202931", "lineWidth": 2},
        "message_flow":              {"lineColor": "#202931", "lineWidth": 2},
        "association":               {"lineColor": "#666666", "lineWidth": 1},
        "data_association":          {"lineColor": "#666666", "lineWidth": 1},
    },
    "global": {
        "defaultBgColor": "#FFFFFF",
        "defaultBorderColor": "#202931",
        "defaultFontColor": "#202931",
    },
    "rendering": {
        "hideIcons": False,
        "borderRadius": 6,  # rounded corners on activities
        "wrapLabels": True,
        "textAlign": "center",
    },
}


# AI creation prompts taught to the LLM when the user picks BPMN. Layered:
# notation-level prompt always applies; diagram-type-level prompts apply
# only for that diagram type.
_AI_NOTATION_PROMPT = (
    "BPMN 2.0 (Business Process Model and Notation) is a left-to-right flow notation "
    "for business processes. Element categories: Activities (Task, Subprocess, Call Activity), "
    "Events (Start/Intermediate/End/Boundary, with trigger variants — none/message/timer/signal/"
    "conditional/error/escalation/compensation/link/terminate), Gateways (Exclusive/Inclusive/"
    "Parallel/Event-Based/Complex), Swimlanes (Pool, Lane), Data (Data Object, Data Store), "
    "Artifacts (Group, Text Annotation). Connecting Objects: Sequence Flow (within a process), "
    "Message Flow (between pools), Association, Data Association. "
    "Hard rules: a Sequence Flow must NOT cross pool boundaries — use a Message Flow instead. "
    "Every process should start with a Start Event and end with at least one End Event. "
    "Gateways branch and merge — every diverging gateway should have a corresponding converging gateway. "
    "Lanes belong inside a Pool. Use the entity-type discriminator fields on `data` to select "
    "shape variants: data.taskType for Task markers, data.gatewayType for gateway inner marker, "
    "data.eventTrigger + data.eventDirection (catch/throw) for event variants, "
    "data.boundaryInterrupting (true=solid border, false=dashed) for boundary events, "
    "data.subprocessKind for subprocess variants, data.dataKind for data variants."
)

_AI_DIAGRAM_PROMPTS = [
    ("process", "BPMN Process diagrams model the flow of work within a single organisation or system. Use one Pool implicitly (no need to draw it for a single-participant process). Lanes partition responsibilities. Keep flow left-to-right or top-to-bottom; don't mix."),
    ("collaboration", "BPMN Collaboration diagrams model interactions between two or more Pools. Each Pool is a participant. Sequence Flows stay inside their Pool; Message Flows cross between Pools. Black-box pools (no internal flow) represent external participants."),
    ("choreography", "BPMN Choreography diagrams model the message exchange sequence between participants without a controlling pool. Each Choreography Task names two participants and the message between them."),
]


async def up(db: aiosqlite.Connection) -> None:
    """Insert BPMN notation, diagram types, mappings, theme, and AI prompts."""
    now = datetime.now(tz=UTC).isoformat()

    # 1. Insert notation (idempotent)
    n_id, n_name, n_desc, n_order = _NOTATION
    await db.execute(
        "INSERT OR IGNORE INTO notations (id, name, description, display_order) VALUES (?, ?, ?, ?)",
        (n_id, n_name, n_desc, n_order),
    )

    # 2. Insert new diagram types (idempotent)
    for dt_id, dt_name, dt_desc, dt_order in _DIAGRAM_TYPES:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_types (id, name, description, display_order) VALUES (?, ?, ?, ?)",
            (dt_id, dt_name, dt_desc, dt_order),
        )

    # 3. Insert notation-diagram-type mappings (idempotent)
    for dt_id, n_id, is_default in _MAPPINGS:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_type_notations (diagram_type_id, notation_id, is_default) VALUES (?, ?, ?)",
            (dt_id, n_id, is_default),
        )

    # 4. Seed BPMN default theme (upsert)
    await db.execute(
        "INSERT OR REPLACE INTO themes "
        "(id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "bpmn-default",
            "BPMN Default",
            "Camunda-inspired neutral palette mirroring bpmn-js styling",
            "bpmn",
            json.dumps(_BPMN_THEME_CONFIG),
            1,
            "system",
            now,
            now,
        ),
    )

    # 5. Seed AI creation prompts (skip if ai_creation_prompts table is missing — older DBs).
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_creation_prompts'"
    )
    if await cursor.fetchone():
        await db.execute(
            "INSERT OR REPLACE INTO ai_creation_prompts "
            "(id, name, description, layer, notation, diagram_type, prompt_text, "
            " display_order, is_active, created_by, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "bpmn-notation",
                "BPMN Notation Prompt",
                "BPMN 2.0 element catalogue and structural rules",
                "notation",
                "bpmn",
                None,
                _AI_NOTATION_PROMPT,
                100,
                1,
                "system",
                now,
                now,
            ),
        )
        for dt_id, prompt_text in _AI_DIAGRAM_PROMPTS:
            await db.execute(
                "INSERT OR REPLACE INTO ai_creation_prompts "
                "(id, name, description, layer, notation, diagram_type, prompt_text, "
                " display_order, is_active, created_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"bpmn-{dt_id}",
                    f"BPMN {dt_id.replace('_', ' ').title()} Prompt",
                    f"BPMN-specific guidance for {dt_id} diagrams",
                    "diagram_type",
                    "bpmn",
                    dt_id,
                    prompt_text,
                    100,
                    1,
                    "system",
                    now,
                    now,
                ),
            )

    await db.commit()
