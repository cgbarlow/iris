"""Tests for iris:// resource URIs."""

from __future__ import annotations

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import resources

BASE = "http://iris.test"


class TestResourceList:
    def test_list_includes_all_kinds(self) -> None:
        items = resources.resource_list()
        uris = {str(r.uri) for r in items}
        assert "iris://diagrams/" in uris
        assert "iris://elements/" in uris
        assert "iris://packages/" in uris
        assert "iris://sets/" in uris
        assert "iris://collections/" in uris


class TestResourceRead:
    @pytest.mark.asyncio
    async def test_reads_diagram_as_json(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/export/diagrams/d1").mock(
            return_value=httpx.Response(
                200, content=b'{"schema_version":"1.0"}',
            ),
        )
        body = await resources.resource_read("iris://diagrams/d1", client)
        assert body == '{"schema_version":"1.0"}'

    @pytest.mark.asyncio
    async def test_unknown_scheme_raises(self, client: IrisClient) -> None:
        with pytest.raises(ValueError, match="scheme"):
            await resources.resource_read("https://example.com/x", client)

    @pytest.mark.asyncio
    async def test_malformed_uri_raises(self, client: IrisClient) -> None:
        with pytest.raises(ValueError, match="must have the form"):
            await resources.resource_read("iris://diagrams", client)

    @pytest.mark.asyncio
    async def test_unknown_kind_raises(self, client: IrisClient) -> None:
        with pytest.raises(ValueError, match="Unsupported kind"):
            await resources.resource_read("iris://widgets/x", client)
