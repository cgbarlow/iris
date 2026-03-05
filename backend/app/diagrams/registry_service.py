"""Service layer for the diagram type/notation registry (ADR-079)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def list_diagram_types(db: aiosqlite.Connection) -> list[dict]:
    """Return all active diagram types with their notation mappings."""
    cursor = await db.execute(
        "SELECT id, name, description, display_order, is_active "
        "FROM diagram_types WHERE is_active = 1 "
        "ORDER BY display_order, name"
    )
    type_rows = await cursor.fetchall()

    result = []
    for r in type_rows:
        dt = {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "display_order": r[3],
            "is_active": bool(r[4]),
            "notations": [],
        }
        # Fetch notation mappings for this type
        map_cursor = await db.execute(
            "SELECT dtn.notation_id, n.name, dtn.is_default "
            "FROM diagram_type_notations dtn "
            "JOIN notations n ON dtn.notation_id = n.id "
            "WHERE dtn.diagram_type_id = ? AND n.is_active = 1 "
            "ORDER BY n.display_order, n.name",
            (r[0],),
        )
        map_rows = await map_cursor.fetchall()
        for mr in map_rows:
            dt["notations"].append({
                "notation_id": mr[0],
                "notation_name": mr[1],
                "is_default": bool(mr[2]),
            })
        result.append(dt)

    return result


async def list_notations(db: aiosqlite.Connection) -> list[dict]:
    """Return all active notations."""
    cursor = await db.execute(
        "SELECT id, name, description, display_order, is_active "
        "FROM notations WHERE is_active = 1 "
        "ORDER BY display_order, name"
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "display_order": r[3],
            "is_active": bool(r[4]),
        }
        for r in rows
    ]


async def get_default_notation(
    db: aiosqlite.Connection, diagram_type_id: str
) -> str | None:
    """Return the default notation ID for a diagram type, or None."""
    cursor = await db.execute(
        "SELECT notation_id FROM diagram_type_notations "
        "WHERE diagram_type_id = ? AND is_default = 1",
        (diagram_type_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else None


async def validate_type_notation(
    db: aiosqlite.Connection, diagram_type_id: str, notation_id: str
) -> bool:
    """Check that a (type, notation) pair exists in the mapping table."""
    cursor = await db.execute(
        "SELECT 1 FROM diagram_type_notations "
        "WHERE diagram_type_id = ? AND notation_id = ?",
        (diagram_type_id, notation_id),
    )
    return await cursor.fetchone() is not None


async def update_diagram_notation(
    db: aiosqlite.Connection, diagram_id: str, notation: str
) -> dict | None:
    """Change a diagram's notation. Returns updated fields or None if not found."""
    # Verify diagram exists
    cursor = await db.execute(
        "SELECT diagram_type FROM diagrams WHERE id = ? AND is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    diagram_type = row[0]

    # Validate the (type, notation) pair
    is_valid = await validate_type_notation(db, diagram_type, notation)
    if not is_valid:
        return {"error": "invalid_pair"}

    await db.execute(
        "UPDATE diagrams SET notation = ? WHERE id = ?",
        (notation, diagram_id),
    )
    await db.commit()
    return {"diagram_id": diagram_id, "notation": notation}
