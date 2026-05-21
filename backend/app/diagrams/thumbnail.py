"""Thumbnail generation for diagram gallery cards."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from html import escape as html_escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite
    from app.db.adapter import DatabasePort

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


_MARKDOWN_DIAGRAM_TYPES = frozenset(
    {"smart_markdown", "text", "dynamic_list"},
)

# Smart Markdown token regex (matches the resolver's in
# `backend/app/diagrams/smart_markdown.py`) so we can strip tokens
# from the thumbnail preview without showing raw `{{element:...}}`.
_SMART_MD_TOKEN_RE = re.compile(
    r"\{\{(?:element|package|diagram|set|collection|image):"
    r"[^:}]+(?::[^}]+)?\}\}",
)


def _markdown_preview_lines(data: dict, diagram_type: str) -> list[str]:
    """Pick a few representative source lines for the thumbnail.

    Per ADR-205 / ADR-206 / ADR-186 each markdown-notation type stores
    its content in a different field:

      smart_markdown → ``data.markdown_source`` (with `{{...}}` tokens)
      text           → ``data.content``         (raw markdown)
      dynamic_list   → ``data.source`` + ``data.show_description``
                       (no markdown body; the thumbnail shows the
                       source mode + description toggle instead)
    """
    if diagram_type == "smart_markdown":
        src = str(data.get("markdown_source") or "")
        # Strip the resolver's tokens so the thumbnail shows plain text.
        src = _SMART_MD_TOKEN_RE.sub("[…]", src)
    elif diagram_type == "text":
        src = str(data.get("content") or "")
    elif diagram_type == "dynamic_list":
        mode = str(data.get("source") or "?")
        show_desc = bool(data.get("show_description"))
        return [
            "# Dynamic list",
            "",
            f"source: {mode}",
            f"show description: {'yes' if show_desc else 'no'}",
        ]
    else:
        src = ""
    # Take first 6 non-trailing-blank lines, truncate each to 60 chars.
    raw_lines = src.splitlines()
    out: list[str] = []
    for line in raw_lines:
        if len(out) == 0 and not line.strip():
            continue  # skip leading blank lines
        out.append(line[:60])
        if len(out) >= 6:
            break
    return out or ["(empty)"]


def _generate_markdown_preview_svg(
    data: dict, diagram_type: str, theme: str = "dark",
) -> str:
    """Render a plain-text SVG preview of a markdown-notation diagram
    (ADR-209 follow-up for issue #205). Pure ``<text>`` elements so
    cairosvg can rasterise reliably — no foreignObject, no HTML."""
    colors = THEME_COLORS.get(theme, THEME_COLORS["dark"])
    width, height = 400, 250
    lines = _markdown_preview_lines(data, diagram_type)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{colors["bg"]}"/>',
        f'<rect x="8" y="8" width="{width - 16}" height="{height - 16}" '
        f'rx="6" fill="{colors["node_fill"]}" '
        f'stroke="{colors["node_stroke"]}" stroke-width="1"/>',
    ]

    # Top-of-content y-coord; first heading rendered larger.
    y = 36
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        is_heading_1 = i == 0 and stripped.startswith("# ")
        is_heading_n = stripped.startswith(("# ", "## ", "### "))
        font_size = 18 if is_heading_1 else (15 if is_heading_n else 12)
        # Render heading text without leading `#` characters for cleaner tile.
        display = stripped.lstrip("# ").strip() if is_heading_n else line
        if not display:
            y += font_size + 4
            continue
        svg_parts.append(
            f'<text x="20" y="{y}" font-family="ui-monospace,monospace" '
            f'font-size="{font_size}" fill="{colors["text_fill"]}">'
            f'{html_escape(display)}</text>',
        )
        y += font_size + 6
        if y > height - 16:
            break

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_svg_from_diagram_data(
    data: dict, diagram_type: str, theme: str = "dark",
) -> str:
    """Generate a simple SVG representation of diagram data.

    v6.17.6 (issue #205 item 3): markdown-notation diagram types
    (smart_markdown / text / dynamic_list) get a plain-text preview
    instead of the empty "Empty" placeholder, so the views gallery
    shows a meaningful tile.
    """
    # ADR-209 follow-up: markdown views get a text-preview tile.
    if diagram_type in _MARKDOWN_DIAGRAM_TYPES:
        return _generate_markdown_preview_svg(data, diagram_type, theme)

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

    if diagram_type == "sequence" and participants:
        # Draw participants as boxes
        gap = width / (len(participants) + 1)
        for i, p in enumerate(participants):
            x = gap * (i + 1) - 30
            name = html_escape(p.get("name", "?")[:8])
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
            label = html_escape(node.get("data", {}).get("label", "?")[:10])
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
        # Empty diagram
        svg_parts.append(
            f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" '
            f'fill="{colors["empty_fill"]}" font-size="14">Empty</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


async def generate_and_store_thumbnail(
    db: DatabasePort,
    diagram_id: str,
    data: dict,
    diagram_type: str,
    theme: str = "dark",
) -> None:
    """Generate PNG thumbnail and store in database.

    Falls back to storing SVG as bytes if cairosvg is not available.
    """
    svg_str = generate_svg_from_diagram_data(data, diagram_type, theme=theme)

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
        "INSERT OR REPLACE INTO diagram_thumbnails "
        "(diagram_id, theme, thumbnail, updated_at) VALUES (?, ?, ?, ?)",
        (diagram_id, theme, png_bytes, now),
    )
    await db.commit()


async def get_thumbnail(
    db: DatabasePort, diagram_id: str, theme: str = "dark",
) -> bytes | None:
    """Get stored thumbnail for a diagram.

    ADR-209 (v6.17.4): markdown-notation diagrams have no graphical
    representation to thumbnail, so they previously returned None and
    the gallery showed an empty tile. Now: if no canonical thumbnail
    exists, fall back to the first ``entity_images`` attachment so
    users can pick their own thumbnail by attaching an image to the
    view's Details → Images section.
    """
    cursor = await db.execute(
        "SELECT thumbnail FROM diagram_thumbnails "
        "WHERE diagram_id = ? AND theme = ?",
        (diagram_id, theme),
    )
    row = await cursor.fetchone()
    if row is not None and row[0]:
        return row[0]

    # Fall back to attached image.
    cursor = await db.execute(
        "SELECT i.bytes FROM entity_images ei "
        "JOIN images i ON ei.image_id = i.id "
        "WHERE ei.entity_type = 'diagram' AND ei.entity_id = ? "
        "ORDER BY ei.display_order, ei.created_at LIMIT 1",
        (diagram_id,),
    )
    arow = await cursor.fetchone()
    if arow is not None and arow[0]:
        raw = arow[0]
        return bytes(raw) if not isinstance(raw, bytes) else raw
    return None


async def regenerate_all_thumbnails(db: DatabasePort) -> int:
    """Regenerate PNG thumbnails for all non-deleted diagrams in all themes.

    Called during startup to ensure all diagrams have up-to-date PNG thumbnails,
    including diagrams created before the thumbnail migration and diagrams with
    stale SVG-byte thumbnails from when cairosvg was not installed.

    Returns the number of diagrams processed.
    """
    cursor = await db.execute(
        "SELECT d.id, d.diagram_type, dv.data "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0"
    )
    rows = await cursor.fetchall()

    for row in rows:
        diagram_id = row[0]
        diagram_type = row[1]
        data = json.loads(row[2]) if row[2] else {}
        for theme in VALID_THEMES:
            await generate_and_store_thumbnail(
                db, diagram_id, data, diagram_type, theme=theme,
            )

    return len(rows)
