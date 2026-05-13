"""create_diagram + list_notations + list_diagram_types tool tests
(ADR-162, SPEC-162-A).

Covers the generic create_diagram tool's happy paths for multiple
notations + the auth_required mapping. Asserts the destination-
confirmation preamble (v5.16.0) AND the creation-flow preamble (v5.17.0)
both appear in the tool description. Also covers the new list_notations
and list_diagram_types discoverability tools.

Includes the assertion that save_doview_analysis's description carries
the deprecation note pointing at create_diagram (v5.17.0 / ADR-162).
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _diagram_payload(**overrides: object) -> dict[str, object]:
    """Minimal payload satisfying the iris-client Diagram model."""
    base = {
        "id": "d-1",
        "name": "X",
        "description": None,
        "diagram_type": "doview_analysis",
        "notation": "markdown",
        "current_version": 1,
        "data": {"content": "# hi"},
        "created_at": "2026-05-12T00:00:00+00:00",
        "updated_at": "2026-05-12T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestInventoryAndDescriptions:
    def test_three_new_tools_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert {"create_diagram", "list_notations", "list_diagram_types"} <= names

    def test_create_diagram_description_carries_both_preambles(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        desc = defs["create_diagram"].description
        # Creation flow preamble (ADR-162)
        assert "CREATION FLOW" in desc
        assert "purpose='creation_format'" in desc
        # Destination preamble (v5.16.0)
        assert "BEFORE CALLING, confirm with the user" in desc

    def test_save_doview_analysis_removed_in_v6(self) -> None:
        # v6.0.0 (ADR-164): save_doview_analysis removed; use
        # create_diagram(notation='markdown', diagram_type='doview_analysis', ...).
        defs = {t.name: t for t in tools.tool_definitions()}
        assert "save_doview_analysis" not in defs

    def test_get_response_prompt_accepts_purpose_argument(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        schema = defs["get_response_prompt"].inputSchema
        assert "purpose" in schema["properties"]
        assert (
            schema["properties"]["purpose"]["enum"]
            == ["response_format", "creation_format"]
        )

    def test_list_response_format_types_accepts_purpose_argument(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        schema = defs["list_response_format_types"].inputSchema
        assert "purpose" in schema["properties"]


class TestCreateDiagram:
    @pytest.mark.asyncio
    async def test_doview_outcomes_map_happy_path(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(
                201,
                json=_diagram_payload(
                    id="d-doview-1",
                    name="Climate 2030",
                    diagram_type="outcomes_map",
                    notation="doview",
                    data={"nodes": [], "edges": []},
                ),
            ),
        )
        result = await tools.dispatch(
            "create_diagram", client,
            {
                "set_id": "set-1",
                "name": "Climate 2030",
                "notation": "doview",
                "diagram_type": "outcomes_map",
                "data": {"nodes": [], "edges": []},
            },
        )
        body = json.loads(result[0].text)
        assert body["id"] == "d-doview-1"
        assert body["notation"] == "doview"

    @pytest.mark.asyncio
    async def test_markdown_doview_analysis_via_create_diagram(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """The deprecated save_doview_analysis path is now reachable via
        the generic create_diagram tool with the same semantics."""
        respx_mock.post(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(
                201,
                json=_diagram_payload(
                    id="d-md-1",
                    name="Analysis of X",
                    diagram_type="doview_analysis",
                    notation="markdown",
                    data={"content": "# analysis"},
                ),
            ),
        )
        result = await tools.dispatch(
            "create_diagram", client,
            {
                "set_id": "set-1",
                "name": "Analysis of X",
                "notation": "markdown",
                "diagram_type": "doview_analysis",
                "data": {"content": "# analysis"},
            },
        )
        body = json.loads(result[0].text)
        assert body["id"] == "d-md-1"

    @pytest.mark.asyncio
    async def test_401_returns_auth_required_payload(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "create_diagram", client,
            {
                "set_id": "set-1",
                "name": "X",
                "diagram_type": "outcomes_map",
            },
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"
        # v6.0.0 (ADR-164): OAuth-setup-guidance — no more next_tool/pairing_url;
        # instead next_step + oauth_resource_metadata_url.
        assert body["next_step"] == "user_signs_in_via_mcp_client_connector_ui"
        assert "/.well-known/oauth-protected-resource" in body["oauth_resource_metadata_url"]


class TestListNotations:
    @pytest.mark.asyncio
    async def test_returns_registry_payload(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/registry/notations").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": "simple", "name": "Simple", "description": None,
                     "display_order": 1, "is_active": True},
                    {"id": "doview", "name": "DoView", "description": None,
                     "display_order": 4, "is_active": True},
                ],
            ),
        )
        result = await tools.dispatch("list_notations", client, {})
        body = json.loads(result[0].text)
        assert isinstance(body, list)
        assert {n["id"] for n in body} == {"simple", "doview"}


class TestListDiagramTypes:
    @pytest.mark.asyncio
    async def test_returns_diagram_types_with_notations(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/registry/diagram-types").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": "outcomes_map",
                        "name": "Outcomes Map",
                        "description": None,
                        "display_order": 0,
                        "is_active": True,
                        "notations": [
                            {"notation_id": "doview", "notation_name": "DoView", "is_default": True},
                        ],
                    },
                ],
            ),
        )
        result = await tools.dispatch("list_diagram_types", client, {})
        body = json.loads(result[0].text)
        assert body[0]["id"] == "outcomes_map"
        assert body[0]["notations"][0]["notation_id"] == "doview"
