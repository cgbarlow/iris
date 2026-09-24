"""Unit tests for the pure canvas-patch engine (ADR-252, SPEC-252-A, #301).

``app.diagrams.canvas_patch`` applies an ordered list of operations to a
diagram's ``{nodes, edges}`` canvas in memory. It does no I/O: element
names / sets and relationship endpoints arrive pre-fetched in a
``PatchContext``. Any failing operation raises ``CanvasPatchError`` naming
the operation index, and the input canvas is never mutated, so the service
can write nothing on failure.
"""

from __future__ import annotations

import copy

import pytest

from app.diagrams.canvas_patch import (
    MAX_OPERATIONS,
    CanvasPatchError,
    ElementRef,
    PatchContext,
    apply_operations,
    referenced_ids,
)

SET = "set-1"
OTHER_SET = "set-2"


def _node(nid: str, entity: str | None = None, label: str = "", **extra) -> dict:
    data: dict = {"label": label or nid, "entityType": "object"}
    if entity:
        data["entityId"] = entity
    return {
        "id": nid, "type": "object", "position": {"x": 10, "y": 20},
        "width": 200, "height": 86, "data": data, **extra,
    }


def _edge(eid: str, source: str, target: str, **data) -> dict:
    return {
        "id": eid, "source": source, "target": target, "type": "association",
        "sourceHandle": "right", "targetHandle": "left",
        "data": {"relationshipType": "association", **data},
    }


