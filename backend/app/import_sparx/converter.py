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
