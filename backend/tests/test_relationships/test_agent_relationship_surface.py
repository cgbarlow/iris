"""ADR-249 / SPEC-249-A (v6.50.0, issue #298): relationship write surface
for MCP + CLI agents.

Covers the backend half:

- ``POST /api/batch/relationships/create`` — bulk create (<=100) with
  per-item failure isolation, UML role names mapped to the canvas/Sparx
  convention (``data.sourceRole`` / ``data.targetRole``), and validation
  that rejects self-referencing and cross-set relationships.
- ``PUT /api/relationships/{id}`` — ``relationship_type`` is now updatable
  (omit to keep), plus optional ``source_role`` / ``target_role``.
- ``GET /api/relationships`` — new ``set_id`` and ``relationship_type``
  filters; every item carries ``source_role`` / ``target_role`` + ``data``.
- Returned ids are usable as ``relationshipId`` on diagram edges without
  the edge auto-create creating a duplicate.
- Existing flows are untouched: the single ``POST /api/relationships``
  (used by the canvas, whose self-loop edges are a supported feature)
  still accepts a reflexive relationship.
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


async def _mk_el(
    c: httpx.AsyncClient, h: dict[str, str], set_id: str, name: str,
) -> str:
    r = await c.post(
        "/api/elements",
        json={"element_type": "class", "name": name, "data": {}, "set_id": set_id,
              "notation": "uml"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _batch(
    c: httpx.AsyncClient, h: dict[str, str], items: list[dict[str, object]],
) -> httpx.Response:
    return await c.post(
        "/api/batch/relationships/create",
        json={"relationships": items},
        headers=h,
    )


# ── Batch create ─────────────────────────────────────────────────────


class TestBatchCreateRelationships:
    async def test_creates_all_and_returns_ids(self, client) -> None:
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        cc = await _mk_el(client, h, s, "C")

        resp = await _batch(client, h, [
            {"source_element_id": a, "target_element_id": b,
             "relationship_type": "association"},
            {"source_element_id": b, "target_element_id": cc,
             "relationship_type": "dependency", "label": "calls"},
        ])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["succeeded"] == 2
        assert body["failed"] == 0
        assert body["errors"] == []
        assert len(body["ids"]) == 2

        got = await client.get(f"/api/relationships/{body['ids'][1]}", headers=h)
        assert got.status_code == 200
        rel = got.json()
        assert rel["source_element_id"] == b
        assert rel["target_element_id"] == cc
        assert rel["relationship_type"] == "dependency"
        assert rel["label"] == "calls"
        assert rel["current_version"] == 1

    async def test_roles_map_to_canvas_sparx_convention(self, client) -> None:
        """source_role / target_role land in data.sourceRole / data.targetRole —
        the exact keys the Sparx importer writes and the canvas renders."""
        h = await _auth(client)
        s = await _mk_set(client, h)
        fam = await _mk_el(client, h, s, "Family")
        kid = await _mk_el(client, h, s, "Kid")

        resp = await _batch(client, h, [{
            "source_element_id": fam, "target_element_id": kid,
            "relationship_type": "association",
            "source_role": "family", "target_role": "child",
            "data": {"gedcom_role": "CHIL", "child_order": 1},
        }])
        assert resp.json()["succeeded"] == 1, resp.text
        rid = resp.json()["ids"][0]
        rel = (await client.get(f"/api/relationships/{rid}", headers=h)).json()
        assert rel["data"] == {
            "gedcom_role": "CHIL", "child_order": 1,
            "sourceRole": "family", "targetRole": "child",
        }
        assert rel["source_role"] == "family"
        assert rel["target_role"] == "child"

    async def test_explicit_role_wins_over_data_key(self, client) -> None:
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        resp = await _batch(client, h, [{
            "source_element_id": a, "target_element_id": b,
            "relationship_type": "association",
            "source_role": "partner",
            "data": {"sourceRole": "stale"},
        }])
        rid = resp.json()["ids"][0]
        rel = (await client.get(f"/api/relationships/{rid}", headers=h)).json()
        assert rel["data"]["sourceRole"] == "partner"

    async def test_self_reference_rejected_per_item(self, client) -> None:
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        resp = await _batch(client, h, [
            {"source_element_id": a, "target_element_id": a,
             "relationship_type": "association"},
            {"source_element_id": a, "target_element_id": b,
             "relationship_type": "association"},
        ])
        body = resp.json()
        assert resp.status_code == 200
        assert body["succeeded"] == 1
        assert body["failed"] == 1
        assert len(body["ids"]) == 1
        assert "index 0" in body["errors"][0]
        assert "self-referencing" in body["errors"][0].lower()

    async def test_cross_set_rejected_per_item(self, client) -> None:
        h = await _auth(client)
        s1 = await _mk_set(client, h, "S1")
        s2 = await _mk_set(client, h, "S2")
        a = await _mk_el(client, h, s1, "A")
        b = await _mk_el(client, h, s2, "B")
        resp = await _batch(client, h, [
            {"source_element_id": a, "target_element_id": b,
             "relationship_type": "association"},
        ])
        body = resp.json()
        assert body["succeeded"] == 0
        assert body["failed"] == 1
        assert "cross-set" in body["errors"][0].lower()
        # Nothing was written.
        lst = await client.get(f"/api/relationships?element_id={a}", headers=h)
        assert lst.json()["total"] == 0

    async def test_missing_and_deleted_elements_rejected(self, client) -> None:
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        gone = await _mk_el(client, h, s, "Gone")
        d = await client.delete(
            f"/api/elements/{gone}", headers={**h, "If-Match": "1"},
        )
        assert d.status_code in (200, 204), d.text
        resp = await _batch(client, h, [
            {"source_element_id": a, "target_element_id": "no-such-element",
             "relationship_type": "association"},
            {"source_element_id": a, "target_element_id": gone,
             "relationship_type": "association"},
        ])
        body = resp.json()
        assert body["failed"] == 2
        assert all("not found" in e for e in body["errors"])

    async def test_required_fields_reported_per_item(self, client) -> None:
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        resp = await _batch(client, h, [
            {"source_element_id": a, "target_element_id": b},
            {"target_element_id": b, "relationship_type": "association"},
            {"source_element_id": a, "target_element_id": b,
             "relationship_type": "association"},
        ])
        body = resp.json()
        assert body["succeeded"] == 1
        assert body["failed"] == 2
        assert "relationship_type is required" in body["errors"][0]
        assert "source_element_id is required" in body["errors"][1]

    async def test_over_100_items_rejected(self, client) -> None:
        h = await _auth(client)
        item = {"source_element_id": "a", "target_element_id": "b",
                "relationship_type": "association"}
        resp = await _batch(client, h, [item] * 101)
        assert resp.status_code == 422

    async def test_empty_batch_rejected(self, client) -> None:
        h = await _auth(client)
        resp = await _batch(client, h, [])
        assert resp.status_code == 422

    async def test_requires_auth(self, client) -> None:
        resp = await client.post(
            "/api/batch/relationships/create",
            json={"relationships": [{"source_element_id": "a",
                                     "target_element_id": "b",
                                     "relationship_type": "x"}]},
        )
        assert resp.status_code == 401

    async def test_counts_like_ui_created(self, client) -> None:
        """A batch-created relationship shows up in the element's
        relationship list exactly like a UI-created one."""
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        cc = await _mk_el(client, h, s, "C")
        ui = await client.post("/api/relationships", json={
            "source_element_id": a, "target_element_id": b,
            "relationship_type": "association",
        }, headers=h)
        assert ui.status_code == 201
        await _batch(client, h, [{
            "source_element_id": cc, "target_element_id": a,
            "relationship_type": "association",
        }])
        lst = (await client.get(f"/api/relationships?element_id={a}", headers=h)).json()
        assert lst["total"] == 2
        keys = {frozenset(i.keys()) for i in lst["items"]}
        assert len(keys) == 1  # identical response shape


class TestBatchCreateWriteScope:
    """ADR-237/238: the batch path enforces collection write-scope per item."""

    async def test_scoped_user_outside_scope_fails_item(self, ctx) -> None:
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
        a1 = await _mk_el(client, admin, set_a, "A1")
        a2 = await _mk_el(client, admin, set_a, "A2")
        b1 = await _mk_el(client, admin, set_b, "B1")
        b2 = await _mk_el(client, admin, set_b, "B2")

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

        resp = await _batch(client, arch, [
            {"source_element_id": a1, "target_element_id": a2,
             "relationship_type": "association"},
            {"source_element_id": b1, "target_element_id": b2,
             "relationship_type": "association"},
        ])
        body = resp.json()
        assert body["succeeded"] == 1
        assert body["failed"] == 1
        assert "write-scope" in body["errors"][0]


# ── Update: relationship_type + roles ────────────────────────────────


class TestUpdateRelationshipTypeAndRoles:
    async def _one(self, client, h) -> tuple[str, str, str]:
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        resp = await _batch(client, h, [{
            "source_element_id": a, "target_element_id": b,
            "relationship_type": "association", "label": "L",
            "source_role": "partner", "data": {"gedcom_role": "HUSB"},
        }])
        return resp.json()["ids"][0], a, b

    async def test_relationship_type_updatable(self, client) -> None:
        h = await _auth(client)
        rid, _, _ = await self._one(client, h)
        resp = await client.put(
            f"/api/relationships/{rid}",
            json={"relationship_type": "composition", "label": "L",
                  "data": {"gedcom_role": "HUSB", "sourceRole": "partner"}},
            headers={**h, "If-Match": "1"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["relationship_type"] == "composition"
        assert resp.json()["current_version"] == 2
        versions = await client.get(f"/api/relationships/{rid}", headers=h)
        assert versions.json()["relationship_type"] == "composition"

    async def test_type_change_recorded_in_version_summary(self, ctx) -> None:
        client, dbm = ctx
        h = await _auth(client)
        rid, _, _ = await self._one(client, h)
        await client.put(
            f"/api/relationships/{rid}",
            json={"relationship_type": "composition", "data": {}},
            headers={**h, "If-Match": "1"},
        )
        cur = await dbm.main_db.execute(
            "SELECT change_summary FROM relationship_versions "
            "WHERE relationship_id = ? AND version = 2", (rid,),
        )
        row = await cur.fetchone()
        assert row[0] is not None
        assert "association" in row[0]
        assert "composition" in row[0]

    async def test_omitting_type_keeps_it(self, client) -> None:
        h = await _auth(client)
        rid, _, _ = await self._one(client, h)
        resp = await client.put(
            f"/api/relationships/{rid}",
            json={"label": "New", "data": {}},
            headers={**h, "If-Match": "1"},
        )
        assert resp.status_code == 200
        assert resp.json()["relationship_type"] == "association"

    async def test_empty_type_rejected(self, client) -> None:
        h = await _auth(client)
        rid, _, _ = await self._one(client, h)
        resp = await client.put(
            f"/api/relationships/{rid}",
            json={"relationship_type": "", "data": {}},
            headers={**h, "If-Match": "1"},
        )
        assert resp.status_code == 422

    async def test_role_fields_merge_into_data(self, client) -> None:
        h = await _auth(client)
        rid, _, _ = await self._one(client, h)
        resp = await client.put(
            f"/api/relationships/{rid}",
            json={"label": "L", "target_role": "wife",
                  "data": {"gedcom_role": "HUSB", "sourceRole": "partner"}},
            headers={**h, "If-Match": "1"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data"] == {
            "gedcom_role": "HUSB", "sourceRole": "partner", "targetRole": "wife",
        }
        assert body["source_role"] == "partner"
        assert body["target_role"] == "wife"

    async def test_empty_role_clears_it(self, client) -> None:
        h = await _auth(client)
        rid, _, _ = await self._one(client, h)
        resp = await client.put(
            f"/api/relationships/{rid}",
            json={"source_role": "", "data": {"sourceRole": "partner"}},
            headers={**h, "If-Match": "1"},
        )
        assert resp.status_code == 200
        assert "sourceRole" not in resp.json()["data"]
        assert resp.json()["source_role"] is None


# ── List filters ─────────────────────────────────────────────────────


class TestListFilters:
    async def _seed(self, client, h) -> dict[str, str]:
        s1 = await _mk_set(client, h, "S1")
        s2 = await _mk_set(client, h, "S2")
        a = await _mk_el(client, h, s1, "A")
        b = await _mk_el(client, h, s1, "B")
        cc = await _mk_el(client, h, s1, "C")
        x = await _mk_el(client, h, s2, "X")
        y = await _mk_el(client, h, s2, "Y")
        r = await _batch(client, h, [
            {"source_element_id": a, "target_element_id": b,
             "relationship_type": "association", "source_role": "partner",
             "target_role": "partner", "data": {"gedcom_role": "HUSB"}},
            {"source_element_id": cc, "target_element_id": a,
             "relationship_type": "dependency"},
            {"source_element_id": x, "target_element_id": y,
             "relationship_type": "association"},
        ])
        assert r.json()["succeeded"] == 3, r.text
        return {"s1": s1, "s2": s2, "a": a, "b": b, "c": cc, "x": x, "y": y}

    async def test_filter_by_set(self, client) -> None:
        h = await _auth(client)
        ids = await self._seed(client, h)
        resp = await client.get(f"/api/relationships?set_id={ids['s1']}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["total"] == 2
        resp = await client.get(f"/api/relationships?set_id={ids['s2']}", headers=h)
        assert resp.json()["total"] == 1

    async def test_filter_by_type(self, client) -> None:
        h = await _auth(client)
        ids = await self._seed(client, h)
        resp = await client.get(
            f"/api/relationships?set_id={ids['s1']}&relationship_type=dependency",
            headers=h,
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["source_element_id"] == ids["c"]

    async def test_element_filter_is_both_directions(self, client) -> None:
        h = await _auth(client)
        ids = await self._seed(client, h)
        resp = await client.get(f"/api/relationships?element_id={ids['a']}", headers=h)
        body = resp.json()
        assert body["total"] == 2
        sources = {i["source_element_id"] for i in body["items"]}
        assert sources == {ids["a"], ids["c"]}

    async def test_items_include_roles_and_data(self, client) -> None:
        h = await _auth(client)
        ids = await self._seed(client, h)
        resp = await client.get(
            f"/api/relationships?element_id={ids['b']}", headers=h,
        )
        item = resp.json()["items"][0]
        assert item["source_role"] == "partner"
        assert item["target_role"] == "partner"
        assert item["data"]["gedcom_role"] == "HUSB"
        assert item["source_element_name"] == "A"
        assert item["target_element_name"] == "B"

    async def test_pagination(self, client) -> None:
        h = await _auth(client)
        ids = await self._seed(client, h)
        p1 = (await client.get(
            f"/api/relationships?set_id={ids['s1']}&page=1&page_size=1", headers=h,
        )).json()
        p2 = (await client.get(
            f"/api/relationships?set_id={ids['s1']}&page=2&page_size=1", headers=h,
        )).json()
        assert p1["total"] == 2
        assert len(p1["items"]) == 1
        assert len(p2["items"]) == 1
        assert p1["items"][0]["id"] != p2["items"][0]["id"]


# ── Diagram edges reuse MCP-created ids ──────────────────────────────


class TestDiagramEdgeReuse:
    async def test_relationship_id_on_edge_creates_no_duplicate(self, client) -> None:
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        rid = (await _batch(client, h, [{
            "source_element_id": a, "target_element_id": b,
            "relationship_type": "association", "target_role": "child",
        }])).json()["ids"][0]

        d = await client.post("/api/diagrams", json={
            "diagram_type": "class", "name": "D", "set_id": s, "notation": "uml",
            "data": {"nodes": [], "edges": []},
        }, headers=h)
        assert d.status_code == 201, d.text
        did = d.json()["id"]
        data = {
            "nodes": [
                {"id": "n1", "type": "class", "position": {"x": 0, "y": 0},
                 "data": {"label": "A", "entityId": a}},
                {"id": "n2", "type": "class", "position": {"x": 200, "y": 0},
                 "data": {"label": "B", "entityId": b}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "type": "association",
                 "data": {"relationshipType": "association", "relationshipId": rid,
                          "targetRole": "child"}},
            ],
        }
        u = await client.put(
            f"/api/diagrams/{did}",
            json={"name": "D", "data": data},
            headers={**h, "If-Match": str(d.json()["current_version"])},
        )
        assert u.status_code == 200, u.text

        lst = (await client.get(f"/api/relationships?element_id={a}", headers=h)).json()
        assert lst["total"] == 1
        assert lst["items"][0]["id"] == rid

    async def _save_single_edge(
        self, client, h, s: str, a: str, b: str, edge_data: dict[str, object],
    ) -> None:
        """Save a diagram with nodes A (n1), B (n2) and one edge n2 -> n1
        (drawn opposite to an A -> B relationship)."""
        d = await client.post("/api/diagrams", json={
            "diagram_type": "class", "name": "D", "set_id": s, "notation": "uml",
            "data": {"nodes": [], "edges": []},
        }, headers=h)
        assert d.status_code == 201, d.text
        data = {
            "nodes": [
                {"id": "n1", "type": "class", "position": {"x": 0, "y": 0},
                 "data": {"label": "A", "entityId": a}},
                {"id": "n2", "type": "class", "position": {"x": 200, "y": 0},
                 "data": {"label": "B", "entityId": b}},
            ],
            "edges": [
                {"id": "e1", "source": "n2", "target": "n1", "type": "association",
                 "data": edge_data},
            ],
        }
        u = await client.put(
            f"/api/diagrams/{d.json()['id']}",
            json={"name": "D", "data": data},
            headers={**h, "If-Match": str(d.json()["current_version"])},
        )
        assert u.status_code == 200, u.text

    async def test_reversed_edge_with_relationship_id_creates_no_duplicate(
        self, client,
    ) -> None:
        """An edge drawn target -> source that names the relationship via
        data.relationshipId refers to that relationship; saving must not
        auto-create a second, reversed one."""
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        rid = (await _batch(client, h, [{
            "source_element_id": a, "target_element_id": b,
            "relationship_type": "association",
        }])).json()["ids"][0]

        await self._save_single_edge(client, h, s, a, b, {
            "relationshipType": "association", "relationshipId": rid,
        })

        lst = (await client.get(f"/api/relationships?element_id={a}", headers=h)).json()
        assert lst["total"] == 1
        assert lst["items"][0]["id"] == rid

    async def test_relationship_id_for_other_elements_does_not_suppress_create(
        self, client,
    ) -> None:
        """A relationshipId that names a relationship between different
        elements (stale or copied edge) does not stand in for this edge."""
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        b = await _mk_el(client, h, s, "B")
        c = await _mk_el(client, h, s, "C")
        other = (await _batch(client, h, [{
            "source_element_id": a, "target_element_id": c,
            "relationship_type": "association",
        }])).json()["ids"][0]

        await self._save_single_edge(client, h, s, a, b, {
            "relationshipType": "association", "relationshipId": other,
        })

        lst = (await client.get(f"/api/relationships?element_id={b}", headers=h)).json()
        assert lst["total"] == 1
        created = lst["items"][0]
        assert created["id"] != other
        assert created["source_element_id"] == b
        assert created["target_element_id"] == a


# ── Existing flows untouched ─────────────────────────────────────────


class TestExistingFlowsUnchanged:
    async def test_single_post_still_allows_reflexive(self, client) -> None:
        """The canvas's self-loop edge (UnifiedCanvas `self_loop`) and the
        Sparx importer's reflexive associations go through the single POST /
        service call; ADR-249's rejection applies only to the batch path."""
        h = await _auth(client)
        s = await _mk_set(client, h)
        a = await _mk_el(client, h, s, "A")
        resp = await client.post("/api/relationships", json={
            "source_element_id": a, "target_element_id": a,
            "relationship_type": "association",
        }, headers=h)
        assert resp.status_code == 201
        assert resp.json()["source_role"] is None


# ── MCP server instructions (re-seeded on every startup, ADR-177) ─────


def test_server_instructions_seed_points_at_relationship_tools() -> None:
    from app.seed.creation_prompts import MCP_SERVER_INSTRUCTIONS_BODY

    for name in (
        "list_relationships", "create_relationships",
        "update_relationship", "delete_relationship",
    ):
        assert f"`{name}`" in MCP_SERVER_INSTRUCTIONS_BODY
    assert "data.relationshipId" in MCP_SERVER_INSTRUCTIONS_BODY
    # Relationship reads require auth (unlike element reads) — the AUTH
    # RECOVERY text must say so.
    assert (
        "except `list_relationships` / `get_relationship`, which need it"
        in MCP_SERVER_INSTRUCTIONS_BODY
    )
