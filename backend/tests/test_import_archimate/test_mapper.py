"""Tests for the OEX xsi:type → iris type mappers."""

from __future__ import annotations

import pytest

from app.import_archimate.mapper import (
    RELATIONSHIP_TYPE_MAP,
    map_oex_element_type,
    map_oex_relationship_type,
)


@pytest.mark.parametrize(
    ("xsi_type", "expected"),
    [
        ("BusinessActor", "business_actor"),
        ("BusinessProcess", "business_process"),
        ("BusinessObject", "business_object"),
        ("BusinessService", "business_service"),
        ("BusinessFunction", "business_function"),
        ("ApplicationComponent", "application_component"),
        ("ApplicationService", "application_service"),
        ("TechnologyNode", "technology_node"),
        ("Stakeholder", "stakeholder"),
        ("Constraint", "constraint_archimate"),
    ],
)
def test_element_types_round_trip_via_archimate_stereotype_map(
    xsi_type: str, expected: str,
) -> None:
    assert map_oex_element_type(xsi_type) == expected


def test_local_overrides() -> None:
    assert map_oex_element_type("Note") == "note"
    assert map_oex_element_type("Group") == "boundary"
    assert map_oex_element_type("Junction") == "junction"


def test_unknown_element_type_returns_none() -> None:
    assert map_oex_element_type("CompletelyMadeUp") is None
    assert map_oex_element_type("") is None
    assert map_oex_element_type(None) is None


def test_all_archimate_3x_relationship_types_map() -> None:
    canonical = {
        "Composition", "Aggregation", "Assignment", "Realization", "Serving",
        "Triggering", "Flow", "Specialization", "Access", "Influence",
        "Association",
    }
    for name in canonical:
        assert map_oex_relationship_type(name) is not None, name


def test_relationship_legacy_used_alias_maps_to_serving() -> None:
    assert map_oex_relationship_type("Used") == "serving"
    assert map_oex_relationship_type("UsedBy") == "serving"
    assert map_oex_relationship_type("Serving") == "serving"


def test_relationship_british_spelling_aliases() -> None:
    assert map_oex_relationship_type("Realisation") == "realization"
    assert map_oex_relationship_type("Specialisation") == "specialization"


def test_relationship_unknown_returns_none() -> None:
    assert map_oex_relationship_type("Bogus") is None
    assert map_oex_relationship_type(None) is None


def test_relationship_map_keys_lowercase_iris_types() -> None:
    # iris relationship_type strings are snake_case lowercase.
    for v in RELATIONSHIP_TYPE_MAP.values():
        assert v == v.lower()
        assert " " not in v