def _canvas() -> dict:
    return {
        "nodes": [
            _node("n1", "e1", "Alice"),
            _node("n2", "e2", "Bob"),
            _node("n3", None, "Note"),
        ],
        "edges": [_edge("x1", "n1", "n2")],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


def _ctx(**kw) -> PatchContext:
    elements = {
        "e1": ElementRef(name="Alice", set_id=SET),
        "e2": ElementRef(name="Bob", set_id=SET),
        "e3": ElementRef(name="Carol", set_id=SET),
        "far": ElementRef(name="Far away", set_id=OTHER_SET),
    }
    elements.update(kw.pop("elements", {}))
    return PatchContext(
        set_id=SET,
        elements=elements,
        relationships=kw.pop("relationships", {"r12": ("e1", "e2"), "r13": ("e1", "e3")}),
    )


def _ids(items: list[dict]) -> list[str]:
    return [i["id"] for i in items]


# ── General behaviour ────────────────────────────────────────────────


class TestGeneral:
    def test_input_is_not_mutated(self) -> None:
        canvas = _canvas()
        before = copy.deepcopy(canvas)
        apply_operations(canvas, [
            {"op": "update_node", "id": "n1", "data": {"label": "X"}},
            {"op": "remove_node", "id": "n2"},
            {"op": "add_node", "node": _node("n9", "e3")},
        ], _ctx())
        assert canvas == before

    def test_failure_does_not_mutate_input(self) -> None:
        canvas = _canvas()
        before = copy.deepcopy(canvas)
        with pytest.raises(CanvasPatchError):
            apply_operations(canvas, [
                {"op": "remove_node", "id": "n1"},
                {"op": "remove_node", "id": "nope"},
            ], _ctx())
        assert canvas == before

    def test_error_names_the_failing_op_index(self) -> None:
        with pytest.raises(CanvasPatchError) as info:
            apply_operations(_canvas(), [
                {"op": "update_node", "id": "n1", "data": {"label": "ok"}},
                {"op": "update_node", "id": "n2", "data": {"label": "ok"}},
                {"op": "remove_edge", "id": "missing"},
            ], _ctx())
        assert info.value.op_index == 2
        assert info.value.op == "remove_edge"
        assert "operations[2]" in str(info.value)
        assert "missing" in str(info.value)

    def test_unknown_op_rejected(self) -> None:
        with pytest.raises(CanvasPatchError) as info:
            apply_operations(_canvas(), [{"op": "explode"}], _ctx())
        assert info.value.op_index == 0
        assert "explode" in str(info.value)

    def test_op_must_be_an_object_with_op(self) -> None:
        for bad in ("add_node", {"id": "n1"}, None):
            with pytest.raises(CanvasPatchError) as info:
                apply_operations(_canvas(), [bad], _ctx())
            assert info.value.op_index == 0

    def test_operation_count_bounds(self) -> None:
        with pytest.raises(CanvasPatchError):
            apply_operations(_canvas(), [], _ctx())
        ops = [{"op": "update_node", "id": "n1", "data": {"k": i}}
               for i in range(MAX_OPERATIONS + 1)]
        with pytest.raises(CanvasPatchError):
            apply_operations(_canvas(), ops, _ctx())
        out = apply_operations(_canvas(), ops[:MAX_OPERATIONS], _ctx())
        assert len(out.results) == MAX_OPERATIONS

    def test_ops_apply_in_order(self) -> None:
        out = apply_operations(_canvas(), [
            {"op": "add_node", "node": _node("n9", "e3")},
            {"op": "add_edge", "edge": _edge("x9", "n1", "n9")},
            {"op": "remove_node", "id": "n9"},
        ], _ctx())
        assert "n9" not in _ids(out.data["nodes"])
        assert "x9" not in _ids(out.data["edges"])

    def test_other_canvas_keys_are_preserved(self) -> None:
        out = apply_operations(
            _canvas(), [{"op": "remove_edge", "id": "x1"}], _ctx(),
        )
        assert out.data["viewport"] == {"x": 0, "y": 0, "zoom": 1}

    def test_empty_canvas_accepts_adds(self) -> None:
        out = apply_operations({}, [{"op": "add_node", "node": _node("n1", "e1")}], _ctx())
        assert _ids(out.data["nodes"]) == ["n1"]
        assert out.data["edges"] == []

    def test_non_canvas_data_rejected(self) -> None:
        for data in ({"content": "# md"}, {"participants": []}, {"nodes": "x"}):
            with pytest.raises(CanvasPatchError) as info:
                apply_operations(data, [{"op": "sync_labels"}], _ctx())
            assert info.value.op_index is None


# ── Nodes ────────────────────────────────────────────────────────────


class TestAddNode:
    def test_appends_node_and_reports_id(self) -> None:
        out = apply_operations(
            _canvas(), [{"op": "add_node", "node": _node("n9", "e3", "Carol")}], _ctx(),
        )
        assert out.data["nodes"][-1]["id"] == "n9"
        assert out.results == [{"index": 0, "op": "add_node", "id": "n9"}]

    def test_node_without_entity_is_allowed(self) -> None:
        out = apply_operations(
            _canvas(), [{"op": "add_node", "node": _node("n9", None, "Note")}], _ctx(),
        )
        assert out.data["nodes"][-1]["data"]["label"] == "Note"

    def test_duplicate_id_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="n1"):
            apply_operations(_canvas(), [{"op": "add_node", "node": _node("n1", "e3")}], _ctx())

    def test_duplicate_within_patch_rejected(self) -> None:
        with pytest.raises(CanvasPatchError) as info:
            apply_operations(_canvas(), [
                {"op": "add_node", "node": _node("n9", "e3")},
                {"op": "add_node", "node": _node("n9", "e3")},
            ], _ctx())
        assert info.value.op_index == 1

    def test_entity_in_other_set_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="set"):
            apply_operations(_canvas(), [{"op": "add_node", "node": _node("n9", "far")}], _ctx())

    def test_unknown_or_deleted_entity_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="ghost"):
            apply_operations(_canvas(), [{"op": "add_node", "node": _node("n9", "ghost")}], _ctx())

    def test_requires_id_and_position(self) -> None:
        no_id = _node("n9")
        del no_id["id"]
        no_pos = _node("n9")
        del no_pos["position"]
        bad_pos = _node("n9")
        bad_pos["position"] = {"x": "left", "y": 0}
        for node in (no_id, no_pos, bad_pos, "n9"):
            with pytest.raises(CanvasPatchError):
                apply_operations(_canvas(), [{"op": "add_node", "node": node}], _ctx())

    def test_flat_ai_shape_is_normalised(self) -> None:
        # ADR-218: the creation prompt's flat node shape is accepted and
        # stored in canvas shape, exactly as update_diagram would store it.
        flat = {"id": "n9", "type": "object", "label": "Flat",
                "position": {"x": 1, "y": 2}}
        out = apply_operations(_canvas(), [{"op": "add_node", "node": flat}], _ctx())
        node = out.data["nodes"][-1]
        assert node["data"]["label"] == "Flat"
        assert node["data"]["entityType"] == "object"

    def test_parent_must_exist(self) -> None:
        with pytest.raises(CanvasPatchError, match="parent"):
            apply_operations(
                _canvas(),
                [{"op": "add_node", "node": _node("n9", None, parentId="nope")}],
                _ctx(),
            )
        out = apply_operations(
            _canvas(), [{"op": "add_node", "node": _node("n9", None, parentId="n3")}], _ctx(),
        )
        assert out.data["nodes"][-1]["parentId"] == "n3"


