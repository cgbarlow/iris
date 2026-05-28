"""Integration tests for canvas-shape normalization on the diagram
write/read paths (ADR-218, issue #238).

These exercise the full FastAPI stack: a flat AI/MCP `data` payload
posted to `create_diagram` / `update_diagram` must round-trip as
Svelte-Flow canvas shape, and a legacy diagram already persisted flat
must be auto-healed on read without mutating storage.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
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
async def app_and_client(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager]]:
    """Yield (client, db_manager) so tests can inject legacy rows."""
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c, db_manager
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _flat_data() -> dict:
    """The flat AI/MCP shape that crashed the canvas in issue #238."""
    return {
        "nodes": [
            {
                "id": "st1",
                "type": "stakeholder",
                "label": "New Zealanders (service users)",
                "position": {"x": 60, "y": 20},
                "size": {"width": 180, "height": 80},
                "visual": {},
            },
            {
                "id": "goal",
                "type": "goal",
                "label": "Create user-focused services",
                "position": {"x": 300, "y": 160},
                "size": {"width": 260, "height": 80},
                "visual": {},
            },
        ],
        "edges": [
            {"id": "e1", "type": "influence", "source": "st1", "target": "goal"},
        ],
    }


def _assert_canvas_shaped(data: dict) -> None:
    nodes = data["nodes"]
    assert len(nodes) == 2
    for node in nodes:
        assert isinstance(node["data"], dict), "node missing data object"
        # The exact access that threw in UnifiedCanvas.svelte:114.
        assert node["data"]["entityType"]
        assert node["data"]["entityType"] != "diagram_frame"
    assert data["edges"][0]["data"]["relationshipType"] == "influence"


class TestCreateNormalizesFlatNodes:
    async def test_posted_flat_nodes_round_trip_canvas_shaped(
        self, app_and_client: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = app_and_client
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "motivation",
                "notation": "archimate",
                "name": "Issue 238 repro",
                "data": _flat_data(),
            },
            headers=headers,
        )
        assert resp.status_code == 201
        diagram_id = resp.json()["id"]
        got = await client.get(f"/api/diagrams/{diagram_id}", headers=headers)
        assert got.status_code == 200
        _assert_canvas_shaped(got.json()["data"])

    async def test_stored_payload_is_canvas_shaped(
        self, app_and_client: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = app_and_client
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "motivation",
                "notation": "archimate",
                "name": "Issue 238 repro",
                "data": _flat_data(),
            },
            headers=headers,
        )
        diagram_id = resp.json()["id"]
        cur = await db_manager.main_db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = 1",
            (diagram_id,),
        )
        stored = json.loads((await cur.fetchone())[0])
        # Write-time normalization means storage itself is canvas-shaped.
        assert isinstance(stored["nodes"][0]["data"], dict)


class TestReadHealsLegacyFlatData:
    async def test_legacy_flat_storage_healed_on_get(
        self, app_and_client: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = app_and_client
        headers = await _auth_headers(client)
        # Create normally, then overwrite the stored version with the
        # legacy flat shape to simulate a pre-fix create_diagram save.
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "motivation",
                "notation": "archimate",
                "name": "Legacy flat",
                "data": {},
            },
            headers=headers,
        )
        diagram_id = resp.json()["id"]
        db = db_manager.main_db
        await db.execute(
            "UPDATE diagram_versions SET data = ? WHERE diagram_id = ? AND version = 1",
            (json.dumps(_flat_data()), diagram_id),
        )
        await db.commit()

        got = await client.get(f"/api/diagrams/{diagram_id}", headers=headers)
        assert got.status_code == 200
        _assert_canvas_shaped(got.json()["data"])

        # Read-time heal is non-destructive: storage stays flat.
        cur = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = 1",
            (diagram_id,),
        )
        stored = json.loads((await cur.fetchone())[0])
        assert "data" not in stored["nodes"][0]


class TestUpdateNormalizesFlatNodes:
    async def test_put_flat_nodes_round_trip_canvas_shaped(
        self, app_and_client: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = app_and_client
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "motivation",
                "notation": "archimate",
                "name": "To update",
                "data": {},
            },
            headers=headers,
        )
        diagram_id = resp.json()["id"]
        version = resp.json()["current_version"]
        put = await client.put(
            f"/api/diagrams/{diagram_id}",
            json={
                "name": "To update",
                "description": None,
                "data": _flat_data(),
                "change_summary": "add flat nodes",
            },
            headers={**headers, "If-Match": str(version)},
        )
        assert put.status_code == 200
        _assert_canvas_shaped(put.json()["data"])
