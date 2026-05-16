"""MCP render_diagram + render_markdown tool tests (ADR-179, v6.2.0).

Covers tool inventory presence, happy paths via respx-mocked backend,
auth-required payload mapping on 401, and web_url attachment from the
client's backend URL.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _artefact_payload(**overrides: object) -> dict[str, object]:
    """Minimal backend ArtefactResponse payload shape."""
    base = {
        "id": "art-9f2c",
        "filename": "test-9f2c.md",
        "mime_type": "text/markdown",
        "size_bytes": 12,
        "source_kind": "render_markdown",
        "source_ref": None,
        "created_at": "2026-05-16T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestInventory:
    def test_new_tools_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert {"render_diagram", "render_markdown"} <= names

    def test_render_diagram_schema(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        schema = defs["render_diagram"].inputSchema
        assert "diagram_id" in schema["properties"]
        assert "format" in schema["properties"]
        assert schema["properties"]["format"]["enum"] == ["md", "docx", "pdf"]

    def test_render_markdown_schema(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        schema = defs["render_markdown"].inputSchema
        assert "markdown" in schema["properties"]
        assert "title" in schema["properties"]
        assert "format" in schema["properties"]
        assert schema["properties"]["format"]["enum"] == ["md", "docx", "pdf"]


class TestRenderDiagram:
    @pytest.mark.asyncio
    async def test_happy_path_md(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/export/diagram/d-1").mock(
            return_value=httpx.Response(
                200,
                json=_artefact_payload(
                    id="art-md-1",
                    filename="d-1.md",
                    source_kind="export_diagram",
                    source_ref="d-1",
                ),
            ),
        )
        result = await tools.dispatch(
            "render_diagram", client,
            {"diagram_id": "d-1", "format": "md"},
        )
        body = json.loads(result[0].text)
        assert body["id"] == "art-md-1"
        assert body["mime_type"] == "text/markdown"
        # web_url attached pointing at backend /api/artefacts/<id>.
        assert body["web_url"] == f"{BASE}/api/artefacts/art-md-1"

    @pytest.mark.asyncio
    async def test_happy_path_pdf(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/export/diagram/d-2").mock(
            return_value=httpx.Response(
                200,
                json=_artefact_payload(
                    id="art-pdf-2",
                    filename="d-2-x.pdf",
                    mime_type="application/pdf",
                    source_kind="export_diagram",
                    source_ref="d-2",
                ),
            ),
        )
        result = await tools.dispatch(
            "render_diagram", client,
            {"diagram_id": "d-2", "format": "pdf"},
        )
        body = json.loads(result[0].text)
        assert body["mime_type"] == "application/pdf"
        assert body["web_url"].endswith("/api/artefacts/art-pdf-2")

    @pytest.mark.asyncio
    async def test_401_returns_auth_required(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/export/diagram/d-1").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "render_diagram", client,
            {"diagram_id": "d-1", "format": "md"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"


class TestRenderMarkdown:
    @pytest.mark.asyncio
    async def test_happy_path_docx(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/export/markdown").mock(
            return_value=httpx.Response(
                200,
                json=_artefact_payload(
                    id="art-docx-3",
                    filename="notes-3a4b.docx",
                    mime_type=(
                        "application/vnd.openxmlformats-"
                        "officedocument.wordprocessingml.document"
                    ),
                    source_kind="render_markdown",
                ),
            ),
        )
        result = await tools.dispatch(
            "render_markdown", client,
            {
                "markdown": "# Notes\n\nbody",
                "title": "Notes",
                "format": "docx",
            },
        )
        body = json.loads(result[0].text)
        assert body["id"] == "art-docx-3"
        assert "wordprocessingml" in body["mime_type"]
        assert body["web_url"] == f"{BASE}/api/artefacts/art-docx-3"

    @pytest.mark.asyncio
    async def test_401_returns_auth_required(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/export/markdown").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "render_markdown", client,
            {"markdown": "x", "title": "T", "format": "md"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"
