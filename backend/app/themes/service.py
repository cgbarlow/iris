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
    """Seed default themes if none exist."""
    cursor = await db.execute("SELECT COUNT(*) FROM themes")
    count = (await cursor.fetchone())[0]
    if count > 0:
        return

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
        "INSERT INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("iris-default-uml", "Iris Default UML", "Clean white look — Iris defaults", "uml",
         json.dumps(iris_uml_config), 1, "system", now, now),
    )

    # Sparx EA Default UML — EA's pale yellow class boxes + stereotype colours
    ea_uml_config = {
        "element_defaults": {
            "class": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "abstract_class": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "interface_uml": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "enumeration": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "package_uml": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "component_uml": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "object": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "use_case": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "node": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "state": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
            "activity": {"bgColor": "#ffffcc", "borderColor": "#000080", "fontColor": "#000000"},
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
            "association": {"lineColor": "#000080"},
            "generalization": {"lineColor": "#000080"},
            "dependency": {"lineColor": "#000080"},
            "realization": {"lineColor": "#000080"},
            "aggregation": {"lineColor": "#000080"},
            "composition": {"lineColor": "#000080"},
        },
        "global": {
            "defaultBgColor": "#ffffcc",
            "defaultBorderColor": "#000080",
            "defaultFontColor": "#000000",
        },
    }
    await db.execute(
        "INSERT INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
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
        "INSERT INTO themes (id, name, description, notation, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("iris-default-simple", "Iris Default Simple", "Clean simple look", "simple",
         json.dumps(iris_simple_config), 1, "system", now, now),
    )

    await db.commit()