class TestUpdateNode:
    def test_shallow_merges_data(self) -> None:
        out = apply_operations(_canvas(), [
            {"op": "update_node", "id": "n1",
             "data": {"label": "Alicia", "visual": {"fill": "#fff"}}},
        ], _ctx())
        data = out.data["nodes"][0]["data"]
        assert data["label"] == "Alicia"
        assert data["visual"] == {"fill": "#fff"}
        assert data["entityId"] == "e1"
        assert data["entityType"] == "object"
        assert out.results == [{"index": 0, "op": "update_node", "id": "n1"}]

    def test_null_removes_a_data_key(self) -> None:
        canvas = _canvas()
        canvas["nodes"][0]["data"]["visual"] = {"fill": "#000"}
        out = apply_operations(
            canvas, [{"op": "update_node", "id": "n1", "data": {"visual": None}}], _ctx(),
        )
        assert "visual" not in out.data["nodes"][0]["data"]

    def test_partial_position_and_size(self) -> None:
        out = apply_operations(_canvas(), [
            {"op": "update_node", "id": "n1", "position": {"x": 500}, "width": 300},
        ], _ctx())
        node = out.data["nodes"][0]
        assert node["position"] == {"x": 500, "y": 20}
        assert node["width"] == 300
        assert node["height"] == 86

    def test_missing_node_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="nope"):
            apply_operations(_canvas(), [{"op": "update_node", "id": "nope",
                                           "data": {"label": "x"}}], _ctx())

    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="colour"):
            apply_operations(_canvas(), [{"op": "update_node", "id": "n1",
                                           "colour": "red"}], _ctx())

    def test_bad_types_rejected(self) -> None:
        for bad in ({"data": "x"}, {"position": {"x": "a"}}, {"width": "wide"}):
            with pytest.raises(CanvasPatchError):
                apply_operations(_canvas(), [{"op": "update_node", "id": "n1", **bad}], _ctx())

    def test_relinking_entity_is_validated(self) -> None:
        with pytest.raises(CanvasPatchError, match="set"):
            apply_operations(_canvas(), [{"op": "update_node", "id": "n3",
                                           "data": {"entityId": "far"}}], _ctx())
        out = apply_operations(_canvas(), [{"op": "update_node", "id": "n3",
                                             "data": {"entityId": "e3"}}], _ctx())
        assert out.data["nodes"][2]["data"]["entityId"] == "e3"


class TestRemoveNode:
    def test_cascades_edges_by_default(self) -> None:
        out = apply_operations(_canvas(), [{"op": "remove_node", "id": "n1"}], _ctx())
        assert _ids(out.data["nodes"]) == ["n2", "n3"]
        assert out.data["edges"] == []
        assert out.results == [
            {"index": 0, "op": "remove_node", "id": "n1", "removed_edges": ["x1"]},
        ]

    def test_without_cascade_rejects_connected_node(self) -> None:
        with pytest.raises(CanvasPatchError, match="x1"):
            apply_operations(_canvas(), [
                {"op": "remove_node", "id": "n2", "cascade_edges": False},
            ], _ctx())

    def test_without_cascade_removes_unconnected_node(self) -> None:
        out = apply_operations(_canvas(), [
            {"op": "remove_node", "id": "n3", "cascade_edges": False},
        ], _ctx())
        assert _ids(out.data["nodes"]) == ["n1", "n2"]

    def test_missing_node_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="nope"):
            apply_operations(_canvas(), [{"op": "remove_node", "id": "nope"}], _ctx())

    def test_parent_of_nested_nodes_rejected(self) -> None:
        canvas = _canvas()
        canvas["nodes"].append(_node("child", None, parentId="n3"))
        with pytest.raises(CanvasPatchError, match="child"):
            apply_operations(canvas, [{"op": "remove_node", "id": "n3"}], _ctx())


# ── Edges ────────────────────────────────────────────────────────────


