"""Unit tests for the shared canvas entityId extraction helper (ADR-248).

Previously inlined in ``get_diagram_relationships`` (ADR-184); now shared
by that route and ``GET /api/diagrams/{id}/elements``.
"""

from __future__ import annotations

import json

from app.diagrams.canvas_entities import canvas_entity_ids


def _canvas(*entity_ids: object) -> dict[str, object]:
    return {
        "nodes": [
            {"id": f"n{i}", "data": {"entityId": eid}} for i, eid in enumerate(entity_ids)
        ],
        "edges": [],
    }


def test_returns_entity_ids_in_canvas_order() -> None:
    assert canvas_entity_ids(_canvas("b", "a", "c")) == ["b", "a", "c"]


def test_dedups_keeping_first_occurrence() -> None:
    assert canvas_entity_ids(_canvas("b", "a", "b", "c", "a")) == ["b", "a", "c"]


def test_accepts_json_string() -> None:
    assert canvas_entity_ids(json.dumps(_canvas("x", "y"))) == ["x", "y"]


def test_skips_nodes_without_a_string_entity_id() -> None:
    canvas = {
        "nodes": [
            {"id": "1", "data": {"label": "free text"}},
            {"id": "2"},
            {"id": "3", "data": None},
            {"id": "4", "data": {"entityId": ""}},
            {"id": "5", "data": {"entityId": 42}},
            "not-a-node",
            {"id": "6", "data": {"entityId": "keep"}},
        ],
    }
    assert canvas_entity_ids(canvas) == ["keep"]


def test_tolerates_malformed_canvas() -> None:
    assert canvas_entity_ids(None) == []
    assert canvas_entity_ids("") == []
    assert canvas_entity_ids("{not json") == []
    assert canvas_entity_ids("[]") == []
    assert canvas_entity_ids({"nodes": None}) == []
    assert canvas_entity_ids({"nodes": "nope"}) == []
    assert canvas_entity_ids({}) == []
