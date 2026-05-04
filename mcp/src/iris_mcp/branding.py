"""Iris-mcp branding — the favicon shown in MCP client connector lists.

Mirrors `frontend/src/lib/assets/favicon.svg` (the Iris eye favicon
introduced in v4.2.0). Inlined as a Python constant rather than a
package data file because the SVG is 700-odd bytes — base64-encoded
into a data URL it embeds directly into the MCP `initialize` response,
which is what every client uses to render the icon.
"""

from __future__ import annotations

import base64

from mcp import types

# Source: frontend/src/lib/assets/favicon.svg. Keep these two in sync —
# the iris monorepo has no shared assets directory yet.
ICON_SVG: bytes = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
    b'width="64" height="64" fill="none" stroke="currentColor" '
    b'stroke-width="4" stroke-linecap="round" stroke-linejoin="round" '
    b'role="img" aria-label="Iris"><title>Iris</title>'
    b'<path d="M4 32c7-13 17-20 28-20s21 7 28 20c-7 13-17 20-28 20'
    b'S11 45 4 32Z" fill="#e0f2fe"/>'
    b'<circle cx="32" cy="32" r="12" fill="#0ea5e9" stroke="#0c4a6e" '
    b'stroke-width="2"/>'
    b'<circle cx="32" cy="32" r="5" fill="#0c1022" stroke="none"/>'
    b'<circle cx="28" cy="28" r="2" fill="#ffffff" stroke="none"/></svg>'
)


def iris_icon() -> types.Icon:
    """Return the Iris favicon as an MCP Icon (data URL, scalable)."""
    encoded = base64.b64encode(ICON_SVG).decode("ascii")
    return types.Icon(
        src=f"data:image/svg+xml;base64,{encoded}",
        mimeType="image/svg+xml",
        sizes=["any"],  # SVG is scalable; "any" tells clients it has no fixed size.
    )
