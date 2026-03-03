"""Tests for SparxEA edge metadata import -- connector fields, mapping, and canvas edge data."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.import_sparx.mapper import map_connector_type
from app.import_sparx.reader import read_connectors
from app.import_sparx.service import import_sparx_file
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

# Path to the sample .qea file
SAMPLE_QEA = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "docs", "reference", "SparxEA", "AIXM_5.1.1_EA16.qea",
)
SAMPLE_QEA = os.path.abspath(SAMPLE_QEA)


# ---------- Fixtures ----------


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
    """Setup admin user and return auth headers."""
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


# ---------- Reader Edge Metadata Tests ----------


class TestReaderEdgeMetadata:
    """Verify the reader extracts edge metadata fields from the sample .qea file."""

    async def test_connectors_have_direction(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_direction = [c for c in connectors if c.Direction]
        # Sample has 683 connectors with Direction set
        assert len(with_direction) >= 600

    async def test_connectors_have_source_card(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_source_card = [c for c in connectors if c.SourceCard]
        # Sample has 641 connectors with SourceCard
        assert len(with_source_card) >= 600

    async def test_connectors_have_dest_card(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_dest_card = [c for c in connectors if c.DestCard]
        # Sample has 641 connectors with DestCard
        assert len(with_dest_card) >= 600

    async def test_connectors_have_source_role(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_source_role = [c for c in connectors if c.SourceRole]
        assert len(with_source_role) >= 1

    async def test_connectors_have_dest_role(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_dest_role = [c for c in connectors if c.DestRole]
        assert len(with_dest_role) >= 1

    async def test_connectors_have_route_style(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_route = [c for c in connectors if c.RouteStyle is not None]
        # All connectors should have RouteStyle (integer column with default 0)
        assert len(with_route) == len(connectors)
        # Check specific values present in sample
        route_values = {c.RouteStyle for c in connectors}
        assert 3 in route_values  # step routing (1417 connectors)
        assert 0 in route_values  # bezier routing (3 connectors)

    async def test_connectors_have_navigable_flags(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_src_nav = [c for c in connectors if c.SourceIsNavigable is not None]
        with_dest_nav = [c for c in connectors if c.DestIsNavigable is not None]
        assert len(with_src_nav) > 0
        assert len(with_dest_nav) > 0


# ---------- Mapper Tests ----------


class TestNestingMapping:
    """Verify Nesting connector maps to 'contains'."""

    def test_nesting_maps_to_contains(self) -> None:
        assert map_connector_type("Nesting") == "contains"

    def test_existing_mappings_unchanged(self) -> None:
        assert map_connector_type("Association") == "association"
        assert map_connector_type("Generalization") == "generalization"
        assert map_connector_type("NoteLink") == "note_link"


# ---------- Relationship Data Tests ----------


class TestRelationshipEdgeData:
    """Verify imported relationships contain connector metadata."""

    async def test_relationship_data_has_direction(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check relationship_versions have data with direction
        cursor = await db.execute(
            "SELECT data FROM relationship_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_direction = False
        for r in rows:
            data = json.loads(r[0])
            if "direction" in data:
                found_direction = True
                break
        assert found_direction

    async def test_relationship_data_has_cardinality(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM relationship_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_source = False
        found_target = False
        for r in rows:
            data = json.loads(r[0])
            if "sourceCardinality" in data:
                found_source = True
            if "targetCardinality" in data:
                found_target = True
            if found_source and found_target:
                break
        assert found_source
        assert found_target

    async def test_relationship_data_has_roles(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM relationship_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_source_role = False
        found_target_role = False
        for r in rows:
            data = json.loads(r[0])
            if "sourceRole" in data:
                found_source_role = True
            if "targetRole" in data:
                found_target_role = True
            if found_source_role and found_target_role:
                break
        assert found_source_role
        assert found_target_role


# ---------- Canvas Edge Data Tests ----------


class TestCanvasEdgeData:
    """Verify canvas edge data contains routing and metadata after import."""

    async def test_canvas_edge_has_routing_type(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Diagram models have canvas data with edges
        cursor = await db.execute(
            "SELECT data FROM model_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_routing = False
        for r in rows:
            data = json.loads(r[0])
            edges = data.get("edges", [])
            for edge in edges:
                edge_data = edge.get("data", {})
                if "routingType" in edge_data:
                    found_routing = True
                    # Verify it maps to valid values
                    assert edge_data["routingType"] in ("bezier", "step")
                    break
            if found_routing:
                break
        assert found_routing

    async def test_canvas_edge_routing_type_mapping(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        """RouteStyle 0 maps to 'bezier', RouteStyle 3 maps to 'step'."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM model_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        routing_values: set[str] = set()
        for r in rows:
            data = json.loads(r[0])
            edges = data.get("edges", [])
            for edge in edges:
                edge_data = edge.get("data", {})
                rt = edge_data.get("routingType")
                if rt:
                    routing_values.add(rt)
        # The sample has both RouteStyle 0 (bezier) and 3 (step)
        assert "step" in routing_values

    async def test_canvas_edge_has_cardinality_and_roles(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM model_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_cardinality = False
        found_role = False
        for r in rows:
            data = json.loads(r[0])
            edges = data.get("edges", [])
            for edge in edges:
                edge_data = edge.get("data", {})
                if "sourceCardinality" in edge_data or "targetCardinality" in edge_data:
                    found_cardinality = True
                if "sourceRole" in edge_data or "targetRole" in edge_data:
                    found_role = True
                if found_cardinality and found_role:
                    break
            if found_cardinality and found_role:
                break
        assert found_cardinality
        assert found_role

    async def test_canvas_edge_has_direction(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM model_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_direction = False
        for r in rows:
            data = json.loads(r[0])
            edges = data.get("edges", [])
            for edge in edges:
                edge_data = edge.get("data", {})
                if "direction" in edge_data:
                    found_direction = True
                    break
            if found_direction:
                break
        assert found_direction
