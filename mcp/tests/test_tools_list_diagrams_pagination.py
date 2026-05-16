"""v6.6.4 — `list_diagrams` MCP tool gains pagination + parent_package_id
filter so an orient-driven model can fetch the root-level bracketing
diagrams (Introduction / Conclusion) in a single targeted call,
matching the Outcomes Theory orient sheet's instruction.

Pre-v6.6.4 the tool only accepted ``set_id`` — the backend's default
``page_size=50`` ``updated_at DESC`` ordering meant root diagrams in
a 100+-diagram Set were unreachable once recent edits filled page 1.

TDD: written before the tool wiring change.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from iris_mcp.tools import TOOLS


def _tool_by_name(name: str):
    return next(t for t in TOOLS if t.name == name)


def _stub_client(*, list_diagrams_result):
    client: Any = MagicMock()
    client.list_diagrams = AsyncMock(return_value=list_diagrams_result)
    return client


class TestListDiagramsToolWiring:
    @pytest.mark.asyncio
    async def test_passes_pagination_and_parent_filter(self) -> None:
        client = _stub_client(list_diagrams_result=[])
        tool = _tool_by_name("list_diagrams")

        await tool.handler(client, {
            "set_id": "s-1",
            "page": 2,
            "page_size": 25,
            "parent_package_id": "parent-1",
        })
        client.list_diagrams.assert_awaited_once_with(
            set_id="s-1",
            parent_package_id="parent-1",
            page=2,
            page_size=25,
        )

    @pytest.mark.asyncio
    async def test_default_pagination_matches_backend_default(self) -> None:
        client = _stub_client(list_diagrams_result=[])
        tool = _tool_by_name("list_diagrams")

        await tool.handler(client, {"set_id": "s-1"})
        client.list_diagrams.assert_awaited_once_with(
            set_id="s-1",
            parent_package_id=None,
            page=1,
            page_size=50,
        )

    @pytest.mark.asyncio
    async def test_passes_null_sentinel_for_root_only(self) -> None:
        """The orient sheet's ``list_diagrams(set_id=...,
        parent_package_id=null)`` instruction lands here as the
        literal string ``"null"`` in tool args (MCP JSON null arrives
        as Python None; the model is steered to use the explicit
        string sentinel by the tool description)."""
        client = _stub_client(list_diagrams_result=[])
        tool = _tool_by_name("list_diagrams")

        await tool.handler(client, {
            "set_id": "s-1",
            "parent_package_id": "null",
        })
        client.list_diagrams.assert_awaited_once_with(
            set_id="s-1",
            parent_package_id="null",
            page=1,
            page_size=50,
        )


class TestListDiagramsToolSchema:
    def test_description_warns_about_pagination(self) -> None:
        tool = _tool_by_name("list_diagrams")
        desc_lower = tool.description.lower()
        # Same warning shape as list_packages — the model needs to
        # know the default cap and that iteration is required for
        # large sets, otherwise the failure mode is silent (returns
        # the wrong 50 rows and the orient TOC is incomplete).
        assert "page" in desc_lower
        assert "50" in tool.description

    def test_description_names_null_sentinel(self) -> None:
        """The orient sheet refers to ``parent_package_id=null``; the
        tool description must spell out that the sentinel arrives as
        the literal string ``"null"`` (not JSON null) so the model
        passes it correctly."""
        tool = _tool_by_name("list_diagrams")
        assert "null" in tool.description.lower()
        assert "parent_package_id" in tool.description

    def test_schema_exposes_page_page_size_parent_package_id(self) -> None:
        tool = _tool_by_name("list_diagrams")
        props = tool.input_schema["properties"]
        assert "page" in props
        assert "page_size" in props
        assert "parent_package_id" in props
        # set_id stays optional and unchanged.
        assert "set_id" in props
