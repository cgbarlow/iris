"""Migration 027: DoView notation, diagram types, and theme (ADR-094).

Adds DoView as a fifth notation with its own diagram types (outcomes_map, overview),
notation-diagram-type mappings, and seeds the DoView default theme.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


_NOTATION = ("doview", "DoView", "DoView outcomes-based theory of change notation", 4)

_DIAGRAM_TYPES = [
    ("outcomes_map", "Outcomes Map", "Left-to-right causal outcomes flow", 7),
    ("overview",     "Overview",     "High-level overview with navigation tiles", 8),
]

_MAPPINGS = [
    ("outcomes_map", "doview", 1),
    ("overview",     "doview", 1),
    ("free_form",    "doview", 0),
]

_DOVIEW_THEME_CONFIG = {
    "element_defaults": {
        "outcome_box":      {"bgColor": "#FFF2CC", "borderColor": "#D6B656", "fontColor": "#333333", "borderWidth": 2},
        "final_outcome":    {"bgColor": "#FFFFFF", "borderColor": "#CCCCCC", "fontColor": "#333333", "borderWidth": 2},
        "overview_tile":    {"bgColor": "#DAE8FC", "borderColor": "#6C8EBF", "fontColor": "#333333", "borderWidth": 2},
        "source_reference": {"bgColor": "#F5F5F5", "borderColor": "#666666", "fontColor": "#333333", "borderWidth": 1},
    },
    "stereotype_overrides": {
        "page_yellow":   {"bgColor": "#FFF2CC", "borderColor": "#D6B656"},
        "page_pink":     {"bgColor": "#F8CECC", "borderColor": "#B85450"},
        "page_blue":     {"bgColor": "#DAE8FC", "borderColor": "#6C8EBF"},
        "page_green":    {"bgColor": "#D5E8D4", "borderColor": "#82B366"},
        "page_beige":    {"bgColor": "#FFF4E6", "borderColor": "#D4A574"},
        "page_lavender": {"bgColor": "#E1D5E7", "borderColor": "#9673A6"},
        "page_peach":    {"bgColor": "#FFE6CC", "borderColor": "#D79B00"},
        "page_cyan":     {"bgColor": "#D4E1F5", "borderColor": "#7EA6E0"},
        "page_grey":     {"bgColor": "#F5F5F5", "borderColor": "#666666"},
        "page_white":    {"bgColor": "#FFFFFF", "borderColor": "#CCCCCC"},
    },
    "edge_defaults": {
        "causal_link": {"lineColor": "#C8C8C8", "lineWidth": 2},
    },
    "global": {
        "defaultBgColor": "#FFF2CC",
        "defaultBorderColor": "#D6B656",
        "defaultFontColor": "#333333",
    },
    "rendering": {
        "hideIcons": False,
        "borderRadius": 4,
        "wrapLabels": True,
        "textAlign": "center",
    },
}


async def up(db: aiosqlite.Connection) -> None:
    """Insert DoView notation, diagram types, mappings, and seed theme."""
    now = datetime.now(tz=UTC).isoformat()

    # 1. Insert notation (idempotent)
    n_id, n_name, n_desc, n_order = _NOTATION
    await db.execute(
        "INSERT OR IGNORE INTO notations (id, name, description, display_order) VALUES (?, ?, ?, ?)",
        (n_id, n_name, n_desc, n_order),
    )

    # 2. Insert diagram types (idempotent)
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

    # 4. Seed DoView default theme (upsert)
    await db.execute(
        "INSERT OR REPLACE INTO themes "
        "(id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "doview-default",
            "DoView Default",
            "Official DoView 10-color palette — DoViewPlanning.org",
            "doview",
            json.dumps(_DOVIEW_THEME_CONFIG),
            1,
            "system",
            now,
            now,
        ),
    )

    await db.commit()
