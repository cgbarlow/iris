"""Tests for DoView notation — registry, notation detection, and diagram creation (ADR-094)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.diagrams.notation_detection import DOVIEW_TYPES, detect_notations
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
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post("/api/auth/setup", json={"username": "admin", "password": "AdminPass123!"})
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Notation detection unit tests ─────────────────────────────────────────────

class TestDoviewTypesSet:
    def test_doview_types_defined(self) -> None:
        assert "outcome_box" in DOVIEW_TYPES
        assert "final_outcome" in DOVIEW_TYPES
        assert "overview_tile" in DOVIEW_TYPES
        assert "source_reference" in DOVIEW_TYPES

    def test_detect_doview_from_outcome_box(self) -> None:
        data = {"nodes": [{"data": {"entityType": "outcome_box"}}]}
        assert detect_notations(data) == ["doview"]

    def test_detect_doview_from_final_outcome(self) -> None:
        data = {"nodes": [{"data": {"entityType": "final_outcome"}}]}
        assert detect_notations(data) == ["doview"]

    def test_detect_doview_from_overview_tile(self) -> None:
        data = {"nodes": [{"data": {"entityType": "overview_tile"}}]}
        assert detect_notations(data) == ["doview"]

    def test_detect_doview_from_source_reference(self) -> None:
        data = {"nodes": [{"data": {"entityType": "source_reference"}}]}
        assert detect_notations(data) == ["doview"]

    def test_detect_doview_mixed_with_universal(self) -> None:
        """Universal types (note, boundary) should not affect detection."""
        data = {
            "nodes": [
                {"data": {"entityType": "outcome_box"}},
                {"data": {"entityType": "note"}},
                {"data": {"entityType": "boundary"}},
            ]
        }
        assert detect_notations(data) == ["doview"]

    def test_detect_doview_not_mixed_with_uml(self) -> None:
        """DoView types alongside UML types yields both notations."""
        data = {
            "nodes": [
                {"data": {"entityType": "outcome_box"}},
                {"data": {"entityType": "class"}},
            ]
        }
        result = detect_notations(data)
        assert "doview" in result
        assert "uml" in result


# ── Registry integration tests ────────────────────────────────────────────────

class TestDoviewRegistry:
    @pytest.mark.anyio
    async def test_doview_notation_exists(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/notations", headers=headers)
        assert resp.status_code == 200
        ids = [n["id"] for n in resp.json()]
        assert "doview" in ids

    @pytest.mark.anyio
    async def test_outcomes_map_diagram_type_exists(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert "outcomes_map" in ids

    @pytest.mark.anyio
    async def test_overview_diagram_type_exists(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        ids = [t["id"] for t in resp.json()]
        assert "overview" in ids

    @pytest.mark.anyio
    async def test_outcomes_map_default_notation_is_doview(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        outcomes_map = next(t for t in types if t["id"] == "outcomes_map")
        defaults = [n for n in outcomes_map["notations"] if n["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["notation_id"] == "doview"

    @pytest.mark.anyio
    async def test_overview_default_notation_is_doview(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        overview = next(t for t in types if t["id"] == "overview")
        defaults = [n for n in overview["notations"] if n["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["notation_id"] == "doview"

    @pytest.mark.anyio
    async def test_free_form_has_doview_notation(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        free_form = next(t for t in types if t["id"] == "free_form")
        notation_ids = [n["notation_id"] for n in free_form["notations"]]
        assert "doview" in notation_ids


# ── Diagram creation tests ─────────────────────────────────────────────────────

class TestDoviewDiagramCreation:
    @pytest.mark.anyio
    async def test_create_outcomes_map_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "outcomes_map", "name": "Climate Action DoView", "notation": "doview", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["diagram_type"] == "outcomes_map"
        assert body["notation"] == "doview"

    @pytest.mark.anyio
    async def test_create_overview_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "overview", "name": "DoView Overview", "notation": "doview", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["diagram_type"] == "overview"
