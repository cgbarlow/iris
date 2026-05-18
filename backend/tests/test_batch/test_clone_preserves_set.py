"""Regression test: batch clone preserves source element's set_id.

Issue #173 item 1, ADR-198 — locks in the invariant that
`batch_clone_elements` reads the source element's `set_id` and
re-uses it on the clone. The frontend single-element clone path
on /elements/{id} had a separate but related bug (didn't pass
set_id in the request) which is fixed in the same PR; this test
guards the backend side so we don't regress that too.

Same fixture pattern as test_operations.py.
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


class TestBatchCloneSetPreservation:
    async def test_clone_inherits_source_set_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)

        set_resp = await client.post(
            "/api/sets", json={"name": "TargetSet"}, headers=h,
        )
        assert set_resp.status_code == 201
        target_set_id = set_resp.json()["id"]

        src_resp = await client.post(
            "/api/elements",
            json={
                "element_type": "component",
                "name": "SourceInSet",
                "data": {},
                "set_id": target_set_id,
            },
            headers=h,
        )
        assert src_resp.status_code == 201
        src_id = src_resp.json()["id"]

        clone_resp = await client.post(
            "/api/batch/elements/clone",
            json={"ids": [src_id]},
            headers=h,
        )
        assert clone_resp.status_code == 200
        assert clone_resp.json()["succeeded"] == 1

        list_resp = await client.get(
            f"/api/elements?set_id={target_set_id}", headers=h,
        )
        items = list_resp.json()["items"]
        names = [e["name"] for e in items]
        assert "SourceInSet" in names
        assert "SourceInSet (Copy)" in names, (
            "Clone must land in the source's set, not the default set "
            "(issue #173 item 1)."
        )
