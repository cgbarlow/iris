"""Integration tests for new diagram types and notation mappings (ADR-082)."""

from __future__ import annotations

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
    """Setup admin and return auth headers."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestNewDiagramTypes:
    """Verify 6 new diagram types exist in registry after migration."""

    @pytest.mark.anyio
    async def test_new_diagram_types_exist(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        assert resp.status_code == 200
        types = resp.json()
        type_ids = [t["id"] for t in types]
        for expected in ["use_case", "state_machine", "system_context", "container", "motivation", "strategy"]:
            assert expected in type_ids, f"Missing diagram type: {expected}"

    @pytest.mark.anyio
    async def test_total_diagram_type_count(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        # 7 original + 6 new = 13
        assert len(types) == 13


class TestNewNotationMappings:
    """Verify notation mappings for new diagram types."""

    @pytest.mark.anyio
    async def test_use_case_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        use_case = next(t for t in types if t["id"] == "use_case")
        notation_ids = [n["notation_id"] for n in use_case["notations"]]
        assert sorted(notation_ids) == ["simple", "uml"]
        defaults = [n for n in use_case["notations"] if n["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["notation_id"] == "uml"

    @pytest.mark.anyio
    async def test_state_machine_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        sm = next(t for t in types if t["id"] == "state_machine")
        notation_ids = [n["notation_id"] for n in sm["notations"]]
        assert sorted(notation_ids) == ["simple", "uml"]
        defaults = [n for n in sm["notations"] if n["is_default"]]
        assert defaults[0]["notation_id"] == "uml"

    @pytest.mark.anyio
    async def test_system_context_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        sc = next(t for t in types if t["id"] == "system_context")
        notation_ids = [n["notation_id"] for n in sc["notations"]]
        assert sorted(notation_ids) == ["c4", "simple"]
        defaults = [n for n in sc["notations"] if n["is_default"]]
        assert defaults[0]["notation_id"] == "c4"

    @pytest.mark.anyio
    async def test_container_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        ct = next(t for t in types if t["id"] == "container")
        notation_ids = [n["notation_id"] for n in ct["notations"]]
        assert sorted(notation_ids) == ["c4", "simple"]
        defaults = [n for n in ct["notations"] if n["is_default"]]
        assert defaults[0]["notation_id"] == "c4"

    @pytest.mark.anyio
    async def test_motivation_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        mot = next(t for t in types if t["id"] == "motivation")
        notation_ids = [n["notation_id"] for n in mot["notations"]]
        assert notation_ids == ["archimate"]
        assert mot["notations"][0]["is_default"] is True

    @pytest.mark.anyio
    async def test_strategy_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        strat = next(t for t in types if t["id"] == "strategy")
        notation_ids = [n["notation_id"] for n in strat["notations"]]
        assert notation_ids == ["archimate"]
        assert strat["notations"][0]["is_default"] is True


class TestQuickWinMappings:
    """Verify quick-win notation additions to existing diagram types."""

    @pytest.mark.anyio
    async def test_roadmap_has_archimate(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        roadmap = next(t for t in types if t["id"] == "roadmap")
        notation_ids = [n["notation_id"] for n in roadmap["notations"]]
        assert "archimate" in notation_ids
        # Default should still be simple
        defaults = [n for n in roadmap["notations"] if n["is_default"]]
        assert defaults[0]["notation_id"] == "simple"

    @pytest.mark.anyio
    async def test_sequence_has_c4(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        seq = next(t for t in types if t["id"] == "sequence")
        notation_ids = [n["notation_id"] for n in seq["notations"]]
        assert "c4" in notation_ids
        # Default should still be uml
        defaults = [n for n in seq["notations"] if n["is_default"]]
        assert defaults[0]["notation_id"] == "uml"


class TestCreateDiagramsWithNewTypes:
    """Verify diagrams can be created with each new type."""

    @pytest.mark.anyio
    async def test_create_use_case_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "use_case", "name": "Login Use Cases", "notation": "uml", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["diagram_type"] == "use_case"

    @pytest.mark.anyio
    async def test_create_state_machine_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "state_machine", "name": "Order Lifecycle", "notation": "uml", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["diagram_type"] == "state_machine"

    @pytest.mark.anyio
    async def test_create_system_context_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "system_context", "name": "System Overview", "notation": "c4", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["diagram_type"] == "system_context"

    @pytest.mark.anyio
    async def test_create_container_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "container", "name": "Container View", "notation": "c4", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["diagram_type"] == "container"

    @pytest.mark.anyio
    async def test_create_motivation_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "motivation", "name": "Business Drivers", "notation": "archimate", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["diagram_type"] == "motivation"

    @pytest.mark.anyio
    async def test_create_strategy_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "strategy", "name": "Capability Map", "notation": "archimate", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["diagram_type"] == "strategy"
