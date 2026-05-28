"""End-to-end tests for import_sparx_xml_file against a real DB."""

from __future__ import annotations

import json

import httpx

from app.import_sparx_xml.service import import_sparx_xml_file

from .conftest import SAMPLE_XMI, admin_user_id, auth_headers


class TestImportSparxXmlFile:
    async def test_imports_model(self, client: httpx.AsyncClient) -> None:
        await auth_headers(client)
        user_id = await admin_user_id(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

        summary = await import_sparx_xml_file(db, SAMPLE_XMI, imported_by=user_id)

        assert summary.packages_created == 1
        assert summary.elements_created == 3
        assert summary.relationships_created == 1
        assert summary.diagrams_created == 1

    async def test_archimate_stereotype_typed_on_diagram_node(
        self, client: httpx.AsyncClient
    ) -> None:
        await auth_headers(client)
        user_id = await admin_user_id(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

        await import_sparx_xml_file(db, SAMPLE_XMI, imported_by=user_id)

        # The ArchiMate_Capability class must render as a `capability` node.
        cursor = await db.execute(
            "SELECT data FROM diagram_versions ORDER BY version DESC LIMIT 1"
        )
        canvas = json.loads((await cursor.fetchone())[0])
        entity_types = {
            n["data"]["entityType"] for n in canvas["nodes"] if n.get("data")
        }
        assert "capability" in entity_types

    async def test_provenance_label(self, client: httpx.AsyncClient) -> None:
        await auth_headers(client)
        user_id = await admin_user_id(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

        await import_sparx_xml_file(db, SAMPLE_XMI, imported_by=user_id)

        cursor = await db.execute(
            "SELECT COUNT(*) FROM element_versions "
            "WHERE change_summary LIKE 'Imported from SparxEA XMI%'"
        )
        assert (await cursor.fetchone())[0] == 3

    async def test_idempotent_reimport(self, client: httpx.AsyncClient) -> None:
        headers = await auth_headers(client)
        user_id = await admin_user_id(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]
        set_id = (await client.post(
            "/api/sets", json={"name": "XMI target"}, headers=headers,
        )).json()["id"]

        await import_sparx_xml_file(db, SAMPLE_XMI, imported_by=user_id, set_id=set_id)
        second = await import_sparx_xml_file(
            db, SAMPLE_XMI, imported_by=user_id, set_id=set_id
        )
        assert second.packages_skipped == 1
        assert second.elements_skipped == 3
