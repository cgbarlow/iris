"""Tests for EA visual conversion utilities (ADR-084)."""

import pytest

from app.import_sparx.converter import (
    bgr_to_rgb,
    build_edge_visual,
    build_node_visual,
    parse_object_style,
)


class TestParseObjectStyle:
    def test_empty_string(self):
        assert parse_object_style("") == {}

    def test_none(self):
        assert parse_object_style(None) == {}

    def test_single_pair(self):
        assert parse_object_style("BCol=255") == {"BCol": 255}

    def test_multiple_pairs(self):
        result = parse_object_style("BCol=255;LCol=128;LWth=2")
        assert result == {"BCol": 255, "LCol": 128, "LWth": 2}

    def test_default_values(self):
        result = parse_object_style("BCol=-1;LCol=-1")
        assert result == {"BCol": -1, "LCol": -1}

    def test_non_integer_value_skipped(self):
        result = parse_object_style("BCol=abc;LCol=128")
        assert result == {"LCol": 128}

    def test_trailing_semicolon(self):
        result = parse_object_style("BCol=255;")
        assert result == {"BCol": 255}


class TestBuildNodeVisual:
    def test_all_defaults_returns_none(self):
        assert build_node_visual(None, -1, -1, -1, None) is None

    def test_all_none_returns_none(self):
        assert build_node_visual(None, None, None, None, None) is None

    def test_element_backcolor(self):
        # Red in BGR = 0x0000FF = 255
        result = build_node_visual(None, 255, None, None, None)
        assert result == {"bgColor": "#ff0000"}

    def test_element_fontcolor(self):
        result = build_node_visual(None, None, 0, None, None)
        assert result == {"fontColor": "#000000"}

    def test_element_bordercolor(self):
        # Blue in BGR = 0xFF0000 = 16711680
        result = build_node_visual(None, None, None, 16711680, None)
        assert result == {"borderColor": "#0000ff"}

    def test_element_border_width(self):
        result = build_node_visual(None, None, None, None, 3)
        assert result == {"borderWidth": 3}

    def test_object_style_overrides_element(self):
        # Object style says green background (BGR 0x00FF00 = 65280)
        # Element says red background (255)
        result = build_node_visual("BCol=65280", 255, None, None, None)
        assert result is not None
        assert result["bgColor"] == "#00ff00"  # Object style wins

    def test_object_style_defaults_fall_through(self):
        # Object style has BCol=-1, element has backcolor
        result = build_node_visual("BCol=-1", 255, None, None, None)
        assert result is not None
        assert result["bgColor"] == "#ff0000"  # Falls through to element

    def test_combined_styles(self):
        result = build_node_visual(
            "BCol=65280;LCol=128",
            None, 0, None, 2,
        )
        assert result is not None
        assert result["bgColor"] == "#00ff00"
        assert result["borderColor"] == bgr_to_rgb(128)
        assert result["fontColor"] == "#000000"
        assert result["borderWidth"] == 2


class TestBuildEdgeVisual:
    def test_all_defaults_returns_none(self):
        assert build_edge_visual(None, None, None) is None

    def test_all_negative_returns_none(self):
        assert build_edge_visual(-1, 0, 0) is None

    def test_line_color(self):
        result = build_edge_visual(255, None, None)
        assert result == {"lineColor": "#ff0000"}

    def test_bold(self):
        result = build_edge_visual(None, 1, None)
        assert result == {"lineWidth": 2}

    def test_dashed_line(self):
        result = build_edge_visual(None, None, 1)
        assert result == {"dashArray": "8 4"}

    def test_dotted_line(self):
        result = build_edge_visual(None, None, 2)
        assert result == {"dashArray": "2 4"}

    def test_combined(self):
        result = build_edge_visual(255, 1, 1)
        assert result is not None
        assert result["lineColor"] == "#ff0000"
        assert result["lineWidth"] == 2
        assert result["dashArray"] == "8 4"
