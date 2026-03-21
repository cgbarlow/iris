"""Tests for AI diagram creation router endpoints (ADR-094-B)."""

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
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _setup(client: httpx.AsyncClient) -> tuple[dict, str]:
    """Create admin, login, create a set. Returns (headers, set_id)."""
    await client.post("/api/auth/setup", json={"username": "admin", "password": "AdminPass123!"})
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    set_resp = await client.post(
        "/api/sets",
        json={"name": "Test Set", "description": "For creation tests"},
        headers=headers,
    )
    set_id = set_resp.json()["id"]
    return headers, set_id


class TestCreationPromptsAdmin:
    @pytest.mark.anyio
    async def test_list_creation_prompts(self, client: httpx.AsyncClient) -> None:
        headers, _ = await _setup(client)
        resp = await client.get("/api/ai/creation-prompts", headers=headers)
        assert resp.status_code == 200
        prompts = resp.json()
        assert isinstance(prompts, list)
        # Seed prompts should exist
        layers = [p["layer"] for p in prompts]
        assert "base" in layers
        assert "notation" in layers

    @pytest.mark.anyio
    async def test_list_creation_prompts_requires_admin(self, client: httpx.AsyncClient) -> None:
        # Create a non-admin viewer via admin user management
        admin_headers, _ = await _setup(client)
        await client.post(
            "/api/users",
            json={"username": "viewer", "password": "ViewerPass123!", "role": "viewer"},
            headers=admin_headers,
        )
        resp = await client.post("/api/auth/login", json={"username": "viewer", "password": "ViewerPass123!"})
        user_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        resp = await client.get("/api/ai/creation-prompts", headers=user_headers)
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_update_creation_prompt(self, client: httpx.AsyncClient) -> None:
        headers, _ = await _setup(client)
        # Get a prompt to update
        prompts = (await client.get("/api/ai/creation-prompts", headers=headers)).json()
        base_prompt = next(p for p in prompts if p["layer"] == "base")
        resp = await client.put(
            f"/api/ai/creation-prompts/{base_prompt['id']}",
            json={"prompt_text": "Updated base prompt"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["prompt_text"] == "Updated base prompt"

    @pytest.mark.anyio
    async def test_update_nonexistent_prompt_returns_404(self, client: httpx.AsyncClient) -> None:
        headers, _ = await _setup(client)
        resp = await client.put(
            "/api/ai/creation-prompts/nonexistent-id",
            json={"prompt_text": "x"},
            headers=headers,
        )
        assert resp.status_code == 404


class TestApplyDiagramCreation:
    @pytest.mark.anyio
    async def test_apply_creates_diagrams(self, client: httpx.AsyncClient) -> None:
        headers, set_id = await _setup(client)
        diagrams_json = json.dumps({
            "diagrams": [
                {
                    "name": "Test Outcomes Map",
                    "diagram_type": "outcomes_map",
                    "notation": "doview",
                    "nodes": [
                        {
                            "id": "n1",
                            "type": "outcome_box",
                            "label": "Awareness raised",
                            "position": {"x": 100, "y": 100},
                            "size": {"width": 200, "height": 86},
                            "visual": {"bgColor": "#FFF2CC"},
                        }
                    ],
                    "edges": [],
                }
            ]
        })
        resp = await client.post(
            f"/api/ai/sets/{set_id}/create-diagram/apply",
            json={"diagrams_json": diagrams_json},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "diagram_ids" in body
        assert len(body["diagram_ids"]) == 1
        assert "primary_diagram_id" in body

    @pytest.mark.anyio
    async def test_apply_invalid_json_returns_422(self, client: httpx.AsyncClient) -> None:
        headers, set_id = await _setup(client)
        resp = await client.post(
            f"/api/ai/sets/{set_id}/create-diagram/apply",
            json={"diagrams_json": "not valid json {{{"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_apply_missing_diagrams_key_returns_422(self, client: httpx.AsyncClient) -> None:
        headers, set_id = await _setup(client)
        resp = await client.post(
            f"/api/ai/sets/{set_id}/create-diagram/apply",
            json={"diagrams_json": json.dumps({"wrong": "key"})},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_apply_wrong_set_returns_404(self, client: httpx.AsyncClient) -> None:
        headers, _ = await _setup(client)
        resp = await client.post(
            "/api/ai/sets/nonexistent-set/create-diagram/apply",
            json={"diagrams_json": json.dumps({"diagrams": []})},
            headers=headers,
        )
        assert resp.status_code == 404
