"""Tests for canvas-data shape normalization (ADR-218, issue #238).

`normalize_canvas_data` converts the flat AI/MCP node shape
(`{id, type, label, position, size, visual}`) into the Svelte-Flow
canvas shape (`{id, type, position, width, height, data: {label,
entityType, ...}}`) that the frontend canvas requires. It is
shape-detecting and idempotent: nodes that already carry a dict
`data` are left untouched, so it is safe to run on read, on write,
and repeatedly.

Root cause it guards: `create_diagram` persists its `data` payload
verbatim, but the shared creation prompt teaches models the flat
shape consumed by `apply_diagram_creation`/`_build_canvas_nodes`.
Saving that flat shape via `create_diagram` produced nodes with no
`data` object, crashing `UnifiedCanvas.svelte` on `n.data.entityType`.
"""

from __future__ import annotations

from app.diagrams.canvas_normalize import (
    flat_edge_to_canvas,
    flat_node_to_canvas,
    normalize_canvas_data,
)


def _issue_238_node() -> dict:
    """A node exactly as persisted for the diagram in issue #238."""
    return {
        "id": "st1",
        "type": "stakeholder",
        "label": "New Zealanders (service users)",
        "position": {"x": 60, "y": 20},
        "size": {"width": 180, "height": 80},
        "visual": {},
    }


class TestFlatNodeToCanvas:
    def test_relocates_label_and_type_into_data(self) -> None:
        out = flat_node_to_canvas(_issue_238_node())
        assert out["data"]["label"] == "New Zealanders (service users)"
        assert out["data"]["entityType"] == "stakeholder"

    def test_keeps_type_and_position_and_id(self) -> None:
        out = flat_node_to_canvas(_issue_238_node())
        assert out["id"] == "st1"
        assert out["type"] == "stakeholder"
        assert out["position"] == {"x": 60, "y": 20}

    def test_size_becomes_top_level_width_height(self) -> None:
        out = flat_node_to_canvas(_issue_238_node())
        assert out["width"] == 180
        assert out["height"] == 80
        assert "size" not in out

    def test_empty_visual_is_omitted(self) -> None:
        out = flat_node_to_canvas(_issue_238_node())
        assert "visual" not in out
        assert "visual" not in out["data"]

    def test_non_empty_visual_moves_into_data(self) -> None:
        node = _issue_238_node()
        node["visual"] = {"bgColor": "#FFF2CC", "borderColor": "#D6B656"}
        out = flat_node_to_canvas(node)
        assert out["data"]["visual"] == {"bgColor": "#FFF2CC", "borderColor": "#D6B656"}
        assert "visual" not in out

    def test_description_moves_into_data(self) -> None:
        node = _issue_238_node()
        node["description"] = "A service user persona"
        out = flat_node_to_canvas(node)
        assert out["data"]["description"] == "A service user persona"
        assert "description" not in out

    def test_missing_size_defaults_dimensions(self) -> None:
        node = _issue_238_node()
        del node["size"]
        out = flat_node_to_canvas(node)
        assert out["width"] == 200
        assert out["height"] == 86

    def test_preserves_unknown_structural_keys(self) -> None:
        node = _issue_238_node()
        node["parentId"] = "pool1"
        out = flat_node_to_canvas(node)
        assert out["parentId"] == "pool1"

    def test_default_entity_type_used_when_type_missing(self) -> None:
        node = _issue_238_node()
        del node["type"]
        out = flat_node_to_canvas(node, default_entity_type="outcome_box")
        assert out["data"]["entityType"] == "outcome_box"
        assert out["type"] == "outcome_box"


