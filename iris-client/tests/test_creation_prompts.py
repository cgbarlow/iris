"""iris-client purpose-aware prompt-fetch methods (ADR-162, SPEC-162-A).

Verifies that `list_response_format_types` and `get_response_prompt`
pass the new `purpose` kwarg through to the backend, defaulting to
`response_format` for backwards compatibility.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient


class TestListResponseFormatTypesPurpose:
    @pytest.mark.asyncio
    async def test_default_sends_purpose_response_format(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(
            "http://iris.test/api/ai/response-prompts/types",
        ).mock(return_value=httpx.Response(200, json=[]))
        await anon_client.list_response_format_types()
        url = route.calls.last.request.url
        assert "purpose=response_format" in str(url)

    @pytest.mark.asyncio
    async def test_creation_format_passes_through(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(
            "http://iris.test/api/ai/response-prompts/types",
        ).mock(return_value=httpx.Response(200, json=[]))
        await anon_client.list_response_format_types(purpose="creation_format")
        url = route.calls.last.request.url
        assert "purpose=creation_format" in str(url)


class TestGetResponsePromptPurpose:
    @pytest.mark.asyncio
    async def test_default_sends_purpose_response_format(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(
            "http://iris.test/api/ai/response-prompts/composed",
        ).mock(return_value=httpx.Response(
            200, json={"notation": "doview", "diagram_type": None, "body": ""},
        ))
        await anon_client.get_response_prompt("doview")
        url = route.calls.last.request.url
        assert "purpose=response_format" in str(url)
        assert "notation=doview" in str(url)

    @pytest.mark.asyncio
    async def test_creation_format_with_diagram_type_passes_through(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(
            "http://iris.test/api/ai/response-prompts/composed",
        ).mock(return_value=httpx.Response(
            200,
            json={
                "notation": "doview",
                "diagram_type": "outcomes_map",
                "body": "Stage 0 — SETUP QUESTIONS...",
            },
        ))
        resp = await anon_client.get_response_prompt(
            "doview", "outcomes_map", purpose="creation_format",
        )
        url = route.calls.last.request.url
        assert "purpose=creation_format" in str(url)
        assert "notation=doview" in str(url)
        assert "diagram_type=outcomes_map" in str(url)
        assert resp.body.startswith("Stage 0")
