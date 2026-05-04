"""Tests for BPMN 2.0 notation — registry, notation detection, and diagram creation (ADR-136)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.diagrams.notation_detection import BPMN_TYPES, detect_notations
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

class TestBpmnTypesSet:
    def test_bpmn_types_complete(self) -> None:
        # Activities
        assert {"task", "subprocess", "call_activity"} <= BPMN_TYPES
        # Events (4 base types)
        assert {"event_start", "event_intermediate", "event_end", "event_boundary"} <= BPMN_TYPES
        # Gateway
        assert "gateway" in BPMN_TYPES
        # Swimlanes
        assert {"pool", "lane"} <= BPMN_TYPES
        # Data
        assert {"data_object", "data_store"} <= BPMN_TYPES
        # Artifacts
        assert {"group", "text_annotation"} <= BPMN_TYPES

    @pytest.mark.parametrize(
        "entity_type",
        [
            "task", "subprocess", "call_activity",
            "event_start", "event_intermediate", "event_end", "event_boundary",
            "gateway", "pool", "lane", "data_object", "data_store",
            "group", "text_annotation",
        ],
    )
    def test_detect_bpmn_from_each_base_type(self, entity_type: str) -> None:
        data = {"nodes": [{"data": {"entityType": entity_type}}]}
        assert detect_notations(data) == ["bpmn"]

    def test_detect_bpmn_mixed_with_universal(self) -> None:
        """Note + boundary universal types must not change BPMN detection."""
        data = {
            "nodes": [
                {"data": {"entityType": "task"}},
                {"data": {"entityType": "note"}},
                {"data": {"entityType": "boundary"}},
            ]
        }
        assert detect_notations(data) == ["bpmn"]

    def test_detect_bpmn_alongside_uml(self) -> None:
        """A BPMN entity alongside a UML entity yields both notations."""
        data = {
            "nodes": [
                {"data": {"entityType": "task"}},
                {"data": {"entityType": "class"}},
            ]
        }
        result = detect_notations(data)
        assert "bpmn" in result
        assert "uml" in result


# ── Registry integration tests ────────────────────────────────────────────────

class TestBpmnRegistry:
    @pytest.mark.anyio
    async def test_bpmn_notation_exists(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/notations", headers=headers)
        assert resp.status_code == 200
        ids = [n["id"] for n in resp.json()]
        assert "bpmn" in ids

    @pytest.mark.anyio
    async def test_bpmn_notation_display_order_after_doview(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/notations", headers=headers)
        bpmn = next(n for n in resp.json() if n["id"] == "bpmn")
        assert bpmn["display_order"] == 5

    @pytest.mark.anyio
    @pytest.mark.parametrize("dt_id", ["collaboration", "choreography"])
    async def test_new_bpmn_diagram_types_exist(self, client: httpx.AsyncClient, dt_id: str) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        ids = [t["id"] for t in resp.json()]
        assert dt_id in ids

    @pytest.mark.anyio
    @pytest.mark.parametrize("dt_id", ["collaboration", "choreography"])
    async def test_new_bpmn_diagram_types_default_to_bpmn(self, client: httpx.AsyncClient, dt_id: str) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        dt = next(t for t in types if t["id"] == dt_id)
        defaults = [n for n in dt["notations"] if n["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["notation_id"] == "bpmn"

    @pytest.mark.anyio
    async def test_existing_process_type_gets_bpmn_as_option(self, client: httpx.AsyncClient) -> None:
        """`process` already exists from m020. BPMN is added as a non-default option."""
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        process = next(t for t in types if t["id"] == "process")
        notation_ids = [n["notation_id"] for n in process["notations"]]
        assert "bpmn" in notation_ids
        # Default must remain whatever it was (not BPMN), to avoid breaking existing process diagrams.
        bpmn_mapping = next(n for n in process["notations"] if n["notation_id"] == "bpmn")
        assert bpmn_mapping["is_default"] is False


# ── Diagram creation tests ─────────────────────────────────────────────────────

class TestBpmnDiagramCreation:
    @pytest.mark.anyio
    async def test_create_bpmn_process_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "process", "name": "Order to Cash", "notation": "bpmn", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["notation"] == "bpmn"

    @pytest.mark.anyio
    async def test_create_bpmn_collaboration_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "collaboration",
                "name": "Customer ↔ Bank",
                "notation": "bpmn",
                "data": {
                    "nodes": [
                        {"id": "p1", "data": {"entityType": "pool", "label": "Customer"}},
                        {"id": "p2", "data": {"entityType": "pool", "label": "Bank"}},
                    ],
                    "edges": [],
                },
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["diagram_type"] == "collaboration"
        assert body["notation"] == "bpmn"
        # Notation auto-detection should also include bpmn.
        assert "bpmn" in body["detected_notations"]
