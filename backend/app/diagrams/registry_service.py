"""Service layer for the diagram type/notation registry (ADR-079)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def list_diagram_types(db: DatabasePort) -> list[dict]:
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


async def list_notations(db: DatabasePort) -> list[dict]:
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
    db: DatabasePort, diagram_type_id: str
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
    db: DatabasePort, diagram_type_id: str, notation_id: str
) -> bool:
    """Check that a (type, notation) pair exists in the mapping table."""
    cursor = await db.execute(
        "SELECT 1 FROM diagram_type_notations "
        "WHERE diagram_type_id = ? AND notation_id = ?",
        (diagram_type_id, notation_id),
    )
    return await cursor.fetchone() is not None


async def list_creation_catalogue(db: DatabasePort) -> list[dict]:
    """Return the (notation, diagram_type) pairs AI creation can produce (ADR-132).

    A pair is creatable when:
      - the pair exists in diagram_type_notations as the default for that
        diagram type, and both sides are active; AND
      - an active `notation`-layer prompt exists for the notation; AND
      - either the notation is `doview` (DoView's own prompt branches
        internally on diagram_type), or an active `diagram_type`-layer
        prompt exists for the diagram type.

    DoView's multiple default pairs are collapsed into one entry with
    `diagram_type=None` and `requires_diagram_type=False` so the frontend
    hides the diagram-type selector for DoView (preserving ADR-094 UX).

    Empty-catalogue fallback: if no active prompts exist at all (greenfield
    install before migrations run), returns a synthesised DoView entry so
    the UI does not appear broken.
    """
    cursor = await db.execute(
        "SELECT DISTINCT "
        "  n.id, n.name, dt.id, dt.name, n.display_order, dt.display_order "
        "FROM diagram_type_notations dtn "
        "JOIN notations n ON dtn.notation_id = n.id "
        "JOIN diagram_types dt ON dtn.diagram_type_id = dt.id "
        "WHERE dtn.is_default = 1 AND n.is_active = 1 AND dt.is_active = 1 "
        "  AND EXISTS ("
        "    SELECT 1 FROM ai_creation_prompts "
        "    WHERE layer = 'notation' AND notation = n.id AND is_active = 1"
        "  ) "
        "  AND ("
        "    n.id = 'doview' OR EXISTS ("
        "      SELECT 1 FROM ai_creation_prompts "
        "      WHERE layer = 'diagram_type' AND diagram_type = dt.id AND is_active = 1"
        "    )"
        "  ) "
        "ORDER BY n.display_order, dt.display_order"
    )
    rows = await cursor.fetchall()

    if not rows:
        # Greenfield fallback — never leave the UI empty.
        return [{
            "notation": "doview",
            "notation_label": "DoView",
            "diagram_type": None,
            "diagram_type_label": None,
            "requires_diagram_type": False,
        }]

    items: list[dict] = []
    doview_seen = False
    for r in rows:
        notation_id, notation_label, dt_id, dt_label, _n_order, _dt_order = r
        if notation_id == "doview":
            if doview_seen:
                continue  # collapse multiple doview rows into one
            doview_seen = True
            items.append({
                "notation": "doview",
                "notation_label": notation_label,
                "diagram_type": None,
                "diagram_type_label": None,
                "requires_diagram_type": False,
            })
        else:
            items.append({
                "notation": notation_id,
                "notation_label": notation_label,
                "diagram_type": dt_id,
                "diagram_type_label": dt_label,
                "requires_diagram_type": True,
            })
    return items


async def update_diagram_notation(
    db: DatabasePort, diagram_id: str, notation: str
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
