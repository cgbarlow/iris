"""ADR-159 (v5.14.0): SearchResult model accepts the new
`mcp_system_context` field on Set / Collection hits."""

from __future__ import annotations

from iris_client.models.core import SearchResult


def test_set_hit_with_mcp_system_context() -> None:
    r = SearchResult.model_validate({
        "id": "s-1",
        "result_type": "set",
        "name": "Outcomes Theory Book",
        "set_id": "s-1",
        "set_name": "Outcomes Theory Book",
        "mcp_system_context": "Orient first.",
    })
    assert r.result_type == "set"
    assert r.mcp_system_context == "Orient first."


def test_collection_hit_with_mcp_system_context() -> None:
    r = SearchResult.model_validate({
        "id": "c-1",
        "result_type": "collection",
        "name": "DoView models",
        "mcp_system_context": "Bootstrap DoView modelling here.",
    })
    assert r.result_type == "collection"
    assert r.mcp_system_context == "Bootstrap DoView modelling here."


def test_legacy_set_hit_without_field_still_validates() -> None:
    """Backwards compat: pre-v5.14.0 backend payload doesn't have the
    field. Field defaults to None on the model."""
    r = SearchResult.model_validate({
        "id": "s-1",
        "result_type": "set",
        "name": "Old set",
    })
    assert r.mcp_system_context is None


def test_non_scope_hit_has_none_mcp_system_context() -> None:
    r = SearchResult.model_validate({
        "id": "d-1",
        "result_type": "diagram",
        "name": "Some diagram",
    })
    assert r.mcp_system_context is None
