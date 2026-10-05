"""The diagram write tools document the canvas keys that decide how a
node or edge renders (ADR-260, issue #315).

A canvas built through MCP used to look right in the stored JSON and
wrong on screen, because nothing told the model which keys the canvas
reads. These tests pin the guidance to the three tools that write a
canvas.
"""

from __future__ import annotations

import pytest

from iris_mcp import tools

CANVAS_WRITE_TOOLS = ("create_diagram", "update_diagram", "patch_diagram")


def _guidance(tool_name: str) -> str:
    """Everything the model reads about a tool's canvas payload."""
    tool = {t.name: t for t in tools.tool_definitions()}[tool_name]
    data = tool.inputSchema["properties"].get("data", {})
    return f"{tool.description}\n{data.get('description', '')}"


@pytest.mark.parametrize("tool_name", CANVAS_WRITE_TOOLS)
class TestCanvasLayoutKeysDocumented:
    def test_edge_label_keys(self, tool_name: str) -> None:
        text = _guidance(tool_name)
        assert "data.labelOffsetX" in text
        assert "data.labelOffsetY" in text
        assert "data.waypoints" in text

    def test_hiding_a_label_and_clearing_waypoints(self, tool_name: str) -> None:
        text = _guidance(tool_name)
        assert 'data.label ""' in text
        assert "null" in text

    def test_class_member_keys(self, tool_name: str) -> None:
        text = _guidance(tool_name)
        assert "data.attributes" in text
        assert "data.operations" in text

    def test_node_size_rules(self, tool_name: str) -> None:
        text = _guidance(tool_name)
        assert "boundary" in text
        assert "three lines" in text


def test_guidance_is_one_shared_block() -> None:
    """Protocol §13: the three tools share one copy of the text."""
    for tool_name in CANVAS_WRITE_TOOLS:
        assert tools.CANVAS_LAYOUT_KEYS in _guidance(tool_name)
