"""v6.6.4 — list_diagrams gains pagination and parent_package_id
filter so MCP / orient-driven callers can fetch root-level diagrams
in a single targeted call.

TDD: written before the client implementation.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient

BASE = "http://iris.test"


class TestListDiagramsPagination:
    @pytest.mark.asyncio
    async def test_default_params_include_page_and_page_size(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json={
                "items": [], "total": 0, "page": 1, "page_size": 50,
            }),
        )
        await pat_client.list_diagrams()
        # Defaults mirror list_packages — page=1, page_size=50.
        params = dict(route.calls.last.request.url.params)
        assert params["page"] == "1"
        assert params["page_size"] == "50"

    @pytest.mark.asyncio
    async def test_passes_page_and_page_size(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json={
                "items": [], "total": 0, "page": 3, "page_size": 25,
            }),
        )
        await pat_client.list_diagrams(set_id="s-1", page=3, page_size=25)
        params = dict(route.calls.last.request.url.params)
        assert params["set_id"] == "s-1"
        assert params["page"] == "3"
        assert params["page_size"] == "25"


class TestListDiagramsParentPackageIdFilter:
    """The orient sheet instructs the model to call
    ``list_diagrams(set_id=..., parent_package_id=null)`` to fetch
    the root-level bracketing diagrams. The client preserves the
    three semantics defined on the backend route:

    - omitted (``None``) → no parent filter sent
    - ``"null"`` → root-level only
    - any other string → that specific parent
    """

    @pytest.mark.asyncio
    async def test_omitted_sends_no_parent_filter(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json={
                "items": [], "total": 0, "page": 1, "page_size": 50,
            }),
        )
        await pat_client.list_diagrams(set_id="s-1")
        params = dict(route.calls.last.request.url.params)
        assert "parent_package_id" not in params

    @pytest.mark.asyncio
    async def test_passes_null_sentinel_for_root_only(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json={
                "items": [], "total": 0, "page": 1, "page_size": 50,
            }),
        )
        await pat_client.list_diagrams(
            set_id="s-1", parent_package_id="null",
        )
        params = dict(route.calls.last.request.url.params)
        assert params["parent_package_id"] == "null"

    @pytest.mark.asyncio
    async def test_passes_specific_parent_uuid(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json={
                "items": [], "total": 0, "page": 1, "page_size": 50,
            }),
        )
        await pat_client.list_diagrams(
            set_id="s-1", parent_package_id="pkg-123",
        )
        params = dict(route.calls.last.request.url.params)
        assert params["parent_package_id"] == "pkg-123"
