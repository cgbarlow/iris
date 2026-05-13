"""v6.0.15 (ADR-175): the create_* tools must return responses with
`web_url` populated so the model can link the user straight to the new
entity in the Iris UI.

Pre-v6.0.15, every read tool was decorated with `web_url` via
`links.with_web_url(...)` but the create_* tools returned a bare
`model_dump_json()`. The model had to guess the host — and when the
user asked "link me to it" after a successful create_set, it produced
a wrong URL (e.g. `iris.chrisbarlow.nz` instead of
`iris-uat.chrisbarlow.nz`).

These tests pin the decoration on each create_* tool. They use
`respx` to mock iris-api responses, dispatch the MCP tool, and assert
that the resulting JSON contains a correctly-shaped `web_url` field.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"
WEB = "https://iris-uat.chrisbarlow.nz"


@pytest.fixture
def patched_web_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set IRIS_WEB_URL so the decoration produces a populated URL."""
    monkeypatch.setenv("IRIS_WEB_URL", WEB)


class TestCreateCollectionWebUrl:
    @pytest.mark.asyncio
    async def test_response_includes_web_url(
        self,
        patched_web_url: None,
        client: IrisClient,
        respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/collections").mock(
            return_value=httpx.Response(201, json={
                "id": "col-abc",
                "name": "Test Collection",
                "description": None,
                "created_at": "2026-05-13T22:45:57.278151+00:00",
                "updated_at": "2026-05-13T22:45:57.278151+00:00",
                "created_by": "user-1",
                "is_deleted": False,
            }),
        )
        result = await tools.dispatch(
            "create_collection", client, {"name": "Test Collection"},
        )
        body = json.loads(result[0].text)
        assert body["web_url"] == f"{WEB}/collections/col-abc"


class TestCreateSetWebUrl:
    @pytest.mark.asyncio
    async def test_response_includes_web_url(
        self,
        patched_web_url: None,
        client: IrisClient,
        respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/sets").mock(
            return_value=httpx.Response(201, json={
                "id": "set-xyz",
                "name": "claude test",
                "description": None,
                "collection_id": None,
                "created_at": "2026-05-13T22:45:57.278151+00:00",
                "updated_at": "2026-05-13T22:45:57.278151+00:00",
                "created_by": "user-1",
                "is_deleted": False,
            }),
        )
        result = await tools.dispatch(
            "create_set", client, {"name": "claude test"},
        )
        body = json.loads(result[0].text)
        assert body["web_url"] == f"{WEB}/sets/set-xyz"
        # Regression on the original symptom: this is exactly the URL
        # the model would have guessed wrong in v6.0.14 (e.g.
        # `iris.chrisbarlow.nz/sets/...` instead of iris-uat).
        assert "chrisbarlow.nz" in body["web_url"]


class TestCreatePackageWebUrl:
    @pytest.mark.asyncio
    async def test_response_includes_web_url(
        self,
        patched_web_url: None,
        client: IrisClient,
        respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/packages").mock(
            return_value=httpx.Response(201, json={
                "id": "pkg-123",
                "name": "Test Package",
                "description": None,
                "set_id": "set-xyz",
                "parent_package_id": None,
                "current_version": 1,
                "created_at": "2026-05-13T22:45:57.278151+00:00",
                "updated_at": "2026-05-13T22:45:57.278151+00:00",
                "is_deleted": False,
            }),
        )
        result = await tools.dispatch(
            "create_package", client,
            {"name": "Test Package", "set_id": "set-xyz"},
        )
        body = json.loads(result[0].text)
        assert body["web_url"] == f"{WEB}/packages/pkg-123"


class TestCreateDiagramWebUrl:
    @pytest.mark.asyncio
    async def test_response_includes_web_url(
        self,
        patched_web_url: None,
        client: IrisClient,
        respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(201, json={
                "id": "dia-789",
                "name": "Test Diagram",
                "diagram_type": "doview_analysis",
                "notation": "markdown",
                "description": None,
                "set_id": "set-xyz",
                "parent_package_id": None,
                "data": {"content": "# test"},
                "created_at": "2026-05-13T22:45:57.278151+00:00",
                "updated_at": "2026-05-13T22:45:57.278151+00:00",
                "is_deleted": False,
                "tags": [],
                "current_version": 1,
                "set_name": "claude test",
            }),
        )
        result = await tools.dispatch(
            "create_diagram", client,
            {
                "name": "Test Diagram",
                "diagram_type": "doview_analysis",
                "notation": "markdown",
                "set_id": "set-xyz",
                "data": {"content": "# test"},
            },
        )
        body = json.loads(result[0].text)
        assert body["web_url"] == f"{WEB}/views/dia-789"


class TestNoIrisWebUrlNoDecoration:
    """When IRIS_WEB_URL isn't configured (dev), the create_* tools
    return the entity dict unchanged (no `web_url` key). The model
    still gets a usable response; just no link to surface."""

    @pytest.mark.asyncio
    async def test_create_set_without_iris_web_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client: IrisClient,
        respx_mock: respx.Router,
    ) -> None:
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        respx_mock.post(f"{BASE}/api/sets").mock(
            return_value=httpx.Response(201, json={
                "id": "set-dev",
                "name": "dev set",
                "description": None,
                "collection_id": None,
                "created_at": "2026-05-13T22:45:57.278151+00:00",
                "updated_at": "2026-05-13T22:45:57.278151+00:00",
                "created_by": "user-1",
                "is_deleted": False,
            }),
        )
        result = await tools.dispatch(
            "create_set", client, {"name": "dev set"},
        )
        body = json.loads(result[0].text)
        assert "web_url" not in body
        # Other fields untouched.
        assert body["id"] == "set-dev"
