"""Cache behaviour tests for the aggregation engine (ADR-227,
SPEC-227-A).

Covers both layers:
  - Layer 1: per-request memoisation via the request_cache ContextVar.
  - Layer 2: process-wide version-keyed LRU.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.aggregation import engine as _engine
from app.aggregation import engine_cache
from app.aggregation.models import AggregationResult
from app.aggregation.profiles_service import create_aggregation_profile
from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases
from app.diagrams.smart_markdown import compute_smart_markdown_content

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
async def env(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager, dict]]:
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
        # Per-test isolation: every cache test starts with empty caches.
        engine_cache.lru_clear()
        yield c, db_manager, h
    engine_cache.lru_clear()
    await db_manager.close()


# ─────────────────────────────────────────────────────────────────────
# Helpers — set up a minimal status-count rollup
# ─────────────────────────────────────────────────────────────────────


async def _create_set(c, h, name="S") -> str:
    r = await c.post("/api/sets", json={"name": name}, headers=h)
    assert r.status_code == 201
    return r.json()["id"]


async def _create_element(c, h, set_id, name, status) -> str:
    r = await c.post(
        "/api/elements",
        json={
            "name": name, "element_type": "class", "set_id": set_id,
            "metadata": {"status": status},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_smart_md(c, h, set_id, source) -> str:
    r = await c.post(
        "/api/diagrams",
        json={
            "name": "src", "set_id": set_id,
            "diagram_type": "smart_markdown",
            "notation": "markdown",
            "data": {"markdown_source": source},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _setup_status_rollup(c, h, dm) -> tuple[str, str]:
    """Returns (profile_id, source_diagram_id) for a count-by-status
    rollup over two elements with status=Approved and one Proposed."""
    set_id = await _create_set(c, h)
    e1 = await _create_element(c, h, set_id, "A1", "Approved")
    e2 = await _create_element(c, h, set_id, "A2", "Approved")
    e3 = await _create_element(c, h, set_id, "P1", "Proposed")
    source_md = (
        f"- {{{{element:{e1}:name}}}}\n"
        f"- {{{{element:{e2}:name}}}}\n"
        f"- {{{{element:{e3}:name}}}}\n"
    )
    source_id = await _create_smart_md(c, h, set_id, source_md)
    profile = await create_aggregation_profile(
        dm.main_db,
        name="status-count",
        description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "meta/status",
                    "bucket_attribute_path": None,
                    "skip_blank_values": False,
                },
            },
            "output": {
                "group_by": "element.meta.status",
                "aggregation_fn": "count",
                "line_format": "- {element.name}",
                "sort_groups": "alpha",
                "sort_items_within_group": "alpha",
                "show_per_source_breakdown": False,
            },
        },
        is_default_for_set=False,
        created_by=None,
    )
    return profile["id"], source_id


# ─────────────────────────────────────────────────────────────────────
# Layer 1 — per-request memo
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_per_request_dedupes_engine_calls(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Three `aggregation` tokens referencing the same view should run
    `_run_uncached` ONCE per render (Layer 1 hit on second/third)."""
    c, dm, h = env
    profile_id, source_id = await _setup_status_rollup(c, h, dm)
    set_id = await _create_set(c, h, "S2")
    # Build the aggregation_list view binding source + profile.
    view_r = await c.post(
        "/api/diagrams",
        json={
            "name": "rollup", "set_id": set_id,
            "diagram_type": "aggregation_list",
            "notation": "markdown",
            "data": {"source_diagram_id": source_id,
                     "profile_id": profile_id},
        },
        headers=h,
    )
    assert view_r.status_code == 201, view_r.text
    view_id = view_r.json()["id"]
    # Body that references the view three times (two group_counts + one row_count).
    body_id = await _create_smart_md(
        c, h, set_id,
        f"a={{{{aggregation:{view_id}:group_count:Approved}}}} "
        f"p={{{{aggregation:{view_id}:group_count:Proposed}}}} "
        f"n={{{{aggregation:{view_id}:row_count}}}}",
    )

    # The aggregation_list view's POST may have already populated Layer 2.
    # Clear so we can observe the cold path on this render.
    engine_cache.lru_clear()

    with patch.object(
        _engine, "_run_uncached", wraps=_engine._run_uncached,
    ) as spy:
        rendered = await compute_smart_markdown_content(dm.main_db, body_id)

    assert "a=" in rendered
    assert "p=" in rendered
    # One render → one _run_uncached call (Layer 1 dedupe).
    assert spy.call_count == 1, (
        f"_run_uncached called {spy.call_count} times — expected 1"
    )


