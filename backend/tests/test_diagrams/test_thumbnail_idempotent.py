"""Tests for content-hashed, idempotent thumbnail regeneration (ADR-242).

Startup regeneration must skip the cairosvg render *and* the DB write for any
``(diagram, theme)`` whose rendered SVG is unchanged, so the free-tier
``iris-api`` stops re-writing ~56 MB of thumbnails to Supabase on every restart.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.diagrams.thumbnail import (
    VALID_THEMES,
    _compute_thumbnail_hash,
    generate_and_store_thumbnail,
    get_thumbnail,
    regenerate_all_thumbnails,
)
from app.startup import initialize_databases

if TYPE_CHECKING:
    from pathlib import Path

    import aiosqlite

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SENTINEL_TS = "1999-01-01T00:00:00+00:00"

_DIAGRAMS_INSERT = (
    "INSERT INTO diagrams "
    "(id, diagram_type, current_version, created_at, created_by, updated_at) "
    "VALUES (?, 'simple-view', 1, ?, ?, ?)"
)
_VERSIONS_INSERT = (
    "INSERT INTO diagram_versions "
    "(diagram_id, version, name, description, data, "
    "change_type, created_at, created_by) "
    "VALUES (?, 1, ?, NULL, ?, 'create', ?, ?)"
)


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


def _node_data(label: str = "T") -> dict:
    return {"nodes": [{"id": "n1", "position": {"x": 0, "y": 0},
                       "data": {"label": label}}]}


async def _insert_diagram(
    db: aiosqlite.Connection, diagram_id: str, data: dict,
) -> None:
    now = datetime.now(tz=UTC).isoformat()
    user_id = "test-user-id"
    cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not await cursor.fetchone():
        cursor = await db.execute("SELECT id FROM roles WHERE name = 'Viewer'")
        role_row = await cursor.fetchone()
        await db.execute(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            (user_id, "testuser", "not-a-real-hash",
             role_row[0] if role_row else "viewer"),
        )
    await db.execute(_DIAGRAMS_INSERT, (diagram_id, now, user_id, now))
    await db.execute(
        _VERSIONS_INSERT, (diagram_id, "T", json.dumps(data), now, user_id),
    )
    await db.commit()


async def _updated_at(
    db: aiosqlite.Connection, diagram_id: str, theme: str,
) -> str | None:
    cursor = await db.execute(
        "SELECT updated_at FROM diagram_thumbnails "
        "WHERE diagram_id = ? AND theme = ?",
        (diagram_id, theme),
    )
    row = await cursor.fetchone()
    return row[0] if row else None


async def _set_sentinel_ts(
    db: aiosqlite.Connection, diagram_id: str, theme: str,
) -> None:
    await db.execute(
        "UPDATE diagram_thumbnails SET updated_at = ? "
        "WHERE diagram_id = ? AND theme = ?",
        (SENTINEL_TS, diagram_id, theme),
    )
    await db.commit()


class TestContentHash:
    def test_hash_is_stable_and_input_sensitive(self) -> None:
        a = _compute_thumbnail_hash("<svg>one</svg>")
        assert a == _compute_thumbnail_hash("<svg>one</svg>")
        assert a != _compute_thumbnail_hash("<svg>two</svg>")
        assert len(a) == 64  # sha256 hex


class TestIdempotentGenerate:
    async def test_second_identical_call_skips_write(
        self, app_config: AppConfig,
    ) -> None:
        """AC1: identical data → True then False, no second write."""
        db_manager = DatabaseManager(app_config)
        await initialize_databases(db_manager)
        db = db_manager.main_db
        await _insert_diagram(db, "d-idem", _node_data("A"))

        wrote_first = await generate_and_store_thumbnail(
            db, "d-idem", _node_data("A"), "simple-view", theme="dark",
        )
        assert wrote_first is True
        await _set_sentinel_ts(db, "d-idem", "dark")

        wrote_second = await generate_and_store_thumbnail(
            db, "d-idem", _node_data("A"), "simple-view", theme="dark",
        )
        assert wrote_second is False
        assert await _updated_at(db, "d-idem", "dark") == SENTINEL_TS
        await db_manager.close()

    async def test_changed_data_regenerates(
        self, app_config: AppConfig,
    ) -> None:
        """AC2: different data → hash differs → regenerates."""
        db_manager = DatabaseManager(app_config)
        await initialize_databases(db_manager)
        db = db_manager.main_db
        await _insert_diagram(db, "d-chg", _node_data("A"))

        await generate_and_store_thumbnail(
            db, "d-chg", _node_data("A"), "simple-view", theme="dark",
        )
        await _set_sentinel_ts(db, "d-chg", "dark")

        wrote = await generate_and_store_thumbnail(
            db, "d-chg", _node_data("DIFFERENT"), "simple-view", theme="dark",
        )
        assert wrote is True
        assert await _updated_at(db, "d-chg", "dark") != SENTINEL_TS
        await db_manager.close()

    async def test_force_always_rewrites(
        self, app_config: AppConfig,
    ) -> None:
        """AC3: force=True rewrites even when unchanged."""
        db_manager = DatabaseManager(app_config)
        await initialize_databases(db_manager)
        db = db_manager.main_db
        await _insert_diagram(db, "d-force", _node_data("A"))

        await generate_and_store_thumbnail(
            db, "d-force", _node_data("A"), "simple-view", theme="dark",
        )
        await _set_sentinel_ts(db, "d-force", "dark")

        wrote = await generate_and_store_thumbnail(
            db, "d-force", _node_data("A"), "simple-view",
            theme="dark", force=True,
        )
        assert wrote is True
        assert await _updated_at(db, "d-force", "dark") != SENTINEL_TS
        await db_manager.close()

    async def test_legacy_null_hash_regenerates_once(
        self, app_config: AppConfig,
    ) -> None:
        """AC4: a row with NULL content_hash regenerates once, then skips."""
        db_manager = DatabaseManager(app_config)
        await initialize_databases(db_manager)
        db = db_manager.main_db
        await _insert_diagram(db, "d-legacy", _node_data("A"))

        # Simulate a pre-ADR-242 row: PNG present, content_hash NULL.
        await db.execute(
            "INSERT OR REPLACE INTO diagram_thumbnails "
            "(diagram_id, theme, thumbnail, updated_at) VALUES (?, ?, ?, ?)",
            ("d-legacy", "dark", b"<svg>legacy</svg>", SENTINEL_TS),
        )
        await db.commit()

        first = await generate_and_store_thumbnail(
            db, "d-legacy", _node_data("A"), "simple-view", theme="dark",
        )
        assert first is True
        thumb = await get_thumbnail(db, "d-legacy", theme="dark")
        assert thumb is not None
        assert thumb != b"<svg>legacy</svg>"  # the legacy bytes were replaced

        await _set_sentinel_ts(db, "d-legacy", "dark")
        second = await generate_and_store_thumbnail(
            db, "d-legacy", _node_data("A"), "simple-view", theme="dark",
        )
        assert second is False
        assert await _updated_at(db, "d-legacy", "dark") == SENTINEL_TS
        await db_manager.close()


class TestIdempotentSweep:
    async def test_second_sweep_writes_nothing(
        self, app_config: AppConfig,
    ) -> None:
        """AC5: a repeat sweep over an unchanged DB performs zero writes."""
        db_manager = DatabaseManager(app_config)
        await initialize_databases(db_manager)
        db = db_manager.main_db
        await _insert_diagram(db, "d-sweep", _node_data("A"))

        # First sweep establishes hashes for every theme.
        await regenerate_all_thumbnails(db)
        for theme in VALID_THEMES:
            await _set_sentinel_ts(db, "d-sweep", theme)

        # Second sweep must skip everything → all sentinels intact.
        await regenerate_all_thumbnails(db)
        for theme in VALID_THEMES:
            assert await _updated_at(db, "d-sweep", theme) == SENTINEL_TS, (
                f"theme {theme} was rewritten by an unchanged sweep"
            )
        await db_manager.close()

    async def test_column_exists_on_fresh_db(
        self, app_config: AppConfig,
    ) -> None:
        """AC7: content_hash column exists after initialisation."""
        db_manager = DatabaseManager(app_config)
        await initialize_databases(db_manager)
        db = db_manager.main_db
        cursor = await db.execute("PRAGMA table_info(diagram_thumbnails)")
        cols = {row[1] for row in await cursor.fetchall()}
        assert "content_hash" in cols
        await db_manager.close()
