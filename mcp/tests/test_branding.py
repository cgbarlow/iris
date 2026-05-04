"""Branding / favicon coverage for iris-mcp."""

from __future__ import annotations

import base64

from iris_mcp.branding import ICON_SVG, iris_icon


class TestIrisIcon:
    def test_data_url_decodes_back_to_svg(self) -> None:
        icon = iris_icon()
        assert icon.src.startswith("data:image/svg+xml;base64,")
        encoded = icon.src.split(",", 1)[1]
        assert base64.b64decode(encoded) == ICON_SVG

    def test_mime_and_sizes(self) -> None:
        icon = iris_icon()
        assert icon.mimeType == "image/svg+xml"
        assert icon.sizes == ["any"]

    def test_svg_is_valid_minimal_xml(self) -> None:
        # Cheap structural check — full XML parse would pull a dep.
        assert ICON_SVG.startswith(b"<svg")
        assert ICON_SVG.endswith(b"</svg>")
        # Iris brand colours present (sky blue ring, dark pupil).
        assert b"#0ea5e9" in ICON_SVG
        assert b"#0c1022" in ICON_SVG
