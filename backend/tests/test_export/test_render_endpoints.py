"""v6.2.0 (ADR-179, SPEC-179-A): integration tests for the renderer
endpoints — POST /api/export/diagram/{id} and POST /api/export/markdown
plus the GET /api/artefacts/{id} download endpoint.

Re-uses the `client` + `_seed_minimal_entities` fixtures from
`test_routes.py` by importing them indirectly via pytest plugin discovery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

# Re-use the existing fixtures from test_routes by importing them as
# pytest discovers them — `app_config` and `client` live in the same
# package so pytest sees them via conftest semantics.
from tests.test_export.test_routes import _seed_minimal_entities  # noqa: F401
from tests.test_export.test_routes import app_config, client  # noqa: F401

if TYPE_CHECKING:
    pass


pytestmark = pytest.mark.asyncio


class TestRenderMarkdownEndpoint:
    async def test_md_format_returns_md_artefact(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/export/markdown",
            json={"markdown": "# Hello\n\nbody.", "title": "T", "format": "md"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mime_type"] == "text/markdown"
        assert body["filename"].endswith(".md")
        assert body["source_kind"] == "render_markdown"
        # GET the artefact and assert the bytes match.
        got = await client.get(f"/api/artefacts/{body['id']}")
        assert got.status_code == 200
        assert got.content.startswith(b"# Hello")
        assert got.headers["content-type"].startswith("text/markdown")

    async def test_docx_format_returns_valid_docx(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/export/markdown",
            json={"markdown": "# Heading\n\nbody.", "title": "Doc",
                  "format": "docx"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mime_type"] == (
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        )
        assert body["filename"].endswith(".docx")
        got = await client.get(f"/api/artefacts/{body['id']}")
        assert got.status_code == 200
        # docx is a ZIP archive.
        assert got.content.startswith(b"PK\x03\x04")

    async def test_pdf_format_returns_valid_pdf(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/export/markdown",
            json={"markdown": "# T\n\ncontent.", "title": "P", "format": "pdf"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mime_type"] == "application/pdf"
        assert body["filename"].endswith(".pdf")
        got = await client.get(f"/api/artefacts/{body['id']}")
        assert got.status_code == 200
        assert got.content.startswith(b"%PDF")
        # Force download disposition.
        cd = got.headers["content-disposition"]
        assert "attachment" in cd
        assert body["filename"] in cd

    async def test_invalid_format_400(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/export/markdown",
            json={"markdown": "x", "title": "T", "format": "svg"},
        )
        # Pydantic field validation rejects unknown literal at 422.
        assert resp.status_code in (400, 422)


class TestRenderDiagramEndpoint:
    async def test_render_diagram_md(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.post(
            f"/api/export/diagram/{ids['diagram']}",
            json={"format": "md"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mime_type"] == "text/markdown"
        assert body["source_kind"] == "export_diagram"
        assert body["source_ref"] == ids["diagram"]

    async def test_render_diagram_pdf(
        self, client: httpx.AsyncClient,
    ) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.post(
            f"/api/export/diagram/{ids['diagram']}",
            json={"format": "pdf"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mime_type"] == "application/pdf"
        got = await client.get(f"/api/artefacts/{body['id']}")
        assert got.content.startswith(b"%PDF")

    async def test_render_diagram_404_for_missing_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/export/diagram/does-not-exist",
            json={"format": "md"},
        )
        assert resp.status_code == 404


class TestArtefactGetEndpoint:
    async def test_missing_artefact_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/artefacts/missing")
        assert resp.status_code == 404
