"""Tests for diagram link geometry and path parsing (ADR-086).

Tests parse_diagram_link_geometry() and parse_diagram_link_path()
from the converter module. These functions extract EA edge routing
waypoints and endpoint offsets for faithful edge rendering.
"""

from __future__ import annotations

import pytest

from app.import_sparx.converter import (
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
