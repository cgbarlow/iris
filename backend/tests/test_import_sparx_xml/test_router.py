"""Tests for POST /api/import/sparx-xml."""

from __future__ import annotations

import os

import httpx

from .conftest import SAMPLE_XMI, auth_headers

OEX_SAMPLE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "docs", "reference", "ArchiMate", "sample-with-view.xml",
    )
)


def _xml_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


class TestImportSparxXmlRouter:
    async def test_import_success(self, client: httpx.AsyncClient) -> None:
        headers = await auth_headers(client)
        resp = await client.post(
            "/api/import/sparx-xml",
            files={"file": ("model.xml", _xml_bytes(SAMPLE_XMI), "application/xml")},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["packages_created"] == 1
        assert body["elements_created"] == 3
        assert body["relationships_created"] == 1
        assert body["diagrams_created"] == 1

    async def test_rejects_wrong_extension(self, client: httpx.AsyncClient) -> None:
        headers = await auth_headers(client)
        resp = await client.post(
            "/api/import/sparx-xml",
            files={"file": ("model.txt", b"<xmi:XMI/>", "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_rejects_non_sparx_xml(self, client: httpx.AsyncClient) -> None:
        """An ArchiMate OEX .xml fails the content sniff."""
        headers = await auth_headers(client)
        resp = await client.post(
            "/api/import/sparx-xml",
            files={"file": ("oex.xml", _xml_bytes(OEX_SAMPLE), "application/xml")},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/import/sparx-xml",
            files={"file": ("model.xml", _xml_bytes(SAMPLE_XMI), "application/xml")},
        )
        assert resp.status_code in (401, 403)

    async def test_rejects_bad_set_id(self, client: httpx.AsyncClient) -> None:
        headers = await auth_headers(client)
        resp = await client.post(
            "/api/import/sparx-xml",
            files={"file": ("model.xml", _xml_bytes(SAMPLE_XMI), "application/xml")},
            data={"set_id": "does-not-exist"},
            headers=headers,
        )
        assert resp.status_code == 400
