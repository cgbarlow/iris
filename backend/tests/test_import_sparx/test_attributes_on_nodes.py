"""Tests for attributes appearing on canvas nodes after SparxEA import (ADR-086)."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.import_sparx.service import import_sparx_file
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

SAMPLE_QEA = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "docs", "reference", "SparxEA", "AIXM_5.1.1_EA16.qea",
))


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
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
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
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestAttributesOnCanvasNodes:
    """Verify imported diagram nodes include element attributes."""

    @pytest.mark.anyio
    async def test_nodes_have_attributes(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        """After import, at least some canvas nodes should have data.attributes."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_attributes = False
        for r in rows:
            data = json.loads(r[0])
            nodes = data.get("nodes", [])
            for node in nodes:
                node_data = node.get("data", {})
                if "attributes" in node_data and len(node_data["attributes"]) > 0:
                    found_attributes = True
                    # Verify attribute structure
                    attr = node_data["attributes"][0]
                    assert "name" in attr
                    assert "type" in attr
                    break
            if found_attributes:
                break
        assert found_attributes, "No canvas nodes found with attributes after import"

    @pytest.mark.anyio
    async def test_attributes_have_scope(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        """Attributes should include scope field for visibility prefix rendering."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_scope = False
        for r in rows:
            data = json.loads(r[0])
            nodes = data.get("nodes", [])
            for node in nodes:
                node_data = node.get("data", {})
                attrs = node_data.get("attributes", [])
                for attr in attrs:
                    if isinstance(attr, dict) and "scope" in attr:
                        found_scope = True
                        break
                if found_scope:
                    break
            if found_scope:
                break
        assert found_scope, "No attributes found with scope field"
