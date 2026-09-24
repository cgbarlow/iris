"""PATCH /api/diagrams/{id} — atomic incremental canvas edits (ADR-252,
SPEC-252-A, issue #301).

Covers the acceptance criteria end to end against a real SQLite backend:

- a patch stores the same ``data`` (and the same side effects) as the
  equivalent full ``PUT /api/diagrams/{id}``;
- validation of every op kind, with the failing op's index in the error;
- atomicity: a failing op leaves the diagram, its versions and its
  relationships untouched;
- optimistic concurrency via ``If-Match`` (mismatch → 409 with the current
  version, nothing written);
- ``sync_labels`` fixes stale labels without touching presentation;
- one new diagram version per successful patch;
- collection write-scope (ADR-237/238), plus the hardened compare-and-swap in
  ``update_diagram`` that the patch relies on.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.diagrams.service import patch_diagram, update_diagram
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

_ARCH_PW = "ArchitectPass123!"


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
async def ctx(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, db_manager
    await db_manager.close()


@pytest.fixture
async def client(ctx) -> httpx.AsyncClient:
    return ctx[0]


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


async def _mk_set(
    c: httpx.AsyncClient, h: dict[str, str], name: str = "S",
    collection_id: str | None = None,
) -> str:
    body: dict[str, object] = {"name": name}
    if collection_id:
        body["collection_id"] = collection_id
    r = await c.post("/api/sets", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _mk_el(c: httpx.AsyncClient, h: dict[str, str], set_id: str, name: str) -> str:
    r = await c.post(
        "/api/elements",
        json={"element_type": "object", "name": name, "data": {}, "set_id": set_id,
              "notation": "uml"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _node(nid: str, entity: str | None, label: str, x: int = 0, y: int = 0) -> dict:
    data: dict[str, Any] = {"label": label, "entityType": "object"}
    if entity:
        data["entityId"] = entity
    return {"id": nid, "type": "object", "position": {"x": x, "y": y},
            "width": 200, "height": 86, "data": data}


def _edge(eid: str, source: str, target: str, **data: Any) -> dict:
    return {"id": eid, "source": source, "target": target, "type": "association",
            "sourceHandle": "right", "targetHandle": "left",
            "data": {"relationshipType": "association", **data}}


async def _mk_diagram(
    c: httpx.AsyncClient, h: dict[str, str], set_id: str, data: dict, name: str = "D",
) -> str:
    r = await c.post(
        "/api/diagrams",
        json={"diagram_type": "component", "notation": "uml", "name": name,
              "description": "desc", "data": data, "set_id": set_id,
              "metadata": {"k": "v"}},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _patch(
    c: httpx.AsyncClient, h: dict[str, str], diagram_id: str, ops: list[dict],
    *, if_match: int | str | None = None, change_summary: str | None = None,
) -> httpx.Response:
    headers = dict(h)
    if if_match is not None:
        headers["If-Match"] = str(if_match)
    body: dict[str, Any] = {"operations": ops}
    if change_summary is not None:
        body["change_summary"] = change_summary
    return await c.patch(f"/api/diagrams/{diagram_id}", json=body, headers=headers)


async def _stored(dbm: DatabaseManager, diagram_id: str) -> tuple[int, dict, int]:
    """(current_version, stored data, number of versions) straight from the DB."""
    db = dbm.main_db
    cur = await db.execute(
        "SELECT d.current_version, dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version WHERE d.id = ?",
        (diagram_id,),
    )
    row = await cur.fetchone()
    cnt = await db.execute(
        "SELECT COUNT(*) FROM diagram_versions WHERE diagram_id = ?", (diagram_id,),
    )
    return row[0], json.loads(row[1]), (await cnt.fetchone())[0]


async def _rel_count(dbm: DatabaseManager) -> int:
    cur = await dbm.main_db.execute("SELECT COUNT(*) FROM relationships WHERE is_deleted = 0")
    return (await cur.fetchone())[0]


async def _family(c: httpx.AsyncClient, h: dict[str, str]) -> dict[str, str]:
    s = await _mk_set(c, h)
    ids = {"set": s}
    for key, name in (("a", "Alice"), ("b", "Bob"), ("c", "Carol")):
        ids[key] = await _mk_el(c, h, s, name)
    return ids


def _base_canvas(f: dict[str, str]) -> dict:
    return {
        "nodes": [_node("n1", f["a"], "Alice", 0, 0), _node("n2", f["b"], "Bob", 300, 0)],
        "edges": [],
    }


# ── Acceptance: patch == equivalent full update ───────────────────────


class TestEquivalentToFullUpdate:
    async def test_same_stored_data_and_side_effects(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        patched = await _mk_diagram(client, h, f["set"], _base_canvas(f), "P")
        full = await _mk_diagram(client, h, f["set"], _base_canvas(f), "F")

        ops = [
            {"op": "add_node", "node": _node("n3", f["c"], "Carol", 600, 0)},
            {"op": "add_edge", "edge": _edge("x1", "n1", "n2")},
            {"op": "add_edge", "edge": _edge("x2", "n2", "n3")},
            {"op": "update_node", "id": "n1", "position": {"y": 40},
             "data": {"visual": {"fill": "#fff"}}},
            {"op": "update_edge", "id": "x2", "data": {"sourceRole": "parent"}},
            {"op": "remove_edge", "id": "x1"},
        ]
        resp = await _patch(client, h, patched, ops, if_match=1)
        assert resp.status_code == 200, resp.text

        before_full = await _rel_count(dbm)
        expected = {
            "nodes": [
                {**_node("n1", f["a"], "Alice", 0, 40),
                 "data": {"label": "Alice", "entityType": "object",
                          "entityId": f["a"], "visual": {"fill": "#fff"}}},
                _node("n2", f["b"], "Bob", 300, 0),
                _node("n3", f["c"], "Carol", 600, 0),
            ],
            "edges": [_edge("x2", "n2", "n3", sourceRole="parent")],
        }
        put = await client.put(
            f"/api/diagrams/{full}",
            json={"name": "F", "description": "desc", "data": expected,
                  "metadata": {"k": "v"}},
            headers={**h, "If-Match": "1"},
        )
        assert put.status_code == 200, put.text

        _, patched_data, _ = await _stored(dbm, patched)
        _, full_data, _ = await _stored(dbm, full)
        assert patched_data == full_data == expected

        # Same edge → relationship auto-create as a full update: the patch
        # created B→C (x2) once; the full update found it and made nothing.
        assert await _rel_count(dbm) == before_full
        lst = (await client.get(
            "/api/relationships", params={"set_id": f["set"]}, headers=h,
        )).json()
        pairs = {(r["source_element_id"], r["target_element_id"]) for r in lst["items"]}
        assert pairs == {(f["b"], f["c"])}

        # Name / description / metadata carried over; notations detected.
        p = (await client.get(f"/api/diagrams/{patched}", headers=h)).json()
        q = (await client.get(f"/api/diagrams/{full}", headers=h)).json()
        assert p["description"] == q["description"] == "desc"
        assert p["metadata"] == q["metadata"] == {"k": "v"}
        assert p["detected_notations"] == q["detected_notations"]

    async def test_reversed_relationship_edge_creates_no_duplicate(self, ctx) -> None:
        # ADR-249 either-direction relationshipId skip applies to patches too.
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        rel = await client.post(
            "/api/batch/relationships/create",
            json={"relationships": [{"source_element_id": f["a"],
                                     "target_element_id": f["b"],
                                     "relationship_type": "association"}]},
            headers=h,
        )
        rid = rel.json()["ids"][0]
        before = await _rel_count(dbm)
        resp = await _patch(client, h, d, [
            {"op": "add_edge", "edge": _edge("x1", "n2", "n1", relationshipId=rid)},
        ])
        assert resp.status_code == 200, resp.text
        assert await _rel_count(dbm) == before


# ── Response shape and versioning ────────────────────────────────────


class TestResponseAndVersioning:
    async def test_response_shape_and_one_version(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))

        resp = await _patch(client, h, d, [
            {"op": "add_node", "node": _node("n3", f["c"], "Carol")},
            {"op": "add_edge", "edge": _edge("x1", "n1", "n3")},
            {"op": "remove_node", "id": "n2"},
        ], change_summary="Add Carol")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == d
        assert body["current_version"] == 2
        assert body["applied"] == 3
        assert body["results"] == [
            {"index": 0, "op": "add_node", "id": "n3"},
            {"index": 1, "op": "add_edge", "id": "x1"},
            {"index": 2, "op": "remove_node", "id": "n2", "removed_edges": []},
        ]
        assert "updated_at" in body

        version, _, count = await _stored(dbm, d)
        assert (version, count) == (2, 2)
        versions = (await client.get(f"/api/diagrams/{d}/versions", headers=h)).json()
        latest = next(v for v in versions if v["version"] == 2)
        assert latest["change_type"] == "update"
        assert latest["change_summary"] == "Add Carol"

    async def test_each_patch_is_one_version(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        for i in range(3):
            ops = [{"op": "update_node", "id": "n1", "position": {"x": i}}] * 5
            assert (await _patch(client, h, d, ops)).status_code == 200
        version, _, count = await _stored(dbm, d)
        assert (version, count) == (4, 4)


# ── Atomicity ────────────────────────────────────────────────────────


class TestAtomicity:
    async def test_failing_op_writes_nothing(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        before = await _stored(dbm, d)
        rels = await _rel_count(dbm)

        resp = await _patch(client, h, d, [
            {"op": "add_node", "node": _node("n3", f["c"], "Carol")},
            {"op": "add_edge", "edge": _edge("x1", "n1", "n3")},
            {"op": "remove_edge", "id": "does-not-exist"},
        ])
        assert resp.status_code == 422, resp.text
        detail = resp.json()["detail"]
        assert detail["error"] == "operation_failed"
        assert detail["op_index"] == 2
        assert detail["op"] == "remove_edge"
        assert "does-not-exist" in detail["message"]

        assert await _stored(dbm, d) == before
        assert await _rel_count(dbm) == rels  # the valid A→C edge made nothing

    async def test_non_canvas_diagram_rejected(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        s = await _mk_set(client, h)
        d = await _mk_diagram(client, h, s, {"content": "# Notes"})
        resp = await _patch(client, h, d, [{"op": "sync_labels"}])
        assert resp.status_code == 422
        assert resp.json()["detail"]["op_index"] is None
        assert (await _stored(dbm, d))[2] == 1


# ── Optimistic concurrency ───────────────────────────────────────────


class TestConcurrency:
    async def test_if_match_mismatch_returns_current_version(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        assert (await _patch(client, h, d, [
            {"op": "update_node", "id": "n1", "position": {"x": 5}},
        ])).status_code == 200
        before = await _stored(dbm, d)

        resp = await _patch(client, h, d, [
            {"op": "update_node", "id": "n1", "position": {"x": 9}},
        ], if_match=1)
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["error"] == "version_conflict"
        assert detail["current_version"] == 2
        assert await _stored(dbm, d) == before

    async def test_if_match_current_version_applies(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        resp = await _patch(client, h, d, [
            {"op": "update_node", "id": "n1", "position": {"x": 9}},
        ], if_match=1)
        assert resp.status_code == 200
        assert resp.json()["current_version"] == 2

    async def test_bad_if_match(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        resp = await _patch(client, h, d, [{"op": "sync_labels"}], if_match="abc")
        assert resp.status_code == 400

    async def test_update_diagram_is_compare_and_swap(self, ctx) -> None:
        """A write landing between update_diagram's version read and its
        UPDATE must make it fail (return None) instead of both writers
        claiming the same next version."""
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        racer = _RacingDb(dbm.main_db, d)
        result = await update_diagram(
            racer, d, name="D", description="desc", data=_base_canvas(f),
            change_summary=None, updated_by="u", expected_version=1,
        )
        assert result is None
        version, _, count = await _stored(dbm, d)
        assert (version, count) == (2, 2)  # only the racing write landed

    async def test_patch_without_if_match_retries_on_race(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        racer = _RacingDb(dbm.main_db, d)
        result = await patch_diagram(
            racer, d,
            operations=[{"op": "update_node", "id": "n2", "position": {"x": 999}}],
            change_summary=None, updated_by="u",
        )
        assert result["current_version"] == 3
        _, data, _ = await _stored(dbm, d)
        # Applied on top of the racing write (which moved n1).
        assert data["nodes"][0]["position"]["x"] == 123
        assert data["nodes"][1]["position"]["x"] == 999

    async def test_patch_with_expected_version_does_not_retry(self, ctx) -> None:
        from app.diagrams.service import DiagramVersionConflictError

        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        racer = _RacingDb(dbm.main_db, d)
        with pytest.raises(DiagramVersionConflictError) as info:
            await patch_diagram(
                racer, d,
                operations=[{"op": "update_node", "id": "n2", "position": {"x": 999}}],
                change_summary=None, updated_by="u", expected_version=1,
            )
        assert info.value.current_version == 2
        version, data, _ = await _stored(dbm, d)
        assert version == 2
        assert data["nodes"][1]["position"]["x"] == 300


class _RacingDb:
    """Delegating DB that lands one competing full update of ``diagram_id``
    just before the first ``UPDATE diagrams SET current_version`` it sees —
    i.e. after the caller has read the version but before it writes."""

    def __init__(self, db: Any, diagram_id: str) -> None:
        self._db = db
        self._diagram_id = diagram_id
        self._armed = True

    async def execute(self, query: str, params: tuple = ()) -> Any:
        if self._armed and query.startswith("UPDATE diagrams SET current_version"):
            self._armed = False
            cur = await self._db.execute(
                "SELECT d.current_version, dv.data FROM diagrams d "
                "JOIN diagram_versions dv ON d.id = dv.diagram_id "
                "AND d.current_version = dv.version WHERE d.id = ?",
                (self._diagram_id,),
            )
            version, raw = await cur.fetchone()
            data = json.loads(raw)
            data["nodes"][0]["position"]["x"] = 123
            done = await update_diagram(
                self._db, self._diagram_id, name="D", description="desc",
                data=data, change_summary="racer", updated_by="racer",
                expected_version=version,
            )
            assert done is not None
        return await self._db.execute(query, params)

    async def commit(self) -> None:
        await self._db.commit()


# ── Validation through the route ─────────────────────────────────────


class TestValidation:
    async def test_entity_from_other_set_rejected(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        f = await _family(client, h)
        other = await _mk_set(client, h, "Other")
        stranger = await _mk_el(client, h, other, "Stranger")
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        resp = await _patch(client, h, d, [
            {"op": "add_node", "node": _node("n9", stranger, "Stranger")},
        ])
        assert resp.status_code == 422
        assert resp.json()["detail"]["op_index"] == 0
        # The stranger was not pulled into this diagram's set either.
        el = (await client.get(f"/api/elements/{stranger}", headers=h)).json()
        assert el["set_id"] == other

    async def test_deleted_entity_rejected(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        gone = await _mk_el(client, h, f["set"], "Gone")
        r = await client.delete(f"/api/elements/{gone}", headers={**h, "If-Match": "1"})
        assert r.status_code in (200, 204), r.text
        resp = await _patch(client, h, d, [
            {"op": "add_node", "node": _node("n9", gone, "Gone")},
        ])
        assert resp.status_code == 422

    async def test_relationship_endpoint_mismatch_rejected(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        rel = await client.post(
            "/api/batch/relationships/create",
            json={"relationships": [{"source_element_id": f["a"],
                                     "target_element_id": f["c"],
                                     "relationship_type": "association"}]},
            headers=h,
        )
        rid = rel.json()["ids"][0]
        resp = await _patch(client, h, d, [
            {"op": "add_edge", "edge": _edge("x1", "n1", "n2", relationshipId=rid)},
        ])
        assert resp.status_code == 422
        assert rid in resp.json()["detail"]["message"]

    async def test_operation_count_limits(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        assert (await _patch(client, h, d, [])).status_code == 422
        too_many = [{"op": "update_node", "id": "n1", "position": {"x": 1}}] * 201
        assert (await _patch(client, h, d, too_many)).status_code == 422
        assert (await _patch(client, h, d, too_many[:200])).status_code == 200

    async def test_missing_diagram_404(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        resp = await _patch(client, h, "no-such-diagram", [{"op": "sync_labels"}])
        assert resp.status_code == 404

    async def test_requires_auth(self, ctx) -> None:
        client, _ = ctx
        h = await _auth(client)
        f = await _family(client, h)
        d = await _mk_diagram(client, h, f["set"], _base_canvas(f))
        resp = await client.patch(
            f"/api/diagrams/{d}", json={"operations": [{"op": "sync_labels"}]},
        )
        assert resp.status_code == 401


# ── sync_labels ──────────────────────────────────────────────────────


class TestSyncLabels:
    async def test_fixes_stale_labels_only(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        f = await _family(client, h)
        canvas = _base_canvas(f)
        canvas["nodes"][0]["data"]["visual"] = {"fill": "#abcdef"}
        canvas["nodes"][0]["position"] = {"x": 17, "y": 42}
        canvas["nodes"].append(_node("n3", None, "Free note"))
        canvas["edges"] = [_edge("x1", "n1", "n2")]
        d = await _mk_diagram(client, h, f["set"], canvas)

        r = await client.put(
            f"/api/elements/{f['a']}",
            json={"name": "Alice ⚭ Bob", "description": None, "data": {}},
            headers={**h, "If-Match": "1"},
        )
        assert r.status_code == 200, r.text
        _, before, _ = await _stored(dbm, d)

        resp = await _patch(client, h, d, [{"op": "sync_labels"}])
        assert resp.status_code == 200, resp.text
        assert resp.json()["results"] == [
            {"index": 0, "op": "sync_labels", "ids": ["n1"], "skipped": []},
        ]
        _, after, _ = await _stored(dbm, d)
        assert after["nodes"][0]["data"]["label"] == "Alice ⚭ Bob"
        # Everything else is byte-for-byte what it was.
        after["nodes"][0]["data"]["label"] = before["nodes"][0]["data"]["label"]
        assert after == before


# ── Write-scope (ADR-237/238) ────────────────────────────────────────


class TestWriteScope:
    async def test_scoped_user_outside_collection_forbidden(self, ctx) -> None:
        client, dbm = ctx
        admin = await _auth(client)
        coll_a = (await client.post(
            "/api/collections", json={"name": "A"}, headers=admin,
        )).json()["id"]
        coll_b = (await client.post(
            "/api/collections", json={"name": "B"}, headers=admin,
        )).json()["id"]
        set_a = await _mk_set(client, admin, "in-a", coll_a)
        set_b = await _mk_set(client, admin, "in-b", coll_b)
        da = await _mk_diagram(client, admin, set_a, {"nodes": [], "edges": []})
        db_ = await _mk_diagram(client, admin, set_b, {"nodes": [], "edges": []})

        r = await client.post(
            "/api/users",
            json={"username": "arch", "password": _ARCH_PW, "role": "architect"},
            headers=admin,
        )
        uid = r.json()["id"]
        await dbm.main_db.execute(
            "INSERT INTO user_collection_scope (user_id, collection_id) VALUES (?, ?)",
            (uid, coll_a),
        )
        await dbm.main_db.commit()
        login = await client.post(
            "/api/auth/login", json={"username": "arch", "password": _ARCH_PW},
        )
        arch = {"Authorization": f"Bearer {login.json()['access_token']}"}

        note = {"op": "add_node", "node": _node("n1", None, "Note")}
        assert (await _patch(client, arch, da, [note])).status_code == 200
        denied = await _patch(client, arch, db_, [note])
        assert denied.status_code == 403
        assert (await _stored(dbm, db_))[2] == 1


def test_server_instructions_seed_points_at_patch_diagram() -> None:
    """WORKFLOW GUIDANCE steers agents to patch_diagram for small edits to
    existing diagrams (ADR-252); the iris-mcp fallback mirrors it."""
    from app.seed.creation_prompts import MCP_SERVER_INSTRUCTIONS_BODY

    workflow = MCP_SERVER_INSTRUCTIONS_BODY.split("WORKFLOW GUIDANCE.")[1]
    workflow = workflow.split("AUTH RECOVERY.")[0]
    assert "`patch_diagram`" in workflow
    assert "expected_version" in workflow
    assert "sync_labels" in workflow