class TestAddEdge:
    def test_appends_edge(self) -> None:
        out = apply_operations(
            _canvas(), [{"op": "add_edge", "edge": _edge("x9", "n2", "n3")}], _ctx(),
        )
        assert out.data["edges"][-1]["id"] == "x9"
        assert out.results == [{"index": 0, "op": "add_edge", "id": "x9"}]

    def test_source_and_target_must_exist(self) -> None:
        for src, tgt in (("nope", "n2"), ("n1", "nope")):
            with pytest.raises(CanvasPatchError, match="nope"):
                apply_operations(
                    _canvas(), [{"op": "add_edge", "edge": _edge("x9", src, tgt)}], _ctx(),
                )

    def test_duplicate_id_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="x1"):
            apply_operations(
                _canvas(), [{"op": "add_edge", "edge": _edge("x1", "n2", "n1")}], _ctx(),
            )

    def test_relationship_matching_either_direction_accepted(self) -> None:
        out = apply_operations(_canvas(), [
            {"op": "add_edge", "edge": _edge("x9", "n2", "n1", relationshipId="r12")},
        ], _ctx())
        assert out.data["edges"][-1]["data"]["relationshipId"] == "r12"

    def test_relationship_for_other_elements_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="r13"):
            apply_operations(_canvas(), [
                {"op": "add_edge", "edge": _edge("x9", "n1", "n2", relationshipId="r13")},
            ], _ctx())

    def test_unknown_relationship_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="gone"):
            apply_operations(_canvas(), [
                {"op": "add_edge", "edge": _edge("x9", "n1", "n2", relationshipId="gone")},
            ], _ctx())

    def test_relationship_on_unlinked_node_rejected(self) -> None:
        with pytest.raises(CanvasPatchError):
            apply_operations(_canvas(), [
                {"op": "add_edge", "edge": _edge("x9", "n1", "n3", relationshipId="r12")},
            ], _ctx())

    def test_edge_to_node_added_earlier_in_patch(self) -> None:
        out = apply_operations(_canvas(), [
            {"op": "add_node", "node": _node("n9", "e3")},
            {"op": "add_edge", "edge": _edge("x9", "n1", "n9", relationshipId="r13")},
        ], _ctx())
        assert _ids(out.data["edges"]) == ["x1", "x9"]

    def test_flat_edge_shape_is_normalised(self) -> None:
        flat = {"id": "x9", "source": "n2", "target": "n3", "type": "dependency"}
        out = apply_operations(_canvas(), [{"op": "add_edge", "edge": flat}], _ctx())
        edge = out.data["edges"][-1]
        assert edge["data"]["relationshipType"] == "dependency"

    def test_requires_id_source_target(self) -> None:
        for edge in ({"source": "n1", "target": "n2", "data": {}},
                     {"id": "x9", "target": "n2", "data": {}},
                     {"id": "x9", "source": "n1", "data": {}}):
            with pytest.raises(CanvasPatchError):
                apply_operations(_canvas(), [{"op": "add_edge", "edge": edge}], _ctx())


class TestUpdateEdge:
    def test_shallow_merges_data_and_handles(self) -> None:
        out = apply_operations(_canvas(), [
            {"op": "update_edge", "id": "x1", "data": {"sourceRole": "partner"},
             "sourceHandle": "bottom"},
        ], _ctx())
        edge = out.data["edges"][0]
        assert edge["data"] == {"relationshipType": "association", "sourceRole": "partner"}
        assert edge["sourceHandle"] == "bottom"
        assert edge["targetHandle"] == "left"
        assert out.results == [{"index": 0, "op": "update_edge", "id": "x1"}]

    def test_endpoints_cannot_change(self) -> None:
        with pytest.raises(CanvasPatchError, match="source"):
            apply_operations(_canvas(), [{"op": "update_edge", "id": "x1",
                                           "source": "n3"}], _ctx())

    def test_missing_edge_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="nope"):
            apply_operations(_canvas(), [{"op": "update_edge", "id": "nope",
                                           "data": {}}], _ctx())

    def test_relationship_id_is_validated(self) -> None:
        with pytest.raises(CanvasPatchError, match="r13"):
            apply_operations(_canvas(), [{"op": "update_edge", "id": "x1",
                                           "data": {"relationshipId": "r13"}}], _ctx())
        out = apply_operations(_canvas(), [{"op": "update_edge", "id": "x1",
                                             "data": {"relationshipId": "r12"}}], _ctx())
        assert out.data["edges"][0]["data"]["relationshipId"] == "r12"


class TestRemoveEdge:
    def test_removes_edge(self) -> None:
        out = apply_operations(_canvas(), [{"op": "remove_edge", "id": "x1"}], _ctx())
        assert out.data["edges"] == []
        assert _ids(out.data["nodes"]) == ["n1", "n2", "n3"]
        assert out.results == [{"index": 0, "op": "remove_edge", "id": "x1"}]

    def test_missing_edge_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="nope"):
            apply_operations(_canvas(), [{"op": "remove_edge", "id": "nope"}], _ctx())


# ── sync_labels ──────────────────────────────────────────────────────


