"""Tests for the aggregation_list diagram type (ADR-213, v6.21.0).

The diagram type is a thin synth-on-read wrapper around the
aggregation engine (ADR-212). Storage is `data.source_diagram_id` +
`data.profile_id`; on GET, `data.content` is filled with the
engine's markdown.
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


_VALID_PD = {
    "traversal": {
        "inner": {
            "collect_token_type": "element",
            "value_attribute_path": "attributes/Quantity/type",
            "skip_blank_values": True,
        },
    },
    "output": {
        "group_by": "element.name",
        "line_format": "- {element.name}: {sum_value}",
    },
}


async def _create_diagram(c, h, body) -> dict:
    r = await c.post("/api/diagrams", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_diagram_type_registered_after_migration(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, _, h = env
    r = await c.get("/api/registry/diagram-types", headers=h)
    assert r.status_code == 200, r.text
    types_list = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    ids = {t["id"] for t in types_list}
    assert "aggregation_list" in ids


@pytest.mark.asyncio
async def test_aggregation_list_synth_on_read(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Create an aggregation_list, GET it, content reflects engine output."""
    c, _, h = env
    set_resp = await c.post("/api/sets", json={"name": "S"}, headers=h)
    set_id = set_resp.json()["id"]
    # Create an element with a Quantity attribute.
    el_resp = await c.post(
        "/api/elements",
        json={
            "name": "Pork mince", "element_type": "class", "set_id": set_id,
            "data": {"attributes": [
                {"name": "Quantity", "type": "", "scope": "Public",
                 "notes": "", "lower_bound": "", "upper_bound": ""},
            ]},
        },
        headers=h,
    )
    el_id = el_resp.json()["id"]
    # Source: a smart-markdown diagram with one token = 500.
    src_resp = await c.post(
        "/api/diagrams",
        json={
            "name": "Source", "set_id": set_id,
            "diagram_type": "smart_markdown", "notation": "markdown",
            "data": {
                "markdown_source":
                    f"- {{{{element:{el_id}:attr:attributes/Quantity/type=500}}}}",
            },
        },
        headers=h,
    )
    assert src_resp.status_code == 201
    src_id = src_resp.json()["id"]
    # Profile.
    prof_resp = await c.post(
        "/api/aggregation/profiles",
        json={"name": "Test", "is_global": True, "profile_data": _VALID_PD},
        headers=h,
    )
    prof_id = prof_resp.json()["id"]
    # aggregation_list diagram pointing at both.
    agg = await _create_diagram(c, h, {
        "name": "Agg list", "set_id": set_id,
        "diagram_type": "aggregation_list", "notation": "markdown",
        "data": {"source_diagram_id": src_id, "profile_id": prof_id},
    })
    # GET → content reflects engine output.
    r = await c.get(f"/api/diagrams/{agg['id']}", headers=h)
    assert r.status_code == 200
    content = r.json()["data"]["content"]
    assert "Pork mince: 500" in content


@pytest.mark.asyncio
async def test_missing_source_renders_placeholder(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, _, h = env
    set_resp = await c.post("/api/sets", json={"name": "S"}, headers=h)
    set_id = set_resp.json()["id"]
    prof_resp = await c.post(
        "/api/aggregation/profiles",
        json={"name": "T", "is_global": True, "profile_data": _VALID_PD},
        headers=h,
    )
    prof_id = prof_resp.json()["id"]
    agg = await _create_diagram(c, h, {
        "name": "Missing src", "set_id": set_id,
        "diagram_type": "aggregation_list", "notation": "markdown",
        "data": {
            "source_diagram_id": "00000000-0000-0000-0000-000000000000",
            "profile_id": prof_id,
        },
    })
    r = await c.get(f"/api/diagrams/{agg['id']}", headers=h)
    assert r.status_code == 200
    content = r.json()["data"]["content"]
    assert "Source diagram not found" in content


@pytest.mark.asyncio
async def test_missing_profile_renders_placeholder(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, _, h = env
    set_resp = await c.post("/api/sets", json={"name": "S"}, headers=h)
    set_id = set_resp.json()["id"]
    src = await _create_diagram(c, h, {
        "name": "S", "set_id": set_id,
        "diagram_type": "smart_markdown", "notation": "markdown",
        "data": {"markdown_source": ""},
    })
    agg = await _create_diagram(c, h, {
        "name": "Missing profile", "set_id": set_id,
        "diagram_type": "aggregation_list", "notation": "markdown",
        "data": {
            "source_diagram_id": src["id"],
            "profile_id": "00000000-0000-0000-0000-000000000000",
        },
    })
    r = await c.get(f"/api/diagrams/{agg['id']}", headers=h)
    content = r.json()["data"]["content"]
    assert "Aggregation profile not found" in content


@pytest.mark.asyncio
async def test_unconfigured_renders_pick_placeholder(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """No source/profile set → friendly placeholder, not an error."""
    c, _, h = env
    set_resp = await c.post("/api/sets", json={"name": "S"}, headers=h)
    set_id = set_resp.json()["id"]
    agg = await _create_diagram(c, h, {
        "name": "Empty", "set_id": set_id,
        "diagram_type": "aggregation_list", "notation": "markdown",
        "data": {},
    })
    r = await c.get(f"/api/diagrams/{agg['id']}", headers=h)
    content = r.json()["data"]["content"]
    assert "Pick a source" in content
