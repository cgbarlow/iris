"""ADR-158 (v5.13.0): list_packages accepts pagination + parent_package_id
filter; package_hierarchy returns the full tree as a typed list of
PackageHierarchyNode (one call, no pagination needed).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient

BASE = "http://iris.test"


class TestListPackagesPagination:
    @pytest.mark.asyncio
    async def test_default_params(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/packages").mock(
            return_value=httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50}),
        )
        await pat_client.list_packages()
        assert dict(route.calls.last.request.url.params) == {"page": "1", "page_size": "50"}

    @pytest.mark.asyncio
    async def test_passes_page_and_page_size(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/packages").mock(
            return_value=httpx.Response(200, json={"items": [], "total": 0, "page": 2, "page_size": 25}),
        )
        await pat_client.list_packages(set_id="s-1", page=2, page_size=25)
        params = dict(route.calls.last.request.url.params)
        assert params["page"] == "2"
        assert params["page_size"] == "25"
        assert params["set_id"] == "s-1"

    @pytest.mark.asyncio
    async def test_passes_parent_package_id_filter(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/packages").mock(
            return_value=httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50}),
        )
        await pat_client.list_packages(set_id="s-1", parent_package_id="parent-1")
        params = dict(route.calls.last.request.url.params)
        assert params["parent_package_id"] == "parent-1"


class TestPackageHierarchy:
    @pytest.mark.asyncio
    async def test_returns_typed_nodes(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/packages/hierarchy").mock(
            return_value=httpx.Response(200, json=[
                {
                    "id": "p-A",
                    "name": "Chapter A",
                    "parent_package_id": None,
                    "children": [
                        {"id": "p-A1", "name": "A.1", "parent_package_id": "p-A", "children": []},
                    ],
                },
                {"id": "p-B", "name": "Chapter B", "parent_package_id": None, "children": []},
            ]),
        )

        tree = await pat_client.package_hierarchy(set_id="s-1")
        assert len(tree) == 2
        assert tree[0].name == "Chapter A"
        assert len(tree[0].children) == 1
        assert tree[0].children[0].name == "A.1"
        assert tree[1].name == "Chapter B"
        assert tree[1].children == []

    @pytest.mark.asyncio
    async def test_passes_set_id_and_root_id(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/packages/hierarchy").mock(
            return_value=httpx.Response(200, json=[]),
        )
        await pat_client.package_hierarchy(set_id="s-1", root_id="r-1")
        params = dict(route.calls.last.request.url.params)
        assert params["set_id"] == "s-1"
        assert params["root_id"] == "r-1"

    @pytest.mark.asyncio
    async def test_empty_hierarchy(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/packages/hierarchy").mock(
            return_value=httpx.Response(200, json=[]),
        )
        tree = await pat_client.package_hierarchy(set_id="empty-set")
        assert tree == []


class TestDiagramHierarchyRename:
    @pytest.mark.asyncio
    async def test_diagram_hierarchy_hits_diagrams_endpoint(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """The pre-v5.13.0 `package_hierarchy` method was actually
        hitting /api/diagrams/hierarchy — a latent bug. v5.13.0
        renamed it to `diagram_hierarchy` (its true semantic) and
        added a real `package_hierarchy` that hits the correct path.
        """
        route = respx_mock.get(f"{BASE}/api/diagrams/hierarchy").mock(
            return_value=httpx.Response(200, json={"tree": []}),
        )
        result = await pat_client.diagram_hierarchy(set_id="s-1")
        assert route.called
        assert result == {"tree": []}
