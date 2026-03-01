"""Thumbnail generation for model gallery cards."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

THEME_COLORS: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#ffffff",
        "node_fill": "#f1f5f9",
        "node_stroke": "#6b7280",
        "text_fill": "#475569",
        "edge_stroke": "#94a3b8",
        "empty_fill": "#94a3b8",
    },
    "dark": {
        "bg": "#1e293b",
        "node_fill": "#334155",
        "node_stroke": "#64748b",
        "text_fill": "#94a3b8",
        "edge_stroke": "#475569",
        "empty_fill": "#475569",
    },
    "high-contrast": {
        "bg": "#000000",
        "node_fill": "#1a1a1a",
        "node_stroke": "#ffffff",
        "text_fill": "#ffffff",
        "edge_stroke": "#cccccc",
        "empty_fill": "#cccccc",
    },
}

VALID_THEMES = frozenset(THEME_COLORS.keys())


def generate_svg_from_model_data(
    data: dict, model_type: str, theme: str = "dark",
) -> str:
    """Generate a simple SVG representation of model data."""
    colors = THEME_COLORS.get(theme, THEME_COLORS["dark"])
    nodes = data.get("nodes", [])
    participants = data.get("participants", [])

    width = 400
    height = 250

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{colors["bg"]}"/>',
    ]

    if model_type == "sequence" and participants:
        # Draw participants as boxes
        gap = width / (len(participants) + 1)
        for i, p in enumerate(participants):
            x = gap * (i + 1) - 30
            name = p.get("name", "?")[:8]
            svg_parts.append(
                f'<rect x="{x}" y="20" width="60" height="30" rx="4" '
                f'fill="{colors["node_fill"]}" stroke="{colors["node_stroke"]}"/>'
            )
            svg_parts.append(
                f'<text x="{x + 30}" y="40" text-anchor="middle" '
                f'fill="{colors["text_fill"]}" font-size="10">{name}</text>'
            )
            svg_parts.append(
                f'<line x1="{x + 30}" y1="50" x2="{x + 30}" y2="{height - 20}" '
                f'stroke="{colors["edge_stroke"]}" stroke-dasharray="4"/>'
            )
    elif nodes:
        # Draw nodes as rounded boxes with connections
        for i, node in enumerate(nodes[:12]):  # Max 12 nodes for thumbnail
            pos = node.get("position", {})
            # Scale positions to fit thumbnail
            nx = min(max(20, (pos.get("x", i * 80) % 350) + 20), width - 80)
            ny = min(max(20, (pos.get("y", i * 60) % 200) + 20), height - 40)
            label = node.get("data", {}).get("label", "?")[:10]
            svg_parts.append(
                f'<rect x="{nx}" y="{ny}" width="70" height="30" rx="4" '
                f'fill="{colors["node_fill"]}" stroke="{colors["node_stroke"]}"/>'
            )
            svg_parts.append(
                f'<text x="{nx + 35}" y="{ny + 19}" text-anchor="middle" '
                f'fill="{colors["text_fill"]}" font-size="9">{label}</text>'
            )

        # Draw edges
        edges = data.get("edges", [])
        node_positions = {}
        for node in nodes[:12]:
            pos = node.get("position", {})
            nx = min(max(20, (pos.get("x", 0) % 350) + 20), width - 80)
            ny = min(max(20, (pos.get("y", 0) % 200) + 20), height - 40)
            node_positions[node.get("id", "")] = (nx + 35, ny + 30)

        for edge in edges[:15]:
            src = node_positions.get(edge.get("source", ""))
            tgt = node_positions.get(edge.get("target", ""))
            if src and tgt:
                svg_parts.append(
                    f'<line x1="{src[0]}" y1="{src[1]}" x2="{tgt[0]}" y2="{tgt[1]}" '
                    f'stroke="{colors["edge_stroke"]}" stroke-width="1"/>'
                )
    else:
        # Empty model
        svg_parts.append(
            f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" '
            f'fill="{colors["empty_fill"]}" font-size="14">Empty</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


async def generate_and_store_thumbnail(
    db: aiosqlite.Connection,
    model_id: str,
    data: dict,
    model_type: str,
    theme: str = "dark",
) -> None:
    """Generate PNG thumbnail and store in database.

    Falls back to storing SVG as bytes if cairosvg is not available.
    """
    svg_str = generate_svg_from_model_data(data, model_type, theme=theme)

    try:
        import cairosvg

        png_bytes = cairosvg.svg2png(
            bytestring=svg_str.encode(), output_width=400, output_height=250
        )
    except ImportError:
        # cairosvg not installed -- store SVG bytes as fallback
        png_bytes = svg_str.encode()

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT OR REPLACE INTO model_thumbnails "
        "(model_id, theme, thumbnail, updated_at) VALUES (?, ?, ?, ?)",
        (model_id, theme, png_bytes, now),
    )
    await db.commit()


async def get_thumbnail(
    db: aiosqlite.Connection, model_id: str, theme: str = "dark",
) -> bytes | None:
    """Get stored thumbnail for a model."""
    cursor = await db.execute(
        "SELECT thumbnail FROM model_thumbnails "
        "WHERE model_id = ? AND theme = ?",
        (model_id, theme),
    )
    row = await cursor.fetchone()
    return row[0] if row else None


async def regenerate_all_thumbnails(db: aiosqlite.Connection) -> int:
    """Regenerate PNG thumbnails for all non-deleted models in all themes.

    Called during startup to ensure all models have up-to-date PNG thumbnails,
    including models created before the thumbnail migration and models with
    stale SVG-byte thumbnails from when cairosvg was not installed.

    Returns the number of models processed.
    """
    cursor = await db.execute(
        "SELECT m.id, m.model_type, mv.data "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
        "WHERE m.is_deleted = 0"
    )
    rows = await cursor.fetchall()

    for row in rows:
        model_id = row[0]
        model_type = row[1]
        data = json.loads(row[2]) if row[2] else {}
        for theme in VALID_THEMES:
            await generate_and_store_thumbnail(
                db, model_id, data, model_type, theme=theme,
            )

    return len(rows)
