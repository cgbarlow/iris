"""Service layer for the visual theme system."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def create_theme(
    db: aiosqlite.Connection,
    *,
    name: str,
    description: str | None = None,
    notation: str,
    config: dict[str, object] | None = None,
    is_default: bool = False,
    created_by: str,
) -> dict[str, object]:
    """Create a new theme."""
    theme_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (theme_id, name, description, notation, json.dumps(config or {}), int(is_default), created_by, now, now),
    )
    await db.commit()
    return {
        "id": theme_id,
        "name": name,
        "description": description,
        "notation": notation,
        "config": config or {},
        "is_default": is_default,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }


async def list_themes(
    db: aiosqlite.Connection,
    notation: str | None = None,
) -> list[dict[str, object]]:
    """List all themes, optionally filtered by notation."""
    if notation:
        cursor = await db.execute(
            "SELECT id, name, description, notation, config, is_default, created_by, created_at, updated_at "
            "FROM themes WHERE notation = ? ORDER BY is_default DESC, name ASC",
            (notation,),
        )
    else:
        cursor = await db.execute(
            "SELECT id, name, description, notation, config, is_default, created_by, created_at, updated_at "
            "FROM themes ORDER BY notation ASC, is_default DESC, name ASC"
        )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "notation": r[3],
            "config": json.loads(r[4]) if r[4] else {},
            "is_default": bool(r[5]),
            "created_by": r[6],
            "created_at": r[7],
            "updated_at": r[8],
        }
        for r in rows
    ]


async def get_theme(
    db: aiosqlite.Connection,
    theme_id: str,
) -> dict[str, object] | None:
    """Get a single theme by ID."""
    cursor = await db.execute(
        "SELECT id, name, description, notation, config, is_default, created_by, created_at, updated_at "
        "FROM themes WHERE id = ?",
        (theme_id,),
    )
    r = await cursor.fetchone()
    if r is None:
        return None
    return {
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "notation": r[3],
        "config": json.loads(r[4]) if r[4] else {},
        "is_default": bool(r[5]),
        "created_by": r[6],
        "created_at": r[7],
        "updated_at": r[8],
    }


async def update_theme(
    db: aiosqlite.Connection,
    theme_id: str,
    *,
    name: str,
    description: str | None = None,
    notation: str,
    config: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Update a theme. Returns None if not found."""
    now = datetime.now(tz=UTC).isoformat()
    cursor = await db.execute(
        "UPDATE themes SET name = ?, description = ?, notation = ?, config = ?, updated_at = ? WHERE id = ?",
        (name, description, notation, json.dumps(config or {}), now, theme_id),
    )
    if cursor.rowcount == 0:
        return None
    await db.commit()
    return await get_theme(db, theme_id)


