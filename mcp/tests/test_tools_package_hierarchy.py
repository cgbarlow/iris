"""ADR-158 (v5.13.0): the `package_hierarchy` MCP tool returns a
complete package tree in a single call, and the `list_packages` tool
gained pagination + parent_package_id filter for level-by-level walks.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from iris_client.models.core import Package, PackageHierarchyNode

from iris_mcp.tools import TOOLS


def _tool_by_name(name: str):
    return next(t for t in TOOLS if t.name == name)


def _stub_client(*, package_hierarchy_result=None, list_packages_result=None):
    client: Any = MagicMock()
    if package_hierarchy_result is not None:
        client.package_hierarchy = AsyncMock(return_value=package_hierarchy_result)
    if list_packages_result is not None:
        client.list_packages = AsyncMock(return_value=list_packages_result)
    return client


@pytest.mark.asyncio
async def test_package_hierarchy_tool_returns_nested_tree() -> None:
    tree = [
        PackageHierarchyNode(
            id="p-A", name="Chapter A", parent_package_id=None,
            children=[
                PackageHierarchyNode(id="p-A1", name="A.1", parent_package_id="p-A", children=[]),
            ],
        ),
        PackageHierarchyNode(
            id="p-B", name="Chapter B", parent_package_id=None, children=[],
        ),
    ]
    client = _stub_client(package_hierarchy_result=tree)
    tool = _tool_by_name("package_hierarchy")

    result = await tool.handler(client, {"set_id": "s-1"})
    import json
    nodes = json.loads(result)
    assert len(nodes) == 2
    assert nodes[0]["name"] == "Chapter A"
    assert len(nodes[0]["children"]) == 1
    assert nodes[0]["children"][0]["name"] == "A.1"
    client.package_hierarchy.assert_awaited_once_with(set_id="s-1", root_id=None)


@pytest.mark.asyncio
async def test_package_hierarchy_tool_accepts_root_id() -> None:
    client = _stub_client(package_hierarchy_result=[])
    tool = _tool_by_name("package_hierarchy")

    await tool.handler(client, {"set_id": "s-1", "root_id": "r-1"})
    client.package_hierarchy.assert_awaited_once_with(set_id="s-1", root_id="r-1")


@pytest.mark.asyncio
async def test_package_hierarchy_tool_returns_empty_list_when_no_packages() -> None:
    client = _stub_client(package_hierarchy_result=[])
    tool = _tool_by_name("package_hierarchy")

    result = await tool.handler(client, {"set_id": "empty"})
    import json
    assert json.loads(result) == []


@pytest.mark.asyncio
async def test_list_packages_tool_passes_pagination() -> None:
    pkg = Package(
        id="p-1", name="Pkg 1", parent_package_id=None,
        current_version=1,
        created_at="2026-05-12T00:00:00Z", created_by="u-1",
        updated_at="2026-05-12T00:00:00Z",
    )
    client = _stub_client(list_packages_result=[pkg])
    tool = _tool_by_name("list_packages")

    await tool.handler(client, {
        "set_id": "s-1",
        "page": 2,
        "page_size": 25,
        "parent_package_id": "parent-1",
    })
    client.list_packages.assert_awaited_once_with(
        set_id="s-1",
        collection_id=None,
        parent_package_id="parent-1",
        page=2,
        page_size=25,
    )


@pytest.mark.asyncio
async def test_list_packages_tool_default_pagination() -> None:
    client = _stub_client(list_packages_result=[])
    tool = _tool_by_name("list_packages")

    await tool.handler(client, {"set_id": "s-1"})
    # Defaults: page=1, page_size=50
    client.list_packages.assert_awaited_once_with(
        set_id="s-1",
        collection_id=None,
        parent_package_id=None,
        page=1,
        page_size=50,
    )


def test_package_hierarchy_tool_is_registered() -> None:
    tool = _tool_by_name("package_hierarchy")
    assert tool.name == "package_hierarchy"
    assert "complete package tree" in tool.description.lower() or "table-of-contents" in tool.description.lower()


def test_list_packages_tool_description_mentions_pagination() -> None:
    tool = _tool_by_name("list_packages")
    desc_lower = tool.description.lower()
    assert "page" in desc_lower
    assert "package_hierarchy" in tool.description  # Cross-reference to preferred tool
