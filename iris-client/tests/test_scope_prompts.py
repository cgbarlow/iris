"""ADR-152: iris-client wrapper for the scope-prompt index endpoint."""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient

BASE = "http://iris.test"


class TestListScopePrompts:
    @pytest.mark.asyncio
    async def test_returns_typed_entries(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/prompts/scope-index").mock(
            return_value=httpx.Response(200, json={
                "items": [
                    {
                        "name": "collection:c-1",
                        "scope_type": "collection",
                        "scope_id": "c-1",
                        "scope_name": "NZISM",
                        "description": "Reference",
                        "body": "Cite the control number.",
                    },
                    {
                        "name": "set:s-1",
                        "scope_type": "set",
                        "scope_id": "s-1",
                        "scope_name": "DoView Book",
                        "description": None,
                        "body": "Use outcomes theory framing.",
                    },
                ],
            }),
        )

        result = await pat_client.list_scope_prompts()

        assert route.called
        assert len(result) == 2
        assert result[0].scope_type == "collection"
        assert result[0].name == "collection:c-1"
        assert result[1].scope_type == "set"
        assert result[1].body == "Use outcomes theory framing."

    @pytest.mark.asyncio
    async def test_empty_index(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/prompts/scope-index").mock(
            return_value=httpx.Response(200, json={"items": []}),
        )

        result = await pat_client.list_scope_prompts()
        assert result == []