async def delete_theme(
    db: aiosqlite.Connection,
    theme_id: str,
) -> bool:
    """Delete a theme. Returns False if not found or is default."""
    cursor = await db.execute(
        "SELECT is_default FROM themes WHERE id = ?",
        (theme_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0]:
        return False
    await db.execute("DELETE FROM themes WHERE id = ?", (theme_id,))
    await db.commit()
    return True


async def seed_default_themes(db: aiosqlite.Connection) -> None:
    """Seed default themes if none exist, or update existing seed themes with latest config."""
    cursor = await db.execute("SELECT COUNT(*) FROM themes")
    count = (await cursor.fetchone())[0]

    if count > 0:
        # Update existing seed themes with latest config (e.g. new rendering fields)
        pass  # Fall through to upsert logic below

    now = datetime.now(tz=UTC).isoformat()

    # Iris Default UML — clean white/black look (current hardcoded defaults)
    iris_uml_config = {
        "element_defaults": {
            "class": {"bgColor": "#ffffff", "borderColor": "#333333", "fontColor": "#000000"},
        },
        "stereotype_overrides": {},
        "edge_defaults": {},
        "global": {
            "defaultBgColor": "#ffffff",
            "defaultBorderColor": "#333333",
            "defaultFontColor": "#000000",
        },
    }
    await db.execute(
        "INSERT OR REPLACE INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("iris-default-uml", "Iris Default UML", "Clean white look — Iris defaults", "uml",
         json.dumps(iris_uml_config), 1, "system", now, now),
    )

    # Sparx EA Default UML — faithful EA rendering: cream boxes, 1px black border, no radius,
    # no UML icons, red attribute text, italic abstract names
    ea_node = {"bgColor": "#ffffcc", "borderColor": "#000000", "fontColor": "#000000", "borderWidth": 1}
    ea_uml_config = {
        "element_defaults": {
            "class": ea_node,
            "abstract_class": {**ea_node, "italic": True},
            "interface_uml": ea_node,
            "enumeration": ea_node,
            "package_uml": ea_node,
            "component_uml": ea_node,
            "component": ea_node,
            "object": ea_node,
            "use_case": ea_node,
            "node": ea_node,
            "state": ea_node,
            "activity": ea_node,
            "note": {"bgColor": "#ffffff", "borderColor": "#000000", "fontColor": "#000000", "borderWidth": 1},
            "boundary": {"bgColor": "transparent", "borderColor": "#999999", "fontColor": "#333333", "borderWidth": 2, "borderStyle": "dashed"},
            "grouping": {"bgColor": "transparent", "borderColor": "#999999", "fontColor": "#333333", "borderWidth": 2, "borderStyle": "dashed"},
        },
        "stereotype_overrides": {
            "feature": {"bgColor": "#ccffcc"},
            "object": {"bgColor": "#ccffcc"},
            "DataType": {"bgColor": "#ffe0cc"},
            "CodeList": {"bgColor": "#ccccff"},
            "XSDsimpleType": {"bgColor": "#ffccff"},
            "choice": {"bgColor": "#ccffff"},
        },
        "edge_defaults": {
            "association": {"lineColor": "#000000"},
            "generalization": {"lineColor": "#000000"},
            "dependency": {"lineColor": "#000000"},
            "realization": {"lineColor": "#000000"},
            "aggregation": {"lineColor": "#000000"},
            "composition": {"lineColor": "#000000"},
        },
        "global": {
            "defaultBgColor": "#ffffcc",
            "defaultBorderColor": "#000000",
            "defaultFontColor": "#000000",
        },
        "rendering": {
            "hideIcons": True,
            "borderRadius": 0,
            "attrFontColor": "#993333",
            "hideTypeStereotypes": True,
            "abstractBoldOverride": False,
        },
    }
    await db.execute(
        "INSERT OR REPLACE INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("ea-default-uml", "Sparx EA Default UML", "EA default UML class diagram palette with stereotype colours", "uml",
         json.dumps(ea_uml_config), 1, "system", now, now),
    )

    # Iris Default Simple — current defaults
    iris_simple_config = {
        "element_defaults": {},
        "stereotype_overrides": {},
        "edge_defaults": {},
        "global": {
            "defaultBgColor": "#ffffff",
            "defaultBorderColor": "#666666",
            "defaultFontColor": "#000000",
        },
    }
    await db.execute(
        "INSERT OR REPLACE INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("iris-default-simple", "Iris Default Simple", "Clean simple look", "simple",
         json.dumps(iris_simple_config), 1, "system", now, now),
    )

    # C4 Default — canonical hybrid colours (c4model.com)
    c4_default_config = {
        "element_defaults": {
            "person":                    {"bgColor": "#f0fdf4", "borderColor": "#2d8a4e", "fontColor": "#166534", "borderWidth": 2},
            "software_system":           {"bgColor": "#eff6ff", "borderColor": "#1168bd", "fontColor": "#1e40af", "borderWidth": 2},
            "software_system_external":  {"bgColor": "#fef2f2", "borderColor": "#c0392b", "fontColor": "#991b1b", "borderWidth": 2},
            "container":                 {"bgColor": "#f0f7ff", "borderColor": "#438dd5", "fontColor": "#1e40af", "borderWidth": 2},
            "c4_component":              {"bgColor": "#f8fbff", "borderColor": "#85bbf0", "fontColor": "#1e40af", "borderWidth": 2},
            "code_element":              {"bgColor": "#fafcff", "borderColor": "#93c5fd", "fontColor": "#1e40af", "borderWidth": 2},
            "deployment_node":           {"bgColor": "#ffffff", "borderColor": "#438dd5", "fontColor": "#1e40af", "borderWidth": 2, "borderStyle": "dashed"},
            "infrastructure_node":       {"bgColor": "#ffffff", "borderColor": "#6b7280", "fontColor": "#555555", "borderWidth": 2, "borderStyle": "dashed"},
            "container_instance":        {"bgColor": "#f0f7ff", "borderColor": "#438dd5", "fontColor": "#1e40af", "borderWidth": 2, "borderStyle": "dashed"},
            "boundary":                  {"bgColor": "transparent", "borderColor": "#999999", "fontColor": "#333333", "borderWidth": 2, "borderStyle": "dashed"},
        },
        "stereotype_overrides": {},
        "edge_defaults": {"c4_relationship": {"lineColor": "#666666"}},
        "global": {"defaultBgColor": "#eff6ff", "defaultBorderColor": "#1168bd", "defaultFontColor": "#1a1a2e"},
    }
    await db.execute(
        "INSERT OR REPLACE INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("c4-default", "C4 Default", "Canonical C4 hybrid colours — c4model.com", "c4",
         json.dumps(c4_default_config), 1, "system", now, now),
    )

    # ArchiMate Default — canonical ArchiMate layer colours
    archimate_config = {
        "element_defaults": {
            "business_actor":      {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_role":       {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_process":    {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_function":   {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_service":    {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_object":     {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_event":      {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_interaction": {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_collaboration": {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "business_interface":  {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "contract":            {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "product":             {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "representation":      {"bgColor": "#ffffb5", "borderColor": "#c9a800", "fontColor": "#333333", "borderWidth": 1},
            "application_component": {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "application_service":   {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "application_function":  {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "application_interface": {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "application_process":   {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "application_interaction": {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "application_event":     {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "application_collaboration": {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "data_object":           {"bgColor": "#b5ffff", "borderColor": "#00b5b5", "fontColor": "#333333", "borderWidth": 1},
            "technology_node":       {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "technology_device":     {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "technology_service":    {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "technology_function":   {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "technology_interface":  {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "technology_process":    {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "technology_interaction": {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "technology_collaboration": {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "system_software":       {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "artifact":              {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "communication_network": {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "path":                  {"bgColor": "#c9e7b7", "borderColor": "#5b9a3c", "fontColor": "#333333", "borderWidth": 1},
            "motivation_stakeholder": {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_driver":      {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_goal":        {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_requirement":  {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_principle":    {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_constraint":   {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_assessment":   {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_value":        {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "motivation_meaning":      {"bgColor": "#ccccff", "borderColor": "#8080ff", "fontColor": "#333333", "borderWidth": 1},
            "strategy_capability":     {"bgColor": "#f5deaa", "borderColor": "#c49a44", "fontColor": "#333333", "borderWidth": 1},
            "strategy_resource":       {"bgColor": "#f5deaa", "borderColor": "#c49a44", "fontColor": "#333333", "borderWidth": 1},
            "strategy_course_of_action": {"bgColor": "#f5deaa", "borderColor": "#c49a44", "fontColor": "#333333", "borderWidth": 1},
            "strategy_value_stream":   {"bgColor": "#f5deaa", "borderColor": "#c49a44", "fontColor": "#333333", "borderWidth": 1},
            "grouping":                {"bgColor": "#e0e0e0", "borderColor": "#999999", "fontColor": "#333333", "borderWidth": 1},
        },
        "stereotype_overrides": {},
        "edge_defaults": {},
        "global": {
            "defaultBgColor": "#ffffff",
            "defaultBorderColor": "#999999",
            "defaultFontColor": "#333333",
        },
    }
    await db.execute(
        "INSERT OR REPLACE INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("archimate-default", "ArchiMate Default", "Canonical ArchiMate layer colours", "archimate",
         json.dumps(archimate_config), 1, "system", now, now),
    )

    await db.commit()
