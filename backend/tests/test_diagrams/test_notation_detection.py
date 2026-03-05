"""Unit tests for notation auto-detection (ADR-079)."""

from __future__ import annotations

import pytest

from app.diagrams.notation_detection import detect_notations


class TestDetectNotations:
    def test_empty_data(self) -> None:
        assert detect_notations({}) == []

    def test_no_nodes_key(self) -> None:
        assert detect_notations({"edges": []}) == []

    def test_empty_nodes(self) -> None:
        assert detect_notations({"nodes": []}) == []

    def test_simple_types(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "component"}},
                {"id": "2", "data": {"entityType": "service"}},
                {"id": "3", "data": {"entityType": "database"}},
            ]
        }
        assert detect_notations(data) == ["simple"]

    def test_uml_types(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "class"}},
                {"id": "2", "data": {"entityType": "interface_uml"}},
            ]
        }
        assert detect_notations(data) == ["uml"]

    def test_c4_types(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "person"}},
                {"id": "2", "data": {"entityType": "software_system"}},
                {"id": "3", "data": {"entityType": "container"}},
            ]
        }
        assert detect_notations(data) == ["c4"]

    def test_archimate_types(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "business_actor"}},
                {"id": "2", "data": {"entityType": "application_component"}},
            ]
        }
        assert detect_notations(data) == ["archimate"]

    def test_mixed_notations(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "component"}},
                {"id": "2", "data": {"entityType": "class"}},
                {"id": "3", "data": {"entityType": "person"}},
            ]
        }
        result = detect_notations(data)
        assert result == ["c4", "simple", "uml"]

    def test_universal_types_ignored(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "note"}},
                {"id": "2", "data": {"entityType": "boundary"}},
                {"id": "3", "data": {"entityType": "modelref"}},
            ]
        }
        assert detect_notations(data) == []

    def test_universal_plus_simple(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "note"}},
                {"id": "2", "data": {"entityType": "component"}},
            ]
        }
        assert detect_notations(data) == ["simple"]

    def test_invalid_node_data_skipped(self) -> None:
        data = {
            "nodes": [
                "not_a_dict",
                {"id": "1", "data": "not_a_dict"},
                {"id": "2"},
                {"id": "3", "data": {"entityType": "component"}},
            ]
        }
        assert detect_notations(data) == ["simple"]

    def test_empty_entity_type_skipped(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": ""}},
                {"id": "2", "data": {"entityType": "actor"}},
            ]
        }
        assert detect_notations(data) == ["simple"]

    def test_unknown_entity_type_skipped(self) -> None:
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "unknown_type_xyz"}},
            ]
        }
        assert detect_notations(data) == []

    def test_all_archimate_layers(self) -> None:
        """Verify types from all ArchiMate layers are detected."""
        data = {
            "nodes": [
                {"id": "1", "data": {"entityType": "business_process"}},
                {"id": "2", "data": {"entityType": "application_service"}},
                {"id": "3", "data": {"entityType": "technology_node"}},
                {"id": "4", "data": {"entityType": "stakeholder"}},
                {"id": "5", "data": {"entityType": "capability"}},
                {"id": "6", "data": {"entityType": "work_package"}},
            ]
        }
        assert detect_notations(data) == ["archimate"]

    def test_nodes_not_a_list(self) -> None:
        assert detect_notations({"nodes": "not_a_list"}) == []
