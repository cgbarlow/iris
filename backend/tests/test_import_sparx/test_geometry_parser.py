"""Tests for diagram link geometry and path parsing (ADR-086).

Tests parse_diagram_link_geometry() and parse_diagram_link_path()
from the converter module. These functions extract EA edge routing
waypoints and endpoint offsets for faithful edge rendering.
"""

from __future__ import annotations

import pytest

from app.import_sparx.converter import (
    build_edge_visual,
    build_node_visual,
    parse_diagram_link_geometry,
    parse_diagram_link_path,
)


class TestParseDiagramLinkGeometry:
    """Verify parse_diagram_link_geometry extracts SX/SY/EX/EY offset pairs."""

    def test_basic_offsets(self) -> None:
        result = parse_diagram_link_geometry("SX=10;SY=-5;EX=20;EY=15;")
        assert result == {"sx": 10, "sy": -5, "ex": 20, "ey": 15}

    def test_none_returns_empty_dict(self) -> None:
        result = parse_diagram_link_geometry(None)
        assert result == {}

    def test_zero_offsets_with_edge_key(self) -> None:
        result = parse_diagram_link_geometry("SX=0;SY=0;EX=0;EY=0;EDGE=2;")
        assert result == {"sx": 0, "sy": 0, "ex": 0, "ey": 0, "edge": 2}

    def test_empty_string_returns_empty_dict(self) -> None:
        result = parse_diagram_link_geometry("")
        assert result == {}


class TestParseLabelPositions:
    """Verify parse_diagram_link_geometry extracts LLB/LLT/LRT/LRB label positions."""

    def test_extracts_llb_label_position(self) -> None:
        result = parse_diagram_link_geometry("SX=0;SY=0;EX=0;EY=0;LLB=100:200;")
        assert result["labels"]["llb"] == {"cx": 100, "cy": 200}

    def test_extracts_multiple_label_positions(self) -> None:
        result = parse_diagram_link_geometry("LLB=10:20;LRT=30:40;LRB=50:60;")
        assert result["labels"]["llb"] == {"cx": 10, "cy": 20}
        assert result["labels"]["lrt"] == {"cx": 30, "cy": 40}
        assert result["labels"]["lrb"] == {"cx": 50, "cy": 60}

    def test_extracts_llt_label_position(self) -> None:
        result = parse_diagram_link_geometry("LLT=100:-200;")
        assert result["labels"]["llt"] == {"cx": 100, "cy": -200}

    def test_no_labels_returns_no_labels_key(self) -> None:
        result = parse_diagram_link_geometry("SX=10;SY=-5;")
        assert "labels" not in result

    def test_invalid_label_coords_ignored(self) -> None:
        result = parse_diagram_link_geometry("LLB=abc:def;SX=10;")
        assert "labels" not in result
        assert result["sx"] == 10


class TestParseDiagramLinkPath:
    """Verify parse_diagram_link_path extracts waypoint coordinates with Y negated."""

    def test_two_waypoints(self) -> None:
        """Path string '100:-200;300:-400;' yields two points with Y negated."""
        result = parse_diagram_link_path("100:-200;300:-400;")
        assert result == [{"x": 100, "y": 200}, {"x": 300, "y": 400}]

    def test_none_returns_empty_list(self) -> None:
        result = parse_diagram_link_path(None)
        assert result == []

    def test_empty_string_returns_empty_list(self) -> None:
        result = parse_diagram_link_path("")
        assert result == []

    def test_single_waypoint(self) -> None:
        result = parse_diagram_link_path("50:-100;")
        assert result == [{"x": 50, "y": 100}]

    def test_positive_y_negated(self) -> None:
        """Positive Y in EA (unusual) should still be negated."""
        result = parse_diagram_link_path("10:20;")
        assert result == [{"x": 10, "y": -20}]


class TestBuildNodeVisualDefaults:
    """Verify build_node_visual emits EA default colors when all values are -1 (ADR-090)."""

    def test_all_defaults_emits_white_bg_and_black_border(self) -> None:
        """EA default -1 for all colors should produce white bg, black border."""
        result = build_node_visual(None, -1, -1, -1, None)
        assert result is not None
        assert result["bgColor"] == "#ffffff"
        assert result["borderColor"] == "#000000"

    def test_none_backcolor_emits_white_bg(self) -> None:
        result = build_node_visual(None, None, None, None, None)
        assert result is not None
        assert result["bgColor"] == "#ffffff"
        assert result["borderColor"] == "#000000"

    def test_explicit_color_overrides_default(self) -> None:
        """When EA has an explicit color, use it instead of default."""
        result = build_node_visual(None, 65280, None, None, None)  # green in BGR
        assert result is not None
        assert result["bgColor"] == "#00ff00"

    def test_object_style_overrides_default(self) -> None:
        result = build_node_visual("BCol=255;", None, None, None, None)  # red in BGR
        assert result is not None
        assert result["bgColor"] == "#ff0000"

    def test_default_does_not_set_fontcolor(self) -> None:
        """Font color default (-1) should NOT be emitted — CSS handles it."""
        result = build_node_visual(None, None, -1, None, None)
        assert result is not None
        assert "fontColor" not in result


class TestBuildEdgeVisualDefaults:
    """Verify build_edge_visual emits EA default black when lineColor is -1 (ADR-090)."""

    def test_none_linecolor_emits_black(self) -> None:
        result = build_edge_visual(None, None, None)
        assert result is not None
        assert result["lineColor"] == "#000000"

    def test_default_linecolor_emits_black(self) -> None:
        result = build_edge_visual(-1, None, None)
        assert result is not None
        assert result["lineColor"] == "#000000"

    def test_explicit_linecolor_preserved(self) -> None:
        result = build_edge_visual(255, None, None)  # red in BGR
        assert result is not None
        assert result["lineColor"] == "#ff0000"

    def test_bold_edge(self) -> None:
        result = build_edge_visual(None, 1, None)
        assert result is not None
        assert result["lineWidth"] == 2
