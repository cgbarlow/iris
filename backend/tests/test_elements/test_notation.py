"""Tests for element notation field (ADR-081)."""

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


@pytest.mark.anyio
async def test_create_element_with_notation(client: httpx.AsyncClient) -> None:
    """Creating an element with explicit notation stores and returns it."""
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/elements",
        json={
            "element_type": "component",
            "name": "UML Component",
            "description": "A UML element",
            "data": {},
            "notation": "uml",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["notation"] == "uml"


@pytest.mark.anyio
async def test_create_element_default_notation(client: httpx.AsyncClient) -> None:
    """Creating an element without notation defaults to 'simple'."""
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/elements",
        json={
            "element_type": "component",
            "name": "Simple Component",
            "description": "No explicit notation",
            "data": {},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["notation"] == "simple"


@pytest.mark.anyio
async def test_get_element_returns_notation(client: httpx.AsyncClient) -> None:
    """GET /api/elements/{id} returns the notation field."""
    headers = await _auth_headers(client)
    create_resp = await client.post(
        "/api/elements",
        json={
            "element_type": "application_component",
            "name": "ArchiMate Element",
            "description": "",
            "data": {},
            "notation": "archimate",
        },
        headers=headers,
    )
    element_id = create_resp.json()["id"]

    resp = await client.get(f"/api/elements/{element_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notation"] == "archimate"


@pytest.mark.anyio
async def test_list_elements_returns_notation(client: httpx.AsyncClient) -> None:
    """GET /api/elements returns notation for each element in the list."""
    headers = await _auth_headers(client)
    await client.post(
        "/api/elements",
        json={
            "element_type": "person",
            "name": "C4 Person",
            "description": "",
            "data": {},
            "notation": "c4",
        },
        headers=headers,
    )

    resp = await client.get("/api/elements", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    # Find our c4 element in the list (seed data may exist too)
    c4_items = [i for i in items if i["name"] == "C4 Person"]
    assert len(c4_items) == 1
    assert c4_items[0]["notation"] == "c4"