class TestSyncLabels:
    def _stale(self) -> dict:
        canvas = _canvas()
        canvas["nodes"][0]["data"]["label"] = "Alice (old name)"
        canvas["nodes"][0]["data"]["visual"] = {"fill": "#123456"}
        canvas["nodes"][1]["data"]["label"] = "Bob (old)"
        return canvas

    def test_resets_labels_to_element_names_only(self) -> None:
        canvas = self._stale()
        out = apply_operations(canvas, [{"op": "sync_labels"}], _ctx())
        n1, n2, n3 = out.data["nodes"]
        assert n1["data"]["label"] == "Alice"
        assert n2["data"]["label"] == "Bob"
        assert n3["data"]["label"] == "Note"  # no entityId: untouched
        # Presentation is untouched (ADR-230 F1: the diagram owns it).
        assert n1["position"] == canvas["nodes"][0]["position"]
        assert n1["width"] == 200
        assert n1["height"] == 86
        assert n1["data"]["visual"] == {"fill": "#123456"}
        assert out.data["edges"] == canvas["edges"]
        assert out.results == [
            {"index": 0, "op": "sync_labels", "ids": ["n1", "n2"], "skipped": []},
        ]

    def test_limited_to_node_ids(self) -> None:
        out = apply_operations(self._stale(), [
            {"op": "sync_labels", "node_ids": ["n2"]},
        ], _ctx())
        assert out.data["nodes"][0]["data"]["label"] == "Alice (old name)"
        assert out.data["nodes"][1]["data"]["label"] == "Bob"

    def test_unknown_node_id_rejected(self) -> None:
        with pytest.raises(CanvasPatchError, match="nope"):
            apply_operations(_canvas(), [{"op": "sync_labels", "node_ids": ["nope"]}], _ctx())

    def test_deleted_element_is_skipped(self) -> None:
        canvas = _canvas()
        canvas["nodes"][0]["data"]["entityId"] = "deleted"
        out = apply_operations(canvas, [{"op": "sync_labels"}], _ctx())
        assert out.data["nodes"][0]["data"]["label"] == "Alice"
        assert out.results[0]["skipped"] == ["n1"]

    def test_up_to_date_labels_report_nothing(self) -> None:
        out = apply_operations(_canvas(), [{"op": "sync_labels"}], _ctx())
        assert out.results[0]["ids"] == []


# ── referenced_ids ───────────────────────────────────────────────────


class TestReferencedIds:
    def test_collects_only_what_validation_needs(self) -> None:
        elements, relationships = referenced_ids(_canvas(), [
            {"op": "add_node", "node": _node("n9", "e3")},
            {"op": "update_node", "id": "n3", "data": {"entityId": "e4"}},
            {"op": "add_edge", "edge": _edge("x9", "n1", "n9", relationshipId="r13")},
            {"op": "update_edge", "id": "x1", "data": {"relationshipId": "r12"}},
            {"op": "remove_node", "id": "n2"},
        ])
        assert set(elements) == {"e3", "e4"}
        assert set(relationships) == {"r13", "r12"}

    def test_sync_labels_needs_canvas_elements(self) -> None:
        elements, _ = referenced_ids(_canvas(), [{"op": "sync_labels"}])
        assert set(elements) == {"e1", "e2"}

    def test_tolerates_malformed_ops(self) -> None:
        elements, relationships = referenced_ids(
            _canvas(), [None, "x", {"op": "add_node", "node": "bad"}, {"op": "add_edge"}],
        )
        assert elements == []
        assert relationships == []


# ── Robustness: malformed input is a CanvasPatchError, never a crash ──


class TestMalformedInput:
    def test_malformed_flat_node_is_an_op_error(self) -> None:
        # flat_node_to_canvas reads size.get(...) — a non-object size must
        # not escape as an AttributeError (HTTP 500).
        bad = {"id": "n9", "label": "x", "size": 5, "position": {"x": 0, "y": 0}}
        with pytest.raises(CanvasPatchError) as info:
            apply_operations(_canvas(), [{"op": "add_node", "node": bad}], _ctx())
        assert info.value.op_index == 0

    def test_sync_labels_tolerates_legacy_node_without_id(self) -> None:
        canvas = _canvas()
        del canvas["nodes"][0]["id"]
        canvas["nodes"][0]["data"]["label"] = "stale"
        out = apply_operations(canvas, [{"op": "sync_labels"}], _ctx())
        assert out.data["nodes"][0]["data"]["label"] == "Alice"
