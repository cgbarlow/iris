"""ADR-237: per-user collection write-scope enforcement.

A user with rows in ``user_collection_scope`` may WRITE only inside those
collections; outside them they are read-only, and they may never create or
delete collections nor mutate global element templates. Admins and users with
no scope rows bypass. Reads are unaffected.

The existing router suites all authenticate as ``admin`` (who bypasses), so
these tests specifically drive a *scoped* ``architect`` user end-to-end.
"""

from __future__ import annotations

from tests.test_authz.scope_helpers import (
    add_scope,
    admin_headers,
    create_architect,
    login,
    mk_collection,
    mk_element,
    mk_set,
)


class TestCollectionWriteScope:
    async def test_scoped_user_writes_inside_scope(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")

        # set + package + element all succeed inside collection A
        s = await mk_set(client, arch, "set-in-a", coll_a)
        assert s.status_code == 201, s.text
        set_id = s.json()["id"]
        pkg = await client.post(
            "/api/packages", json={"name": "p", "set_id": set_id}, headers=arch
        )
        assert pkg.status_code == 201, pkg.text
        el = await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "e", "data": {}, "set_id": set_id},
            headers=arch,
        )
        assert el.status_code == 201, el.text

    async def test_scoped_user_403_outside_scope(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        coll_b = await mk_collection(client, admin, "B")
        # admin seeds a set inside B
        set_b = (await mk_set(client, admin, "set-in-b", coll_b)).json()["id"]
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")

        # creating a set in B is denied
        denied = await mk_set(client, arch, "nope", coll_b)
        assert denied.status_code == 403, denied.text
        # creating an element in B's set is denied
        el = await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "e", "data": {}, "set_id": set_b},
            headers=arch,
        )
        assert el.status_code == 403, el.text

    async def test_scoped_user_update_element_gated_by_collection(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        coll_b = await mk_collection(client, admin, "B")
        set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
        set_b = (await mk_set(client, admin, "sb", coll_b)).json()["id"]
        el_a = await mk_element(client, admin, set_a, "ea")
        el_b = await mk_element(client, admin, set_b, "eb")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")

        # update inside scope (A) → 200
        ok = await client.put(
            f"/api/elements/{el_a['id']}",
            json={"name": "ea2", "data": {}},
            headers={**arch, "If-Match": str(el_a["current_version"])},
        )
        assert ok.status_code == 200, ok.text
        # update outside scope (B) → 403
        no = await client.put(
            f"/api/elements/{el_b['id']}",
            json={"name": "eb2", "data": {}},
            headers={**arch, "If-Match": str(el_b["current_version"])},
        )
        assert no.status_code == 403, no.text

    async def test_unscoped_user_unaffected(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_b = await mk_collection(client, admin, "B")
        await create_architect(client, admin)  # NO scope rows
        arch = await login(client, "arch")
        # writes everywhere, as before ADR-237
        s = await mk_set(client, arch, "free", coll_b)
        assert s.status_code == 201, s.text

    async def test_admin_bypasses_even_with_scope_rows(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        coll_b = await mk_collection(client, admin, "B")
        # find admin id and scope them to A only
        cur = await dbm.main_db.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = (await cur.fetchone())[0]
        await add_scope(dbm, admin_id, coll_a)
        # admin still writes in B
        s = await mk_set(client, admin, "admin-set-b", coll_b)
        assert s.status_code == 201, s.text

    async def test_scoped_user_cannot_create_collection(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")
        r = await client.post("/api/collections", json={"name": "new"}, headers=arch)
        assert r.status_code == 403, r.text

    async def test_scoped_user_cannot_delete_collection_even_in_scope(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")
        r = await client.delete(f"/api/collections/{coll_a}", headers=arch)
        assert r.status_code == 403, r.text

    async def test_scoped_user_cannot_create_global_template(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
        el = await mk_element(client, admin, set_a, "e")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")
        r = await client.post(
            "/api/element-templates",
            json={
                "name": "g",
                "source_element_id": el["id"],
                "is_global": True,
            },
            headers=arch,
        )
        assert r.status_code == 403, r.text

    async def test_set_move_across_boundary_denied(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        coll_b = await mk_collection(client, admin, "B")
        set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")
        # moving an in-scope set OUT to B (not in scope) is denied
        r = await client.put(
            f"/api/sets/{set_a}",
            json={"name": "sa", "collection_id": coll_b},
            headers=arch,
        )
        assert r.status_code == 403, r.text

    async def test_comment_create_gated_by_collection(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        coll_b = await mk_collection(client, admin, "B")
        set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
        set_b = (await mk_set(client, admin, "sb", coll_b)).json()["id"]
        el_a = await mk_element(client, admin, set_a, "ea")
        el_b = await mk_element(client, admin, set_b, "eb")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")

        ok = await client.post(
            f"/api/elements/{el_a['id']}/comments",
            json={"content": "hi"}, headers=arch,
        )
        assert ok.status_code == 201, ok.text
        no = await client.post(
            f"/api/elements/{el_b['id']}/comments",
            json={"content": "hi"}, headers=arch,
        )
        assert no.status_code == 403, no.text

    async def test_reads_unaffected_for_scoped_user(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        coll_b = await mk_collection(client, admin, "B")
        set_b = (await mk_set(client, admin, "sb", coll_b)).json()["id"]
        el_b = await mk_element(client, admin, set_b, "eb")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")
        # reads outside scope still succeed
        assert (await client.get(f"/api/sets/{set_b}", headers=arch)).status_code == 200
        assert (await client.get(f"/api/elements/{el_b['id']}", headers=arch)).status_code == 200
        assert (await client.get("/api/collections", headers=arch)).status_code == 200


class TestAuthMeWriteScope:
    async def test_scoped_user_me_lists_scope(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")
        me = (await client.get("/api/auth/me", headers=arch)).json()
        assert me["write_scope"] == [coll_a]

    async def test_unscoped_user_me_null_scope(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        await create_architect(client, admin)
        arch = await login(client, "arch")
        me = (await client.get("/api/auth/me", headers=arch)).json()
        assert me["write_scope"] is None

    async def test_admin_me_null_scope(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        me = (await client.get("/api/auth/me", headers=admin)).json()
        assert me["write_scope"] is None


class TestScopeConsistencyADR238:
    """ADR-238: create-gate, persisted row, and update-gate must resolve the
    SAME collection — the original ADR-237 defect let a create pass while the
    subsequent save 403'd."""

    async def test_create_under_package_without_set_id_then_update(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
        pkg = (
            await client.post(
                "/api/packages", json={"name": "p", "set_id": set_a}, headers=admin
            )
        ).json()
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")

        # Diagram created with ONLY parent_package_id (the canvas/hierarchy shape)
        dg = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "simple-view", "name": "d", "data": {},
                "parent_package_id": pkg["id"],
            },
            headers=arch,
        )
        assert dg.status_code == 201, dg.text
        dg_id = dg.json()["id"]
        # It lands in the package's set (collection A), NOT the un-grouped Default.
        got = (await client.get(f"/api/diagrams/{dg_id}", headers=arch)).json()
        assert got["set_id"] == set_a
        assert got["collection_id"] == coll_a
        # And the subsequent save/update SUCCEEDS (the regression).
        upd = await client.put(
            f"/api/diagrams/{dg_id}",
            json={"name": "d2", "data": {}},
            headers={**arch, "If-Match": str(dg.json()["current_version"])},
        )
        assert upd.status_code == 200, upd.text

        # Same for an element created with only package_id.
        el = await client.post(
            "/api/elements",
            json={
                "element_type": "component", "name": "e", "data": {},
                "package_id": pkg["id"],
            },
            headers=arch,
        )
        assert el.status_code == 201, el.text
        el_got = (await client.get(f"/api/elements/{el.json()['id']}", headers=arch)).json()
        assert el_got["collection_id"] == coll_a

    async def test_element_create_without_context_denied_for_scoped(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")
        # No set_id and no package_id → resolves to the Default set (collection
        # NULL) → 403 for a scoped user.
        r = await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "e", "data": {}},
            headers=arch,
        )
        assert r.status_code == 403, r.text
        # An UNSCOPED architect can still do it (lands in Default) — unchanged.
        await create_architect(client, admin, username="free")
        free = await login(client, "free")
        r2 = await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "e", "data": {}},
            headers=free,
        )
        assert r2.status_code == 201, r2.text

    async def test_relationship_create_gated_by_collection(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        coll_b = await mk_collection(client, admin, "B")
        set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
        set_b = (await mk_set(client, admin, "sb", coll_b)).json()["id"]
        a1 = await mk_element(client, admin, set_a, "a1")
        a2 = await mk_element(client, admin, set_a, "a2")
        b1 = await mk_element(client, admin, set_b, "b1")
        b2 = await mk_element(client, admin, set_b, "b2")
        uid = await create_architect(client, admin)
        await add_scope(dbm, uid, coll_a)
        arch = await login(client, "arch")

        ok = await client.post(
            "/api/relationships",
            json={
                "source_element_id": a1["id"], "target_element_id": a2["id"],
                "relationship_type": "uses",
            },
            headers=arch,
        )
        assert ok.status_code == 201, ok.text
        no = await client.post(
            "/api/relationships",
            json={
                "source_element_id": b1["id"], "target_element_id": b2["id"],
                "relationship_type": "uses",
            },
            headers=arch,
        )
        assert no.status_code == 403, no.text

    async def test_package_response_carries_collection_id(self, ctx) -> None:
        client, dbm = ctx
        admin = await admin_headers(client)
        coll_a = await mk_collection(client, admin, "A")
        set_a = (await mk_set(client, admin, "sa", coll_a)).json()["id"]
        pkg = (
            await client.post(
                "/api/packages", json={"name": "p", "set_id": set_a}, headers=admin
            )
        ).json()
        got = (await client.get(f"/api/packages/{pkg['id']}", headers=admin)).json()
        assert got["collection_id"] == coll_a
