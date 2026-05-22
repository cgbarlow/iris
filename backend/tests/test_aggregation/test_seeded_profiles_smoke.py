"""Smoke test: every seeded global aggregation profile is valid and
the engine accepts it against a minimal source diagram. ADR-212.

Doesn't assert specific output (each profile's output shape is its
own concern) — just that profile_data parses against ProfileData and
the engine runs without raising.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.aggregation import engine as _engine
from app.aggregation.models import ProfileData
from app.aggregation.profiles_service import list_aggregation_profiles
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
        debug=True, cors_origins=[],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1, argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture
async def env(app_config: AppConfig) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager, dict]]:
    application = create_app(app_config)
    dm = DatabaseManager(app_config)
    await initialize_databases(dm)
    application.state.db_manager = dm
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        await c.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        resp = await c.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        h = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        yield c, dm, h
    await dm.close()


@pytest.mark.asyncio
async def test_all_five_seeded_profiles_validate_and_run(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, dm, h = env
    items, _ = await list_aggregation_profiles(
        dm.main_db, set_id=None, include_global=True, page=1, page_size=100,
    )
    seeded = {p["name"] for p in items}
    assert {
        "Shopping list", "Sprint points rollup", "Time tracker rollup",
        "Expense report", "Reading log rollup",
    } <= seeded
    # 1. Validate the JSON shape.
    for p in items:
        ProfileData(**p["profile_data"])  # raises if invalid

    # 2. Build a minimal source diagram and run each profile.
    set_resp = await c.post("/api/sets", json={"name": "Smoke"}, headers=h)
    set_id = set_resp.json()["id"]
    diag_resp = await c.post(
        "/api/diagrams",
        json={
            "name": "Empty source", "set_id": set_id,
            "diagram_type": "smart_markdown", "notation": "markdown",
            "data": {"markdown_source": "", "servings": 1},
        },
        headers=h,
    )
    assert diag_resp.status_code == 201
    diag_id = diag_resp.json()["id"]

    for p in items:
        if p["name"] not in {
            "Shopping list", "Sprint points rollup",
            "Time tracker rollup", "Expense report",
            "Reading log rollup",
        }:
            continue
        # Run; should not raise. Empty source → empty markdown is OK.
        result = await _engine.run(
            dm.main_db,
            profile_id=p["id"],
            source_diagram_id=diag_id,
        )
        assert result.row_count == 0, (
            f"Profile '{p['name']}' against empty source returned "
            f"{result.row_count} rows (expected 0)."
        )
