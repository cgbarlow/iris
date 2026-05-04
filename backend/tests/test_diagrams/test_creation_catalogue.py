"""Integration tests for the creation catalogue endpoint (ADR-132, SPEC-132-B).

GET /api/registry/creation-catalogue returns the set of
(notation, diagram_type) pairs that AI diagram creation can currently produce,
joined against ai_creation_prompts.
"""

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
    db_manager = DatabaseManager(app_config)
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
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestCreationCatalogueEndpoint:
    @pytest.mark.anyio
    async def test_returns_200(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/creation-catalogue", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_shape_is_items_list(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/creation-catalogue", headers=headers)
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.anyio
    async def test_doview_is_creatable_without_diagram_type(
        self, client: httpx.AsyncClient
    ) -> None:
        """DoView appears exactly once with requires_diagram_type=False and null diagram_type."""
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/creation-catalogue", headers=headers)
        items = resp.json()["items"]
        doview_items = [i for i in items if i["notation"] == "doview"]
        assert len(doview_items) == 1, (
            "DoView must appear exactly once in the catalogue; its internal "
            "prompt branches between outcomes_map and overview without a UI "
            "diagram-type selector."
        )
        entry = doview_items[0]
        assert entry["diagram_type"] is None
        assert entry["requires_diagram_type"] is False
        assert entry["notation_label"]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ("notation", "diagram_type"),
        [
            ("simple", "component"),
            ("simple", "roadmap"),
            ("simple", "free_form"),
            ("uml", "sequence"),
            ("uml", "class"),
            ("archimate", "process"),
            ("c4", "deployment"),
        ],
    )
    async def test_expanded_bundles_present(
        self, client: httpx.AsyncClient, notation: str, diagram_type: str
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/creation-catalogue", headers=headers)
        items = resp.json()["items"]
        match = [
            i for i in items
            if i["notation"] == notation and i["diagram_type"] == diagram_type
        ]
        assert len(match) == 1, (
            f"Expected exactly one entry for {notation}/{diagram_type}, "
            f"got {len(match)}"
        )
        entry = match[0]
        assert entry["requires_diagram_type"] is True
        assert entry["notation_label"]
        assert entry["diagram_type_label"]

    @pytest.mark.anyio
    async def test_every_non_doview_row_requires_diagram_type(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/creation-catalogue", headers=headers)
        items = resp.json()["items"]
        for item in items:
            if item["notation"] == "doview":
                assert item["requires_diagram_type"] is False
                assert item["diagram_type"] is None
            else:
                assert item["requires_diagram_type"] is True
                assert item["diagram_type"] is not None

    @pytest.mark.anyio
    async def test_total_count_after_seed(self, client: httpx.AsyncClient) -> None:
        """After expansion seed: 1 DoView + 7 expanded bundles + 2 BPMN bundles = 10 catalogue entries."""
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/creation-catalogue", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 10, (
            f"Expected 10 creation-catalogue entries "
            f"(1 DoView + 7 expanded bundles + 2 BPMN bundles), got {len(items)}"
        )
