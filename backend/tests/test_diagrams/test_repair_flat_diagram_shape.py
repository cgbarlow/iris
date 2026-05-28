"""Tests for the targeted flat-diagram repair script (ADR-218, issue #238).

Exercises the core `repair_diagram` against a real temporary SQLite
database (no mocks, Protocol §9). Validates in-place normalization of
every version, idempotency, dry-run safety, and strict scoping (an
unknown id is reported, never guessed at).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import aiosqlite
import pytest
import pytest_asyncio

from app.db.adapter import SqliteAdapter

_SCRIPT = (
    Path(__file__).resolve().parents[2].parent
    / "scripts"
    / "repair_flat_diagram_shape.py"
)
_spec = importlib.util.spec_from_file_location("repair_flat_diagram_shape", _SCRIPT)
assert _spec and _spec.loader
_repair_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_repair_mod)
repair_diagram = _repair_mod.repair_diagram

_FLAT_DATA = {
    "nodes": [
        {
            "id": "st1",
            "type": "stakeholder",
            "label": "Users",
            "position": {"x": 60, "y": 20},
            "size": {"width": 180, "height": 80},
            "visual": {"bgColor": "#DAE8FC", "borderColor": "#6C8EBF"},
        },
        {
            "id": "goal",
            "type": "goal",
            "label": "Quality services",
            "position": {"x": 300, "y": 160},
            "size": {"width": 260, "height": 80},
            "visual": {},
        },
    ],
    "edges": [{"id": "e1", "type": "influence", "source": "st1", "target": "goal"}],
}


async def _setup(conn: aiosqlite.Connection) -> None:
    await conn.execute(
        "CREATE TABLE diagrams (id TEXT PRIMARY KEY, diagram_type TEXT, "
        "current_version INTEGER, is_deleted INTEGER DEFAULT 0)"
    )
    await conn.execute(
        "CREATE TABLE diagram_versions (diagram_id TEXT, version INTEGER, "
        "data TEXT, PRIMARY KEY (diagram_id, version))"
    )
    await conn.commit()


async def _insert_diagram(
    conn: aiosqlite.Connection, diagram_id: str, *, versions: int, data: dict
) -> None:
    await conn.execute(
        "INSERT INTO diagrams (id, diagram_type, current_version) VALUES (?, ?, ?)",
        (diagram_id, "motivation", versions),
    )
    for v in range(1, versions + 1):
        await conn.execute(
            "INSERT INTO diagram_versions (diagram_id, version, data) VALUES (?, ?, ?)",
            (diagram_id, v, json.dumps(data)),
        )
    await conn.commit()


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        await _setup(conn)
        yield SqliteAdapter(conn), conn


async def _stored(conn: aiosqlite.Connection, diagram_id: str, version: int) -> dict:
    cur = await conn.execute(
        "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = ?",
        (diagram_id, version),
    )
    return json.loads((await cur.fetchone())[0])


class TestRepairDiagram:
    @pytest.mark.asyncio
    async def test_normalizes_all_versions_in_place(self, db) -> None:
        adapter, conn = db
        await _insert_diagram(conn, "d1", versions=2, data=_FLAT_DATA)

        summary = await repair_diagram(adapter, "d1")
        await adapter.commit()

        assert summary["found"] is True
        assert summary["versions_changed"] == [1, 2]
        for v in (1, 2):
            stored = await _stored(conn, "d1", v)
            for node in stored["nodes"]:
                assert isinstance(node["data"], dict)
                assert node["data"]["entityType"]
            assert stored["edges"][0]["data"]["relationshipType"] == "influence"

    @pytest.mark.asyncio
    async def test_visual_relocated_into_data(self, db) -> None:
        adapter, conn = db
        await _insert_diagram(conn, "d1", versions=1, data=_FLAT_DATA)
        await repair_diagram(adapter, "d1")
        await adapter.commit()
        stored = await _stored(conn, "d1", 1)
        assert stored["nodes"][0]["data"]["visual"] == {
            "bgColor": "#DAE8FC",
            "borderColor": "#6C8EBF",
        }

    @pytest.mark.asyncio
    async def test_idempotent_second_run_changes_nothing(self, db) -> None:
        adapter, conn = db
        await _insert_diagram(conn, "d1", versions=1, data=_FLAT_DATA)
        await repair_diagram(adapter, "d1")
        await adapter.commit()
        again = await repair_diagram(adapter, "d1")
        assert again["versions_changed"] == []

    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing(self, db) -> None:
        adapter, conn = db
        await _insert_diagram(conn, "d1", versions=1, data=_FLAT_DATA)
        summary = await repair_diagram(adapter, "d1", dry_run=True)
        assert summary["versions_changed"] == [1]
        stored = await _stored(conn, "d1", 1)
        assert "data" not in stored["nodes"][0]  # untouched

    @pytest.mark.asyncio
    async def test_unknown_id_reported_not_guessed(self, db) -> None:
        adapter, _ = db
        summary = await repair_diagram(adapter, "does-not-exist")
        assert summary["found"] is False

    @pytest.mark.asyncio
    async def test_already_canvas_shaped_no_change(self, db) -> None:
        adapter, conn = db
        canvas_data = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "goal",
                    "position": {"x": 0, "y": 0},
                    "width": 200,
                    "data": {"label": "Already", "entityType": "goal"},
                }
            ],
            "edges": [],
        }
        await _insert_diagram(conn, "d1", versions=1, data=canvas_data)
        summary = await repair_diagram(adapter, "d1")
        assert summary["versions_changed"] == []
