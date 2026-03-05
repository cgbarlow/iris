"""Coordinate and colour conversion for SparxEA imports."""

from __future__ import annotations


def bgr_to_rgb(bgr_int: int) -> str:
    """Convert EA BGR decimal integer to CSS hex colour string.

    EA stores colours as decimal BGR integers.
    Returns '#FFFFFF' for negative values (EA's default colour marker).
    """
    if bgr_int < 0:
        return "#FFFFFF"
    b = (bgr_int >> 16) & 0xFF
    g = (bgr_int >> 8) & 0xFF
    r = bgr_int & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}"


def parse_object_style(style_str: str | None) -> dict[str, int]:
    """Parse EA diagram object style string like 'BCol=X;BFol=Y;LCol=Z;...' into a dict.

    Values are integers. Keys commonly include BCol (background), LCol (line),
    LWth (line width), FCol (font colour).
    """
    result: dict[str, int] = {}
    if not style_str:
        return result
    for part in style_str.split(";"):
        if "=" in part:
            key, _, val = part.partition("=")
            key = key.strip()
            val = val.strip()
            try:
                result[key] = int(val)
            except ValueError:
                pass
    return result


def build_node_visual(
    object_style: str | None,
    backcolor: int | None,
    fontcolor: int | None,
    bordercolor: int | None,
    border_width: int | None,
) -> dict[str, object] | None:
    """Build a NodeVisualOverrides dict from EA element/object style data.

    Returns None when all values are defaults (-1 or None).
    Priority: object_style (per-diagram-placement) > element-level colors.
    """
    style = parse_object_style(object_style)
    visual: dict[str, object] = {}

    # Object style overrides (per-placement on diagram)
    bg = style.get("BCol", -1)
    lc = style.get("LCol", -1)
    fc = style.get("FCol", -1)
    lw = style.get("LWth", -1)

    # Fall back to element-level colors
    if bg == -1 and backcolor is not None and backcolor >= 0:
        bg = backcolor
    if lc == -1 and bordercolor is not None and bordercolor >= 0:
        lc = bordercolor
    if fc == -1 and fontcolor is not None and fontcolor >= 0:
        fc = fontcolor
    if lw == -1 and border_width is not None and border_width > 0:
        lw = border_width

    if bg >= 0:
        visual["bgColor"] = bgr_to_rgb(bg)
    if lc >= 0:
        visual["borderColor"] = bgr_to_rgb(lc)
    if fc >= 0:
        visual["fontColor"] = bgr_to_rgb(fc)
    if lw > 0:
        visual["borderWidth"] = lw

    return visual if visual else None


def build_edge_visual(
    line_color: int | None,
    is_bold: int | None,
    line_style: int | None,
) -> dict[str, object] | None:
    """Build an EdgeVisualOverrides dict from EA connector data.

    Returns None when all values are defaults.
    """
    visual: dict[str, object] = {}

    if line_color is not None and line_color >= 0:
        visual["lineColor"] = bgr_to_rgb(line_color)
    if is_bold and is_bold > 0:
        visual["lineWidth"] = 2
    # EA line styles: 0=solid, 1=dashed, 2=dotted, 3=dash-dot, 4=dash-dot-dot
    if line_style is not None and line_style > 0:
        dash_map = {1: "8 4", 2: "2 4", 3: "8 4 2 4", 4: "8 4 2 4 2 4"}
        da = dash_map.get(line_style)
        if da:
            visual["dashArray"] = da

    return visual if visual else None


def ea_rect_to_position(
    rect_left: int, rect_right: int, rect_top: int, rect_bottom: int
) -> dict[str, int]:
    """Convert EA diagram object rectangle to canvas position and size.

    EA coordinate system:
    - X: left-to-right (same as screen), positive values.
    - Y: all negative, where RectTop is less negative (closer to 0) = higher
      on screen, and RectBottom is more negative = lower on screen.
    - Height = RectTop - RectBottom (always positive since Top > Bottom).

    To convert to screen coordinates (Y increases downward):
    - screen_y = -RectTop  (negate to flip; top of element)

    Returns dict with x, y, width, height suitable for canvas rendering.
    """
    x = rect_left
    y = -rect_top  # Negate: EA top (less negative) becomes smaller screen Y
    width = abs(rect_right - rect_left)
    height = abs(rect_top - rect_bottom)
    return {
        "x": x,
        "y": y,
        "width": max(width, 100),
        "height": max(height, 60),
    }
