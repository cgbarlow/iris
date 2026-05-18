"""Tests for the deleted-source-element case on element templates.

Issue #173 item 3, ADR-197 — when a template's source element is
soft-deleted, the template viewer should clearly say the source is
deleted instead of rendering a link that 404s.

Backend invariant: `source_element_name` returns NULL when the source
element is soft-deleted; `source_element_id` remains populated (it is a
dangling FK by design — no ON DELETE cascade). The frontend then uses
`source_element_name` as the existence signal.

Same fixtures / patterns as test_crud_and_apply.py.
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
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_set(c: httpx.AsyncClient, h: dict, name: str = "S") -> str:
    r = await c.post("/api/sets", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_source_element(c: httpx.AsyncClient, h: dict, set_id: str) -> dict:
    r = await c.post(
        "/api/elements",
        json={
            "element_type": "component",
            "name": "Source",
            "data": {"k": "v"},
            "set_id": set_id,
            "notation": "simple",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _create_template(
    c: httpx.AsyncClient, h: dict, *, source_id: str, set_id: str,
) -> dict:
    r = await c.post(
        "/api/element-templates",
        json={
            "source_element_id": source_id,
            "name": "T",
            "included_fields": ["name", "data"],
            "set_id": set_id,
            "is_global": False,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestGetTemplateAfterSourceSoftDelete:
    async def test_source_element_name_is_null_after_source_deletion(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        source = await _create_source_element(client, h, set_id)
        template = await _create_template(
            client, h, source_id=source["id"], set_id=set_id,
        )

        del_resp = await client.delete(
            f"/api/elements/{source['id']}",
            headers={**h, "If-Match": str(source["current_version"])},
        )
        assert del_resp.status_code == 204, del_resp.text

        get_resp = await client.get(
            f"/api/element-templates/{template['id']}", headers=h,
        )
        assert get_resp.status_code == 200, get_resp.text
        body = get_resp.json()
        assert body["source_element_name"] is None, (
            "source_element_name must be None when source is soft-deleted "
            "so the frontend can show '(source element deleted)'"
        )
        # The id stays populated — dangling FK by design; no ON DELETE cascade
        # was declared in m067_element_templates.
        assert body["source_element_id"] == source["id"]

    async def test_list_endpoint_also_nulls_source_element_name(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        source = await _create_source_element(client, h, set_id)
        await _create_template(
            client, h, source_id=source["id"], set_id=set_id,
        )
        await client.delete(
            f"/api/elements/{source['id']}",
            headers={**h, "If-Match": str(source["current_version"])},
        )

        list_resp = await client.get(
            f"/api/element-templates?set_id={set_id}", headers=h,
        )
        assert list_resp.status_code == 200, list_resp.text
        items = list_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["source_element_name"] is None
        assert items[0]["source_element_id"] == source["id"]

    async def test_source_element_name_present_when_source_visible(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Sanity: the join still produces a name when source is alive."""
        h = await _auth(client)
        set_id = await _create_set(client, h)
        source = await _create_source_element(client, h, set_id)
        template = await _create_template(
            client, h, source_id=source["id"], set_id=set_id,
        )

        get_resp = await client.get(
            f"/api/element-templates/{template['id']}", headers=h,
        )
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["source_element_name"] == "Source"
        assert body["source_element_id"] == source["id"]
