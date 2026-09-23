"""Unit tests for the batched diagram-usage matcher (ADR-248, SPEC-248-A).

``count_diagram_usage`` answers, for many element ids at once, "how many
diagrams' current data mention this id as a substring" — the question
``get_element`` asks with ``dv.data LIKE '%<id>%'`` for one id. It must do
that in one pass over the diagram data, not one substring scan per id.

TDD: written before the module existed.
"""

from __future__ import annotations

import json

from app.elements.diagram_usage import count_diagram_usage

A = "0b6c8a52-1f7e-4c1d-9d0e-3a4b5c6d7e8f"
B = "7f3e2d1c-0b9a-4876-9543-210fedcba987"
C = "c0ffee00-1234-4abc-8def-001122334455"


def _canvas(*entity_ids: str) -> str:
    return json.dumps({
        "nodes": [
            {"id": f"n{i}", "data": {"entityId": eid}}
            for i, eid in enumerate(entity_ids)
        ],
        "edges": [],
    })


class TestCountDiagramUsage:
    def test_counts_distinct_diagrams_mentioning_each_id(self) -> None:
        datas = [_canvas(A, B), _canvas(A), _canvas(C)]
        assert count_diagram_usage([A, B, C], datas) == {A: 2, B: 1, C: 1}

    def test_several_mentions_in_one_diagram_count_once(self) -> None:
        assert count_diagram_usage([A], [_canvas(A, A, A)]) == {A: 1}

    def test_unmentioned_ids_are_zero(self) -> None:
        assert count_diagram_usage([A, B], [_canvas(A)]) == {A: 1, B: 0}

    def test_no_ids_or_no_diagrams(self) -> None:
        assert count_diagram_usage([], [_canvas(A)]) == {}
        assert count_diagram_usage([A], []) == {A: 0}

    def test_substring_mentions_count_like_the_single_element_query(self) -> None:
        """LIKE '%id%' matches the id anywhere — inside an edge id, a
        longer hex run, or free text — so the batch must too."""
        edge_only = json.dumps({"nodes": [], "edges": [{"id": f"e-{A}-{B}"}]})
        hex_run = json.dumps({"note": f"ff{C}ff"})
        assert count_diagram_usage([A, B, C], [edge_only, hex_run]) == {
            A: 1, B: 1, C: 1,
        }

    def test_overlapping_uuid_shaped_substrings_are_all_found(self) -> None:
        """A greedy left-to-right scan would consume the first UUID-shaped
        match and miss one that overlaps it; the matcher must not."""
        # X ends with "-...-" + 12 hex; Y starts 28 chars into X.
        x = "aaaaaaaa-bbbb-cccc-dddd-eeee11112222"
        y = "11112222-3333-4444-5555-666666666666"
        text = x[:28] + y
        assert text.startswith(x)
        assert text.endswith(y)
        assert count_diagram_usage([x, y], [text]) == {x: 1, y: 1}

    def test_matching_is_case_sensitive(self) -> None:
        """Ids are exact identifiers (PostgreSQL LIKE semantics); an
        upper-cased copy of an id is not a mention of it."""
        assert count_diagram_usage([A], [_canvas(A.upper())]) == {A: 0}
        assert count_diagram_usage([A.upper()], [_canvas(A)]) == {A.upper(): 0}
        assert count_diagram_usage([A.upper()], [_canvas(A.upper())]) == {
            A.upper(): 1,
        }

    def test_non_uuid_ids_fall_back_to_substring_search(self) -> None:
        datas = [
            json.dumps({"nodes": [{"data": {"entityId": "legacy-42"}}]}),
            json.dumps({"x": "prefix-legacy-42-suffix"}),
            json.dumps({"x": "legacy-4"}),
        ]
        assert count_diagram_usage(["legacy-42", "legacy-4"], datas) == {
            "legacy-42": 2, "legacy-4": 3,
        }

    def test_like_wildcards_in_ids_are_literal(self) -> None:
        """Unlike LIKE, '_' and '%' in an id are not wildcards."""
        datas = [json.dumps({"x": "abXcd"}), json.dumps({"x": "ab_cd"})]
        assert count_diagram_usage(["ab_cd", "a%d"], datas) == {
            "ab_cd": 1, "a%d": 0,
        }

    def test_none_data_is_ignored(self) -> None:
        assert count_diagram_usage([A], [None, _canvas(A)]) == {A: 1}

    def test_duplicate_ids_in_input_collapse(self) -> None:
        assert count_diagram_usage([A, A], [_canvas(A)]) == {A: 1}
