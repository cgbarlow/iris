"""Tests for the surface-agnostic import_sparx_model orchestrator (ADR-219).

import_sparx_file (the .qea path) and import_sparx_xml_file (the native
XMI path) both delegate to import_sparx_model. This file exercises the
orchestrator directly with hand-built dataclass lists — no source file —
to prove it persists packages/elements/connectors/diagrams from in-memory
model data, independent of any reader.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.import_sparx.reader import (
    QeaConnector,
    QeaDiagram,
    QeaDiagramObject,
    QeaElement,
    QeaPackage,
)
from app.import_sparx.service import import_sparx_model
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _setup_user(client: httpx.AsyncClient) -> tuple[str, dict[str, str]]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]
    cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
    row = await cursor.fetchone()
    return row[0], headers


def _sample_model() -> dict:
    """A minimal in-memory EA model: 1 package, 2 classes, 1 association, 1 diagram."""
    packages = [QeaPackage(Package_ID=1, Name="Pkg", Parent_ID=0, ea_guid="PKG-1")]
    elements = [
        QeaElement(Object_ID=10, Object_Type="Class", Name="A", Package_ID=1,
                   Note=None, ea_guid="EL-A"),
        QeaElement(Object_ID=11, Object_Type="Class", Name="B", Package_ID=1,
                   Note=None, ea_guid="EL-B"),
    ]
    connectors = [
        QeaConnector(Connector_ID=100, Connector_Type="Association", Name="rel",
                     Start_Object_ID=10, End_Object_ID=11, ea_guid="CN-1"),
    ]
    diagrams = [
        QeaDiagram(Diagram_ID=200, Name="Diag", Diagram_Type="Logical",
                   Package_ID=1, ea_guid="DG-1"),
    ]
    # .qea geometry convention: Top > Bottom (negative Y, screen-up).
    diagram_objects = [
        QeaDiagramObject(Diagram_ID=200, Object_ID=10, RectLeft=100, RectRight=220,
                         RectTop=-100, RectBottom=-160),
        QeaDiagramObject(Diagram_ID=200, Object_ID=11, RectLeft=300, RectRight=420,
                         RectTop=-100, RectBottom=-160),
    ]
    return {
        "packages": packages,
        "elements": elements,
        "connectors": connectors,
        "diagrams": diagrams,
        "diagram_objects": diagram_objects,
        "diagram_links": [],
        "attributes": [],
        "tagged_values": [],
    }


class TestImportSparxModel:
    async def test_orchestrator_persists_model(self, client: httpx.AsyncClient) -> None:
        user_id, _ = await _setup_user(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

        summary = await import_sparx_model(
            db, **_sample_model(), imported_by=user_id, source_label="UnitTest",
        )

        assert summary.packages_created == 1
        assert summary.elements_created == 2
        assert summary.relationships_created == 1
        assert summary.diagrams_created == 1

    async def test_source_label_flows_into_change_summary(
        self, client: httpx.AsyncClient
    ) -> None:
        user_id, _ = await _setup_user(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

        await import_sparx_model(
            db, **_sample_model(), imported_by=user_id, source_label="SparxEA XMI",
        )

        cursor = await db.execute(
            "SELECT COUNT(*) FROM element_versions "
            "WHERE change_summary LIKE 'Imported from SparxEA XMI%'"
        )
        row = await cursor.fetchone()
        assert row[0] == 2

    async def test_idempotent_reimport_skips(self, client: httpx.AsyncClient) -> None:
        user_id, headers = await _setup_user(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]
        # Idempotency (ADR-073) is scoped per set — _build_guid_index filters
        # by set_id, so re-import dedup only applies within a target set.
        set_id = (await client.post(
            "/api/sets", json={"name": "Import target"}, headers=headers,
        )).json()["id"]

        await import_sparx_model(db, **_sample_model(), imported_by=user_id, set_id=set_id)
        second = await import_sparx_model(
            db, **_sample_model(), imported_by=user_id, set_id=set_id,
        )

        # Re-import with identical ea_guids: packages + elements are skipped.
        assert second.packages_skipped == 1
        assert second.elements_skipped == 2
