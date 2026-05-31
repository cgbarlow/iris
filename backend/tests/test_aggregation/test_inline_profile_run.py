"""POST /api/aggregation/run with an inline profile_data draft (SPEC-212-f).

Enables the form-editor's live-preview pane to render a draft profile
that hasn't been saved yet. Mirrors the on-disk profile-id path through
the same engine — no duplication.
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
        debug=True, cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1, argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture
async def env(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, dict]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
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
        yield c, h
    await db_manager.close()


_ATTR_BLUEPRINT = {
    "attributes": [
        {"name": "Quantity", "type": "", "scope": "Public",
         "notes": "", "lower_bound": "", "upper_bound": ""},
        {"name": "Unit", "type": "g", "scope": "Public",
         "notes": "", "lower_bound": "", "upper_bound": ""},
    ],
}


_INLINE_PROFILE = {
    "traversal": {
        "inner": {
            "collect_token_type": "element",
            "value_attribute_path": "attributes/Quantity/type",
            "bucket_attribute_path": "attributes/Unit/type",
            "skip_blank_values": True,
        },
    },
    "output": {
        "group_by": "element.name",
        "sort_groups": "alpha",
        "sort_items_within_group": "alpha",
        "aggregation_fn": "sum",
        "line_format": "- {element.name}: {sum_value}{bucket_spaced}",
        "show_per_source_breakdown": False,
        "breakdown_format": "",
    },
}


async def _seed_source(
    c: httpx.AsyncClient, h: dict,
) -> tuple[str, str]:
    """Create a set + Pork element + smart-markdown diagram referencing
    it twice (so the engine has something to aggregate). Returns
    (set_id, diagram_id)."""
    r = await c.post("/api/sets", json={"name": "S"}, headers=h)
    set_id = r.json()["id"]
    r = await c.post(
        "/api/elements",
        json={
            "name": "Pork mince", "element_type": "class",
            "set_id": set_id, "data": _ATTR_BLUEPRINT,
        },
        headers=h,
    )
    pork_id = r.json()["id"]
    source = (
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}} "
        f"{{{{element:{pork_id}:attr:attributes/Unit/type}}}}\n"
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=300}}}} "
        f"{{{{element:{pork_id}:attr:attributes/Unit/type}}}}"
    )
    r = await c.post(
        "/api/diagrams",
        json={
            "name": "Src", "set_id": set_id,
            "diagram_type": "smart_markdown", "notation": "markdown",
            "data": {"markdown_source": source},
        },
        headers=h,
    )
    return set_id, r.json()["id"]


# ─────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_with_inline_profile_data_renders(
    env: tuple[httpx.AsyncClient, dict],
) -> None:
    """profile_data only — engine runs against the inline draft."""
    c, h = env
    _, diag_id = await _seed_source(c, h)
    r = await c.post(
        "/api/aggregation/run",
        json={
            "profile_data": _INLINE_PROFILE,
            "source_diagram_id": diag_id,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # 500 + 300 = 800 g
    assert "Pork mince: 800 g" in body["markdown"]
    assert body["row_count"] == 1


@pytest.mark.asyncio
async def test_run_inline_profile_does_not_persist(
    env: tuple[httpx.AsyncClient, dict],
) -> None:
    """An inline draft is ephemeral — no profile is created on disk."""
    c, h = env
    _, diag_id = await _seed_source(c, h)
    # Snapshot the profile list before the inline run (the m077 seed
    # ships globals, so we compare deltas — not absolute counts).
    r = await c.get("/api/aggregation/profiles", headers=h)
    before = r.json()["total"]
    await c.post(
        "/api/aggregation/run",
        json={
            "profile_data": _INLINE_PROFILE,
            "source_diagram_id": diag_id,
        },
        headers=h,
    )
    r = await c.get("/api/aggregation/profiles", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == before


# ─────────────────────────────────────────────────────────────────────
# Validation guards
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_rejects_both_profile_id_and_profile_data(
    env: tuple[httpx.AsyncClient, dict],
) -> None:
    """Exactly-one-of contract — passing both is a client error."""
    c, h = env
    _, diag_id = await _seed_source(c, h)
    r = await c.post(
        "/api/aggregation/run",
        json={
            "profile_id": "any-string",
            "profile_data": _INLINE_PROFILE,
            "source_diagram_id": diag_id,
        },
        headers=h,
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_run_rejects_neither_profile_id_nor_profile_data(
    env: tuple[httpx.AsyncClient, dict],
) -> None:
    """Exactly-one-of contract — passing neither is a client error."""
    c, h = env
    _, diag_id = await _seed_source(c, h)
    r = await c.post(
        "/api/aggregation/run",
        json={"source_diagram_id": diag_id},
        headers=h,
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_run_rejects_malformed_inline_profile_data(
    env: tuple[httpx.AsyncClient, dict],
) -> None:
    """Pydantic catches a profile_data that doesn't match ProfileData."""
    c, h = env
    _, diag_id = await _seed_source(c, h)
    r = await c.post(
        "/api/aggregation/run",
        json={
            # Missing required `traversal.inner` and `output`.
            "profile_data": {"traversal": {}},
            "source_diagram_id": diag_id,
        },
        headers=h,
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_run_inline_profile_source_not_found(
    env: tuple[httpx.AsyncClient, dict],
) -> None:
    """The source-diagram 404 path still fires for inline drafts."""
    c, h = env
    await _seed_source(c, h)
    r = await c.post(
        "/api/aggregation/run",
        json={
            "profile_data": _INLINE_PROFILE,
            "source_diagram_id": "non-existent-diagram-id",
        },
        headers=h,
    )
    assert r.status_code == 404, r.text


# ─────────────────────────────────────────────────────────────────────
# Existing profile_id path remains unchanged
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_with_profile_id_still_works(
    env: tuple[httpx.AsyncClient, dict],
) -> None:
    """Backwards compatibility — the on-disk profile_id path is intact."""
    c, h = env
    _, diag_id = await _seed_source(c, h)
    r = await c.post(
        "/api/aggregation/profiles",
        json={
            "name": "Saved profile",
            "is_global": True,
            "profile_data": _INLINE_PROFILE,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    profile_id = r.json()["id"]
    r = await c.post(
        "/api/aggregation/run",
        json={
            "profile_id": profile_id,
            "source_diagram_id": diag_id,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert "Pork mince: 800 g" in r.json()["markdown"]