@pytest.mark.asyncio
async def test_request_cache_isolated_between_tasks() -> None:
    """Two `set_request_cache()` scopes in parallel asyncio tasks do
    not see each other's writes."""

    async def task(value: int) -> int:
        with engine_cache.set_request_cache():
            engine_cache.store_request(("k",), value)
            # Yield to let the other task interleave.
            await asyncio.sleep(0)
            hit = engine_cache.lookup_request(("k",))
            assert hit is not engine_cache.MISSING
            return hit  # type: ignore[return-value]

    results = await asyncio.gather(task(1), task(2))
    assert results == [1, 2]


# ─────────────────────────────────────────────────────────────────────
# Layer 2 — process-wide LRU
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lru_hit_when_sources_unchanged(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Second `engine.run` for the same (profile, source) hits the LRU
    and does NOT enter `_run_uncached`."""
    c, dm, h = env
    profile_id, source_id = await _setup_status_rollup(c, h, dm)

    with patch.object(
        _engine, "_run_uncached", wraps=_engine._run_uncached,
    ) as spy:
        await _engine.run(
            dm.main_db,
            profile_id=profile_id, source_diagram_id=source_id,
        )
        await _engine.run(
            dm.main_db,
            profile_id=profile_id, source_diagram_id=source_id,
        )

    assert spy.call_count == 1


@pytest.mark.asyncio
async def test_lru_miss_when_source_version_bumps(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Bumping the source diagram's current_version invalidates the
    cached entry on the next lookup."""
    c, dm, h = env
    profile_id, source_id = await _setup_status_rollup(c, h, dm)

    with patch.object(
        _engine, "_run_uncached", wraps=_engine._run_uncached,
    ) as spy:
        await _engine.run(
            dm.main_db,
            profile_id=profile_id, source_diagram_id=source_id,
        )
        # Update the source diagram → bumps current_version.
        r = await c.put(
            f"/api/diagrams/{source_id}",
            json={
                "name": "src",
                "data": {"markdown_source": "- changed\n"},
            },
            headers={**h, "If-Match": "1"},
        )
        assert r.status_code == 200, r.text
        await _engine.run(
            dm.main_db,
            profile_id=profile_id, source_diagram_id=source_id,
        )

    assert spy.call_count == 2


@pytest.mark.asyncio
async def test_lru_miss_when_profile_updates(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Bumping the bound profile's `updated_at` invalidates the cached
    entry on the next lookup."""
    c, dm, h = env
    profile_id, source_id = await _setup_status_rollup(c, h, dm)

    with patch.object(
        _engine, "_run_uncached", wraps=_engine._run_uncached,
    ) as spy:
        await _engine.run(
            dm.main_db,
            profile_id=profile_id, source_diagram_id=source_id,
        )
        # Bump the profile's updated_at directly (mirrors what an
        # update endpoint would do).
        await dm.main_db.execute(
            "UPDATE aggregation_profiles SET updated_at = ? WHERE id = ?",
            (datetime.now(tz=UTC).isoformat() + "-touched", profile_id),
        )
        await dm.main_db.commit()
        await _engine.run(
            dm.main_db,
            profile_id=profile_id, source_diagram_id=source_id,
        )

    assert spy.call_count == 2


def test_lru_respects_maxsize() -> None:
    """LRU evicts oldest entries past `maxsize`."""
    engine_cache.lru_clear()
    engine_cache.lru_set_maxsize(3)
    try:
        for i in range(5):
            engine_cache.lru_put(
                (f"p{i}", f"s{i}"),
                AggregationResult(
                    markdown="x",
                    computed_at=str(i),
                    source_versions={f"s{i}": 1},
                ),
            )
        assert engine_cache.lru_size() == 3
        # Two oldest evicted.
        assert engine_cache.lru_get(("p0", "s0")) is None
        assert engine_cache.lru_get(("p1", "s1")) is None
        # Three newest survive.
        assert engine_cache.lru_get(("p2", "s2")) is not None
        assert engine_cache.lru_get(("p3", "s3")) is not None
        assert engine_cache.lru_get(("p4", "s4")) is not None
    finally:
        engine_cache.lru_clear()
        engine_cache.lru_set_maxsize(engine_cache.LRU_MAXSIZE)
