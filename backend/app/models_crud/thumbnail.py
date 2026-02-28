"""Thumbnail generation for model gallery cards."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


def generate_svg_from_model_data(data: dict, model_type: str) -> str:
    """Generate a simple SVG representation of model data."""
    nodes = data.get("nodes", [])
    participants = data.get("participants", [])

    width = 400
    height = 250

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#1e293b"/>',
    ]

    if model_type == "sequence" and participants:
        # Draw participants as boxes
        gap = width / (len(participants) + 1)
        for i, p in enumerate(participants):
            x = gap * (i + 1) - 30
            name = p.get("name", "?")[:8]
            svg_parts.append(
                f'<rect x="{x}" y="20" width="60" height="30" rx="4" fill="#334155" stroke="#64748b"/>'
            )
            svg_parts.append(
                f'<text x="{x + 30}" y="40" text-anchor="middle" fill="#94a3b8" font-size="10">{name}</text>'
            )
            svg_parts.append(
                f'<line x1="{x + 30}" y1="50" x2="{x + 30}" y2="{height - 20}" stroke="#475569" stroke-dasharray="4"/>'
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
                f'<rect x="{nx}" y="{ny}" width="70" height="30" rx="4" fill="#334155" stroke="#64748b"/>'
            )
            svg_parts.append(
                f'<text x="{nx + 35}" y="{ny + 19}" text-anchor="middle" fill="#94a3b8" font-size="9">{label}</text>'
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
                    f'<line x1="{src[0]}" y1="{src[1]}" x2="{tgt[0]}" y2="{tgt[1]}" stroke="#475569" stroke-width="1"/>'
                )
    else:
        # Empty model
        svg_parts.append(
            f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" fill="#475569" font-size="14">Empty</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


async def generate_and_store_thumbnail(
    db: aiosqlite.Connection, model_id: str, data: dict, model_type: str
) -> None:
    """Generate PNG thumbnail and store in database.

    Falls back to storing SVG as bytes if cairosvg is not available.
    """
    svg_str = generate_svg_from_model_data(data, model_type)

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
        "INSERT OR REPLACE INTO model_thumbnails (model_id, thumbnail, updated_at) VALUES (?, ?, ?)",
        (model_id, png_bytes, now),
    )
    await db.commit()


async def get_thumbnail(db: aiosqlite.Connection, model_id: str) -> bytes | None:
    """Get stored thumbnail for a model."""
    cursor = await db.execute(
        "SELECT thumbnail FROM model_thumbnails WHERE model_id = ?",
        (model_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else None
