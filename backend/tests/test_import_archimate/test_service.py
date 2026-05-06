"""End-to-end tests for the OEX import service.

Spins up a real iris app with a fresh sqlite db (per-test tmp dir), runs
``import_oex_file`` against the committed fixtures, and asserts on the
persisted state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.import_archimate.service import import_oex_file
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

REF = Path(__file__).resolve().parents[3] / "docs" / "reference" / "ArchiMate"
SAMPLE = str(REF / "sample-with-view.xml")
MSD = str(REF / "msd-map.xml")


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
async def client(app_config: AppConfig) -> "AsyncIterator[httpx.AsyncClient]":
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _user_id(client: httpx.AsyncClient) -> str:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]
    cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
    row = await cursor.fetchone()
    return row[0]


async def test_imports_sample_with_view_using_provided_layout(
    client: httpx.AsyncClient,
) -> None:
    user_id = await _user_id(client)
    db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

    summary = await import_oex_file(db, SAMPLE, imported_by=user_id)

    assert summary.elements_created == 3
    assert summary.relationships_created == 2
    assert summary.diagrams_created == 1
    assert summary.elements_skipped == 0
    assert summary.relationships_skipped == 0
    # No auto-layout warning when source had a view.
    assert not any(w.category == "auto_layout" for w in summary.warnings)

    # Verify the diagram persisted with correct notation + node entityType.
    cursor = await db.execute(
        "SELECT dv.data, d.notation FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0"
    )
    row = await cursor.fetchone()
    assert row is not None
    data = json.loads(row[0])
    assert row[1] == "archimate"
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2
    entity_types = {n["data"]["entityType"] for n in data["nodes"]}
    assert entity_types == {
        "business_actor", "business_process", "application_service",
    }
    # Coordinates from the OEX file are preserved (not auto-laid-out).
    customer_node = next(
        n for n in data["nodes"] if n["data"]["entityType"] == "business_actor"
    )
    assert customer_node["position"] == {"x": 40, "y": 40}


async def test_imports_msd_real_world_with_auto_overview(
    client: httpx.AsyncClient,
) -> None:
    """Model-only OEX (no views) → one auto-generated Overview diagram."""
    user_id = await _user_id(client)
    db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

    summary = await import_oex_file(db, MSD, imported_by=user_id)

    assert summary.elements_created == 127
    assert summary.relationships_created == 977
    assert summary.diagrams_created == 1
    assert summary.elements_skipped == 0
    # Auto-layout warning recorded.
    assert any(w.category == "auto_layout" for w in summary.warnings)

    # Pull the synthesised Overview and assert structure.
    cursor = await db.execute(
        "SELECT dv.name, dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0"
    )
    row = await cursor.fetchone()
    assert row is not None
    name = row[0]
    data = json.loads(row[1])
    assert "Overview" in name
    # Every imported element gets a node.
    assert len(data["nodes"]) == 127
    # Every imported relationship becomes an edge.
    assert len(data["edges"]) == 977
    # Grid layout: ceil(sqrt(127)) == 12 columns; positions are deterministic
    # multiples of the cell size.
    xs = [n["position"]["x"] for n in data["nodes"]]
    ys = [n["position"]["y"] for n in data["nodes"]]
    assert max(xs) == 11 * 220  # 0..11 columns => x ∈ {0, 220, ..., 11*220}
    assert min(xs) == 0
    assert min(ys) == 0
    # All five distinct iris element types are represented.
    iris_types = {n["data"]["entityType"] for n in data["nodes"]}
    assert iris_types == {
        "business_service", "business_object", "business_process",
        "business_function", "constraint_archimate",
    }


async def test_unmapped_element_type_is_warned_not_fatal(
    client: httpx.AsyncClient, tmp_path: Path,
) -> None:
    user_id = await _user_id(client)
    db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

    fixture = tmp_path / "with_unknown.xml"
    fixture.write_text(
        '<?xml version="1.0"?>'
        '<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" identifier="m">'
        '<name>Mixed</name>'
        '<elements>'
        '<element identifier="ok" xsi:type="BusinessActor"><name>A</name></element>'
        '<element identifier="bad" xsi:type="MadeUpType"><name>B</name></element>'
        '</elements></model>'
    )
    summary = await import_oex_file(db, str(fixture), imported_by=user_id)
    assert summary.elements_created == 1
    assert summary.elements_skipped == 1
    assert any(
        w.category == "unmapped_element_type" for w in summary.warnings
    )
