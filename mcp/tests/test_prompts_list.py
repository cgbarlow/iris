"""ADR-152: MCP `prompts/list` handler.

Maps each iris-client `ScopePromptIndexEntry` into an MCP SDK `Prompt`
object that Claude Desktop displays in its prompt picker.
"""

from __future__ import annotations

from typing import Any

import pytest
from iris_client.models.core import ScopePromptIndexEntry

from iris_mcp import prompts as iris_prompts


class _StubClient:
    """Minimal IrisClient stand-in returning a fixed index."""

    def __init__(self, entries: list[ScopePromptIndexEntry]) -> None:
        self._entries = entries

    async def list_scope_prompts(self) -> list[ScopePromptIndexEntry]:
        return list(self._entries)


def _entry(**kwargs: Any) -> ScopePromptIndexEntry:
    defaults = {
        "name": "iris:set:00000000-0000-0000-0000-000000000001",
        "scope_type": "set",
        "scope_id": "00000000-0000-0000-0000-000000000001",
        "scope_name": "Test Set",
        "description": None,
        "body": "prompt body",
    }
    defaults.update(kwargs)
    return ScopePromptIndexEntry(**defaults)


class TestListPrompts:
    @pytest.mark.asyncio
    async def test_empty_index_returns_empty_list(self) -> None:
        client: Any = _StubClient([])
        result = await iris_prompts.list_prompts(client)
        assert result == []

    @pytest.mark.asyncio
    async def test_maps_set_entry(self) -> None:
        entries = [_entry(
            name="iris:set:11111111-1111-1111-1111-111111111111",
            scope_id="11111111-1111-1111-1111-111111111111",
            scope_name="DoView Book",
            description="Outcomes theory reference",
        )]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)

        assert len(result) == 1
        p = result[0]
        assert p.name == "iris:set:11111111-1111-1111-1111-111111111111"
        # Description includes scope-type label, human name, and description.
        assert "Set" in p.description
        assert "DoView Book" in p.description
        assert "Outcomes theory reference" in p.description
        # No template arguments in v1.
        assert p.arguments == []

    @pytest.mark.asyncio
    async def test_maps_collection_entry(self) -> None:
        entries = [_entry(
            name="iris:collection:22222222-2222-2222-2222-222222222222",
            scope_type="collection",
            scope_id="22222222-2222-2222-2222-222222222222",
            scope_name="NZISM",
            description=None,
        )]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)

        assert len(result) == 1
        p = result[0]
        assert p.name == "iris:collection:22222222-2222-2222-2222-222222222222"
        assert "Collection" in p.description
        assert "NZISM" in p.description

    @pytest.mark.asyncio
    async def test_truncates_very_long_descriptions(self) -> None:
        entries = [_entry(description="x" * 500)]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)
        # Description capped at 200 chars.
        assert len(result[0].description) <= 200

    @pytest.mark.asyncio
    async def test_strips_redundant_scope_name_prefix_from_description(self) -> None:
        """v5.8.4: avoid 'Set: DoView Book — DoView Book — published from ...'

        When the scope's description already begins with the scope name
        (common Iris authoring pattern), we'd double up the name in the
        picker label. Strip the leading scope name + separator so the
        picker reads 'Set: DoView Book — published from doview-book repo'.
        """
        entries = [_entry(
            scope_name="DoView Book",
            description="DoView Book — published from doview-book repo",
        )]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)
        desc = result[0].description
        # Name appears exactly once.
        assert desc.count("DoView Book") == 1
        # The remainder of the original description is preserved.
        assert "published from doview-book repo" in desc
        # Picker label format unchanged for the prefix.
        assert desc.startswith("Set: DoView Book")

    @pytest.mark.asyncio
    async def test_strip_is_case_insensitive(self) -> None:
        """Description starting with 'doview book' (lowercase) still
        recognised as a duplicate of scope name 'DoView Book'."""
        entries = [_entry(
            scope_name="DoView Book",
            description="doview book — repo",
        )]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)
        desc = result[0].description
        # Only the canonical name from the prefix remains; the lowercase
        # duplicate is gone.
        assert desc.lower().count("doview book") == 1

    @pytest.mark.asyncio
    async def test_drops_description_when_it_is_only_the_scope_name(self) -> None:
        """If description IS the scope name, drop it entirely rather
        than emitting 'Set: DoView Book — DoView Book'."""
        entries = [_entry(
            scope_name="DoView Book",
            description="DoView Book",
        )]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)
        # No dangling " — " at the end, no second occurrence of the name.
        desc = result[0].description
        assert desc == "Set: DoView Book"

    @pytest.mark.asyncio
    async def test_preserves_description_when_no_redundancy(self) -> None:
        """Description that doesn't start with the scope name is
        passed through verbatim."""
        entries = [_entry(
            scope_name="DoView Book",
            description="Outcomes theory companion volume.",
        )]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)
        desc = result[0].description
        assert desc == "Set: DoView Book — Outcomes theory companion volume."

    @pytest.mark.asyncio
    async def test_preserves_order(self) -> None:
        entries = [
            _entry(
                name="iris:collection:c1",
                scope_type="collection",
                scope_id="c1",
                scope_name="First",
            ),
            _entry(
                name="iris:set:s1",
                scope_type="set",
                scope_id="s1",
                scope_name="Second",
            ),
        ]
        client: Any = _StubClient(entries)
        result = await iris_prompts.list_prompts(client)
        assert [p.name for p in result] == [
            "iris:collection:c1",
            "iris:set:s1",
        ]
