"""ADR-250: batch endpoints enforce collection write-scope per item.

Before ADR-250 every ``/api/batch/*`` endpoint except relationship create
(ADR-249) skipped ``assert_write_allowed``, so a user scoped to collection A
could delete, clone, retag, move, create or update elements and diagrams in
collection B — writes the single-item endpoints refuse with 403. Batch
endpoints keep per-item failure isolation, so an out-of-scope item is
reported as a per-item error and left untouched while in-scope items in the
same call still succeed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.test_authz.scope_helpers import (
    add_scope,
    admin_headers,
    create_architect,
    login,
    mk_collection,
    mk_element,
    mk_set,
)

if TYPE_CHECKING:
    import httpx

    from app.database import DatabaseManager

SCOPE_ERROR = "Outside your collection write-scope"


async def _mk_diagram(
    client: httpx.AsyncClient, headers: dict[str, str], set_id: str, name: str,
) -> dict:
    r = await client.post(
        "/api/diagrams",
        json={"diagram_type": "component", "name": name, "data": {}, "set_id": set_id},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _world(ctx: tuple[httpx.AsyncClient, DatabaseManager]) -> dict:
    """Collections A and B with a set, element and diagram each (seeded by
    admin), plus a second set in A, and an architect scoped to A only."""
    client, dbm = ctx
    admin = await admin_headers(client)
    coll_a = await mk_collection(client, admin, "A")
    coll_b = await mk_collection(client, admin, "B")
    set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
    set_a2 = (await mk_set(client, admin, "sa2", coll_a)).json()["id"]
    set_b = (await mk_set(client, admin, "sb", coll_b)).json()["id"]
    uid = await create_architect(client, admin)
    await add_scope(dbm, uid, coll_a)
    return {
        "client": client,
        "admin": admin,
        "arch": await login(client, "arch"),
        "set_a": set_a,
        "set_a2": set_a2,
        "set_b": set_b,
        "el_a": await mk_element(client, admin, set_a, "ea"),
        "el_b": await mk_element(client, admin, set_b, "eb"),
        "dg_a": await _mk_diagram(client, admin, set_a, "da"),
        "dg_b": await _mk_diagram(client, admin, set_b, "db"),
    }


def _assert_only_b_rejected(result: dict, b_id: str | None = None) -> None:
    assert result["succeeded"] == 1, result
    assert result["failed"] == 1, result
    assert len(result["errors"]) == 1, result
    assert SCOPE_ERROR in result["errors"][0], result
    if b_id is not None:
        assert b_id in result["errors"][0], result


class TestBatchElementWriteScope:
    async def test_delete(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/elements/delete",
            json={"ids": [w["el_a"]["id"], w["el_b"]["id"]]}, headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        _assert_only_b_rejected(r.json(), w["el_b"]["id"])
        assert (await c.get(f"/api/elements/{w['el_b']['id']}")).status_code == 200
        assert (await c.get(f"/api/elements/{w['el_a']['id']}")).status_code == 404

    async def test_clone(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/elements/clone",
            json={"ids": [w["el_a"]["id"], w["el_b"]["id"]]}, headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        _assert_only_b_rejected(r.json(), w["el_b"]["id"])
        in_b = (await c.get(f"/api/elements?set_id={w['set_b']}")).json()
        assert in_b["total"] == 1  # no clone landed in B

    async def test_tags(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/elements/tags",
            json={"ids": [w["el_a"]["id"], w["el_b"]["id"]], "add_tags": ["x"]},
            headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        _assert_only_b_rejected(r.json(), w["el_b"]["id"])
        assert (await c.get(f"/api/elements/{w['el_b']['id']}")).json()["tags"] == []
        assert (await c.get(f"/api/elements/{w['el_a']['id']}")).json()["tags"] == ["x"]

    async def test_set_move_out_of_scope_denied(self, ctx) -> None:
        """Moving an in-scope element into B's set writes into B."""
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/elements/set",
            json={"ids": [w["el_a"]["id"]], "set_id": w["set_b"]}, headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["succeeded"] == 0, body
        assert body["failed"] == 1, body
        assert SCOPE_ERROR in body["errors"][0], body
        assert (await c.get(f"/api/elements/{w['el_a']['id']}")).json()["set_id"] == w["set_a"]

    async def test_set_move_into_scope_denied(self, ctx) -> None:
        """Pulling an element out of B also writes B (it removes it)."""
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/elements/set",
            json={"ids": [w["el_a"]["id"], w["el_b"]["id"]], "set_id": w["set_a2"]},
            headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        _assert_only_b_rejected(r.json(), w["el_b"]["id"])
        assert (await c.get(f"/api/elements/{w['el_b']['id']}")).json()["set_id"] == w["set_b"]
        assert (await c.get(f"/api/elements/{w['el_a']['id']}")).json()["set_id"] == w["set_a2"]

    async def test_create(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/elements/create",
            json={"elements": [
                {"element_type": "component", "name": "new-a", "set_id": w["set_a"]},
                {"element_type": "component", "name": "new-b", "set_id": w["set_b"]},
            ]},
            headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        body = r.json()
        _assert_only_b_rejected(body)
        assert len(body["ids"]) == 1
        in_b = (await c.get(f"/api/elements?set_id={w['set_b']}")).json()
        assert [e["name"] for e in in_b["items"]] == ["eb"]

    async def test_update(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/elements/update",
            json={"updates": [
                {"element_id": w["el_a"]["id"], "expected_version": 1, "name": "ea2"},
                {"element_id": w["el_b"]["id"], "expected_version": 1, "name": "eb2"},
            ]},
            headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        body = r.json()
        _assert_only_b_rejected(body)
        assert body["errors"][0].startswith("Update at index 1:"), body
        assert (await c.get(f"/api/elements/{w['el_b']['id']}")).json()["name"] == "eb"
        assert (await c.get(f"/api/elements/{w['el_a']['id']}")).json()["name"] == "ea2"


class TestBatchDiagramWriteScope:
    async def test_delete(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/diagrams/delete",
            json={"ids": [w["dg_a"]["id"], w["dg_b"]["id"]]}, headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        _assert_only_b_rejected(r.json(), w["dg_b"]["id"])
        assert (await c.get(f"/api/diagrams/{w['dg_b']['id']}")).status_code == 200

    async def test_clone(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/diagrams/clone",
            json={"ids": [w["dg_a"]["id"], w["dg_b"]["id"]]}, headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        _assert_only_b_rejected(r.json(), w["dg_b"]["id"])
        in_b = (await c.get(f"/api/diagrams?set_id={w['set_b']}")).json()
        assert in_b["total"] == 1

    async def test_tags(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/diagrams/tags",
            json={"ids": [w["dg_a"]["id"], w["dg_b"]["id"]], "add_tags": ["x"]},
            headers=w["arch"],
        )
        assert r.status_code == 200, r.text
        _assert_only_b_rejected(r.json(), w["dg_b"]["id"])
        assert (await c.get(f"/api/diagrams/{w['dg_b']['id']}")).json()["tags"] == []

    async def test_set_move_across_boundary_denied(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        out = await c.post(
            "/api/batch/diagrams/set",
            json={"ids": [w["dg_a"]["id"]], "set_id": w["set_b"]}, headers=w["arch"],
        )
        assert out.status_code == 200, out.text
        assert out.json()["failed"] == 1, out.json()
        assert SCOPE_ERROR in out.json()["errors"][0], out.json()
        pull = await c.post(
            "/api/batch/diagrams/set",
            json={"ids": [w["dg_a"]["id"], w["dg_b"]["id"]], "set_id": w["set_a2"]},
            headers=w["arch"],
        )
        assert pull.status_code == 200, pull.text
        _assert_only_b_rejected(pull.json(), w["dg_b"]["id"])
        assert (await c.get(f"/api/diagrams/{w['dg_b']['id']}")).json()["set_id"] == w["set_b"]


class TestBatchScopeBypass:
    async def test_unscoped_user_writes_across_collections(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        await create_architect(c, w["admin"], username="free")
        free = await login(c, "free")
        r = await c.post(
            "/api/batch/elements/tags",
            json={"ids": [w["el_a"]["id"], w["el_b"]["id"]], "add_tags": ["y"]},
            headers=free,
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"succeeded": 2, "failed": 0, "errors": []}

    async def test_admin_writes_across_collections(self, ctx) -> None:
        w = await _world(ctx)
        c = w["client"]
        r = await c.post(
            "/api/batch/diagrams/set",
            json={"ids": [w["dg_a"]["id"], w["dg_b"]["id"]], "set_id": w["set_a2"]},
            headers=w["admin"],
        )
        assert r.status_code == 200, r.text
        assert r.json()["succeeded"] == 2, r.json()