class TestFlatEdgeToCanvas:
    def test_type_becomes_relationship_type(self) -> None:
        out = flat_edge_to_canvas(
            {"id": "e1", "type": "influence", "source": "a", "target": "b"}
        )
        assert out["data"]["relationshipType"] == "influence"

    def test_adds_center_handles(self) -> None:
        out = flat_edge_to_canvas(
            {"id": "e1", "type": "influence", "source": "a", "target": "b"}
        )
        assert out["sourceHandle"] == "center"
        assert out["targetHandle"] == "center"

    def test_preserves_source_target_id(self) -> None:
        out = flat_edge_to_canvas(
            {"id": "e1", "type": "influence", "source": "a", "target": "b"}
        )
        assert out["id"] == "e1"
        assert out["source"] == "a"
        assert out["target"] == "b"

    def test_keeps_top_level_type_for_renderer_dispatch(self) -> None:
        out = flat_edge_to_canvas(
            {"id": "e1", "type": "influence", "source": "a", "target": "b"}
        )
        assert out["type"] == "influence"


class TestNormalizeCanvasData:
    def test_issue_238_full_payload_gets_data_on_every_node(self) -> None:
        data = {
            "nodes": [
                _issue_238_node(),
                {
                    "id": "goal",
                    "type": "goal",
                    "label": "Create user-focused services",
                    "position": {"x": 300, "y": 160},
                    "size": {"width": 260, "height": 80},
                    "visual": {},
                },
            ],
            "edges": [
                {"id": "e3", "type": "influence", "source": "st1", "target": "goal"},
            ],
        }
        out = normalize_canvas_data(data)
        for node in out["nodes"]:
            assert isinstance(node["data"], dict)
            assert node["data"]["entityType"]
            # The exact access that crashed UnifiedCanvas.svelte:114
            assert node["data"]["entityType"] != "diagram_frame"
        assert out["edges"][0]["data"]["relationshipType"] == "influence"

    def test_already_canvas_node_is_untouched(self) -> None:
        canvas_node = {
            "id": "n1",
            "type": "stakeholder",
            "position": {"x": 0, "y": 0},
            "width": 200,
            "data": {"label": "Existing", "entityType": "stakeholder"},
        }
        out = normalize_canvas_data({"nodes": [canvas_node], "edges": []})
        assert out["nodes"][0] == canvas_node

    def test_mixed_nodes_only_flat_converted(self) -> None:
        canvas_node = {
            "id": "n1",
            "type": "goal",
            "position": {"x": 0, "y": 0},
            "data": {"label": "Canvas", "entityType": "goal"},
        }
        out = normalize_canvas_data({"nodes": [canvas_node, _issue_238_node()]})
        assert out["nodes"][0] == canvas_node
        assert out["nodes"][1]["data"]["entityType"] == "stakeholder"

    def test_already_canvas_edge_is_untouched(self) -> None:
        canvas_edge = {
            "id": "e1",
            "type": "influence",
            "source": "a",
            "target": "b",
            "sourceHandle": "center",
            "targetHandle": "center",
            "data": {"relationshipType": "influence"},
        }
        out = normalize_canvas_data({"nodes": [], "edges": [canvas_edge]})
        assert out["edges"][0] == canvas_edge

    def test_markdown_data_untouched(self) -> None:
        data = {"content": "# Heading\n\nSome **markdown** body."}
        assert normalize_canvas_data(data) == data

    def test_sequence_data_untouched(self) -> None:
        data = {"participants": [{"id": "p1"}], "messages": [], "activations": []}
        assert normalize_canvas_data(data) == data

    def test_non_dict_passthrough(self) -> None:
        assert normalize_canvas_data(None) is None
        assert normalize_canvas_data([1, 2, 3]) == [1, 2, 3]

    def test_empty_dict_passthrough(self) -> None:
        assert normalize_canvas_data({}) == {}

    def test_idempotent(self) -> None:
        data = {
            "nodes": [_issue_238_node()],
            "edges": [{"id": "e1", "type": "influence", "source": "a", "target": "b"}],
        }
        once = normalize_canvas_data(data)
        twice = normalize_canvas_data(once)
        assert once == twice

    def test_does_not_mutate_input(self) -> None:
        node = _issue_238_node()
        data = {"nodes": [node], "edges": []}
        normalize_canvas_data(data)
        # original flat node still flat (no data key added in place)
        assert "data" not in node
        assert node["label"] == "New Zealanders (service users)"
