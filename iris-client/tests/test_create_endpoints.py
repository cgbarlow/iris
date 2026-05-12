"""iris-client entity-creation methods (ADR-161, SPEC-161-A).

Covers create_collection, create_set, create_package — the three
write methods added in v5.16.0 to support MCP-side organisation of
new destinations before saving content.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient
from iris_client.exceptions import IrisAuthError
from iris_client.models.core import Collection, IrisSet, Package


class TestCreateCollection:
    @pytest.mark.asyncio
    async def test_happy_path(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post("http://iris.test/api/collections").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "col-1",
                    "name": "Outcomes Work",
                    "description": None,
                    "created_at": "2026-05-12T00:00:00+00:00",
                    "updated_at": "2026-05-12T00:00:00+00:00",
                },
            ),
        )
        result = await pat_client.create_collection(
            "Outcomes Work", description=None,
        )
        assert isinstance(result, Collection)
        assert result.id == "col-1"
        assert result.name == "Outcomes Work"
        sent = route.calls.last.request.content.decode()
        # Optional fields omitted when None.
        assert '"description"' not in sent
        assert '"name":"Outcomes Work"' in sent


class TestCreateSet:
    @pytest.mark.asyncio
    async def test_with_collection_id(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post("http://iris.test/api/sets").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "set-1",
                    "name": "Pilot DoView",
                    "description": "first pilot",
                    "collection_id": "col-1",
                    "created_at": "2026-05-12T00:00:00+00:00",
                    "updated_at": "2026-05-12T00:00:00+00:00",
                },
            ),
        )
        result = await pat_client.create_set(
            "Pilot DoView", collection_id="col-1", description="first pilot",
        )
        assert isinstance(result, IrisSet)
        assert result.id == "set-1"
        sent = route.calls.last.request.content.decode()
        assert '"collection_id":"col-1"' in sent
        assert '"description":"first pilot"' in sent

    @pytest.mark.asyncio
    async def test_top_level_omits_collection_id(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post("http://iris.test/api/sets").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "set-1",
                    "name": "Standalone",
                    "description": None,
                    "collection_id": None,
                    "created_at": "2026-05-12T00:00:00+00:00",
                    "updated_at": "2026-05-12T00:00:00+00:00",
                },
            ),
        )
        await pat_client.create_set("Standalone")
        sent = route.calls.last.request.content.decode()
        assert '"collection_id"' not in sent
        assert '"description"' not in sent


class TestCreatePackage:
    @pytest.mark.asyncio
    async def test_with_set_and_parent(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post("http://iris.test/api/packages").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "pkg-1",
                    "name": "Section A",
                    "description": None,
                    "set_id": "set-1",
                    "parent_package_id": "pkg-root",
                    "metadata": {"order": 1},
                    "current_version": 1,
                    "created_at": "2026-05-12T00:00:00+00:00",
                    "updated_at": "2026-05-12T00:00:00+00:00",
                },
            ),
        )
        result = await pat_client.create_package(
            "Section A",
            set_id="set-1",
            parent_package_id="pkg-root",
            metadata={"order": 1},
        )
        assert isinstance(result, Package)
        sent = route.calls.last.request.content.decode()
        assert '"set_id":"set-1"' in sent
        assert '"parent_package_id":"pkg-root"' in sent
        assert '"metadata"' in sent

    @pytest.mark.asyncio
    async def test_minimal_omits_all_optionals(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post("http://iris.test/api/packages").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "pkg-1",
                    "name": "Loose",
                    "description": None,
                    "set_id": None,
                    "parent_package_id": None,
                    "current_version": 1,
                    "created_at": "2026-05-12T00:00:00+00:00",
                    "updated_at": "2026-05-12T00:00:00+00:00",
                },
            ),
        )
        await pat_client.create_package("Loose")
        sent = route.calls.last.request.content.decode()
        assert '"set_id"' not in sent
        assert '"parent_package_id"' not in sent
        assert '"description"' not in sent
        assert '"metadata"' not in sent


class TestAuthErrorMapping:
    @pytest.mark.asyncio
    async def test_401_raises_iris_auth_error(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post("http://iris.test/api/collections").mock(
            return_value=httpx.Response(
                401, json={"detail": "Not authenticated"},
            ),
        )
        with pytest.raises(IrisAuthError):
            await anon_client.create_collection("Whatever")


class TestPermissiveModel:
    @pytest.mark.asyncio
    async def test_future_server_field_is_tolerated(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post("http://iris.test/api/collections").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "col-1",
                    "name": "X",
                    "description": None,
                    "created_at": "2026-05-12T00:00:00+00:00",
                    "updated_at": "2026-05-12T00:00:00+00:00",
                    "future_server_field": "not yet known",
                },
            ),
        )
        result = await pat_client.create_collection("X")
        assert result.id == "col-1"
