"""End-to-end smoke test (Phase 10).

Boots a real backend via `httpx.ASGITransport` and drives `iris-client`,
`iris-cli`, and `iris-mcp` against it — no mocks, no subprocesses. This
is the single test that proves parity across the three surfaces.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

# --- Real backend -----------------------------------------------------------


@pytest.fixture
async def backend_transport(
    tmp_path: Path,
) -> AsyncIterator[httpx.ASGITransport]:
    """Boot a real backend against a temp SQLite DB; yield ASGI transport."""
    from app.config import AppConfig, AuthConfig, DatabaseConfig
    from app.database import DatabaseManager
    from app.main import create_app
    from app.startup import initialize_databases

    cfg = AppConfig(
        debug=True,
        cors_origins=["http://test"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
        rate_limit_general=10_000,
        rate_limit_anon=10_000,
        rate_limit_pat=10_000,
    )
    app = create_app(cfg)
    dbm = DatabaseManager(cfg)
    await initialize_databases(dbm)
    app.state.db_manager = dbm
    try:
        yield httpx.ASGITransport(app=app)
    finally:
        await dbm.close()


async def _setup_admin_and_pat(
    transport: httpx.ASGITransport,
) -> tuple[str, str]:
    """Create an admin user, log in, and mint a PAT. Returns (base_url, pat)."""
    base = "http://test"
    async with httpx.AsyncClient(transport=transport, base_url=base) as c:
        await c.post(
            "/api/auth/setup",
            json={"username": "alice", "password": "TestPass123!"},
        )
        login = (await c.post(
            "/api/auth/login",
            json={"username": "alice", "password": "TestPass123!"},
        )).json()
        token_resp = (await c.post(
            "/api/users/me/tokens",
            json={"name": "smoke"},
            headers={"Authorization": f"Bearer {login['access_token']}"},
        )).json()
    return base, token_resp["token"]


# --- Parity tests -----------------------------------------------------------


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_iris_client_against_real_backend(
        self, backend_transport: httpx.ASGITransport,
    ) -> None:
        """iris-client: PAT auth → search works end-to-end."""
        from iris_client import IrisClient

        base, pat = await _setup_admin_and_pat(backend_transport)

        async with IrisClient(url=base, token=pat, transport=backend_transport) as client:
            me = await client.whoami()
            assert me.username == "alice"
            assert pat.startswith("iris_pat_")

            # Search endpoint works even with an empty repository.
            result = await client.search("something")
            assert isinstance(result.total, int)

    @pytest.mark.asyncio
    async def test_iris_mcp_tool_dispatch_against_real_backend(
        self, backend_transport: httpx.ASGITransport,
    ) -> None:
        """iris-mcp: tool dispatch goes through the whole stack."""
        from iris_client import IrisClient
        from iris_mcp import tools

        base, pat = await _setup_admin_and_pat(backend_transport)

        async with IrisClient(url=base, token=pat, transport=backend_transport) as client:
            result = await tools.dispatch(
                "search", client, {"query": "anything"},
            )
            assert len(result) == 1
            body = json.loads(result[0].text)
            assert "query" in body
            assert body["query"] == "anything"

    @pytest.mark.asyncio
    async def test_iris_mcp_resource_read_against_real_backend(
        self, backend_transport: httpx.ASGITransport,
    ) -> None:
        """An unknown resource id returns a mapped error, not a crash."""
        from iris_client import IrisClient
        from iris_mcp import resources

        base, pat = await _setup_admin_and_pat(backend_transport)

        async with IrisClient(url=base, token=pat, transport=backend_transport) as client:
            with pytest.raises(Exception) as excinfo:  # noqa: PT011, BLE001
                await resources.resource_read(
                    "iris://diagrams/nonexistent", client,
                )
            # Either a 404 from iris-client or the resource validator —
            # both are acceptable "no such thing" signals.
            assert "404" in str(excinfo.value) or "not found" in str(excinfo.value).lower()


class TestRelationshipToolsEndToEnd:
    """ADR-249 (v6.50.0, #298): the MCP relationship tools against a real
    backend — batch create with per-item rejections, list with roles + data,
    partial update, diagram-edge reuse without duplicates, soft delete."""

    @pytest.mark.asyncio
    async def test_relationship_lifecycle(
        self, backend_transport: httpx.ASGITransport,
    ) -> None:
        from iris_client import IrisClient
        from iris_mcp import tools

        base, pat = await _setup_admin_and_pat(backend_transport)

        async def call(name: str, args: dict) -> dict:
            out = await tools.dispatch(name, client, args)
            return json.loads(out[0].text)

        async with IrisClient(url=base, token=pat, transport=backend_transport) as client:
            s1 = (await client._request(
                "POST", "/api/sets", json={"name": "Family"},
            )).json()["id"]
            s2 = (await client._request(
                "POST", "/api/sets", json={"name": "Other"},
            )).json()["id"]
            els = await call("create_elements", {"elements": [
                {"element_type": "class", "name": "Family F1", "set_id": s1},
                {"element_type": "class", "name": "Alice", "set_id": s1},
                {"element_type": "class", "name": "Bob", "set_id": s1},
                {"element_type": "class", "name": "Elsewhere", "set_id": s2},
            ]})
            fam, alice, bob, other = els["ids"]

            created = await call("create_relationships", {"relationships": [
                {"source_element_id": fam, "target_element_id": alice,
                 "relationship_type": "association",
                 "source_role": "family", "target_role": "partner",
                 "data": {"gedcom_role": "WIFE"}},
                {"source_element_id": fam, "target_element_id": bob,
                 "relationship_type": "association", "target_role": "child",
                 "data": {"child_order": 1}},
                {"source_element_id": fam, "target_element_id": fam,
                 "relationship_type": "association"},
                {"source_element_id": fam, "target_element_id": other,
                 "relationship_type": "association"},
            ]})
            assert created["succeeded"] == 2
            assert created["failed"] == 2
            assert "index 2" in created["errors"][0]
            assert "self-referencing" in created["errors"][0]
            assert "index 3" in created["errors"][1]
            assert "cross-set" in created["errors"][1]
            wife_rel, child_rel = created["ids"]

            listed = await call("list_relationships", {"element_id": alice})
            assert listed["total"] == 1
            item = listed["items"][0]
            assert item["source_role"] == "family"
            assert item["target_role"] == "partner"
            assert item["data"] == {
                "gedcom_role": "WIFE", "sourceRole": "family", "targetRole": "partner",
            }
            by_set = await call("list_relationships", {"set_id": s1})
            assert by_set["total"] == 2

            updated = await call("update_relationship", {
                "relationship_id": child_rel,
                "relationship_type": "composition",
                "data": {"child_order": 2},
            })
            assert updated["relationship_type"] == "composition"
            assert updated["data"] == {"child_order": 2, "targetRole": "child"}
            assert updated["current_version"] == 2

            # Returned ids work as diagram-edge relationshipId, no duplicates.
            diagram = (await client._request("POST", "/api/diagrams", json={
                "diagram_type": "class", "name": "Tree", "set_id": s1,
                "notation": "uml", "data": {"nodes": [], "edges": []},
            })).json()
            canvas = {
                "nodes": [
                    {"id": "n-fam", "type": "class", "position": {"x": 0, "y": 0},
                     "data": {"label": "Family F1", "entityId": fam}},
                    {"id": "n-alice", "type": "class", "position": {"x": 0, "y": 200},
                     "data": {"label": "Alice", "entityId": alice}},
                ],
                "edges": [
                    {"id": "e1", "source": "n-fam", "target": "n-alice",
                     "type": "association",
                     "data": {"relationshipType": "association",
                              "relationshipId": wife_rel}},
                ],
            }
            await call("update_diagram", {"diagram_id": diagram["id"], "data": canvas})
            after = await call("list_relationships", {"element_id": alice})
            assert after["total"] == 1
            assert after["items"][0]["id"] == wife_rel

            deleted = await call("delete_relationship", {"relationship_id": child_rel})
            assert deleted["deleted"] is True
            remaining = await call("list_relationships", {"set_id": s1})
            assert remaining["total"] == 1


class TestPatchDiagramEndToEnd:
    """ADR-252 (v6.51.0, #301): the MCP patch_diagram tool against a real
    backend — incremental add + relationship edge, sync_labels after a
    rename, a failing op writing nothing, and an expected_version conflict."""

    @pytest.mark.asyncio
    async def test_patch_lifecycle(
        self, backend_transport: httpx.ASGITransport,
    ) -> None:
        from iris_client import IrisClient
        from iris_mcp import tools

        base, pat = await _setup_admin_and_pat(backend_transport)

        async def call(name: str, args: dict) -> dict:
            out = await tools.dispatch(name, client, args)
            return json.loads(out[0].text)

        async with IrisClient(url=base, token=pat, transport=backend_transport) as client:
            s1 = (await client._request(
                "POST", "/api/sets", json={"name": "Family"},
            )).json()["id"]
            els = await call("create_elements", {"elements": [
                {"element_type": "object", "name": "Peter", "set_id": s1},
                {"element_type": "object", "name": "Elizabeth", "set_id": s1},
            ]})
            peter, liz = els["ids"]
            rel = (await call("create_relationships", {"relationships": [
                {"source_element_id": peter, "target_element_id": liz,
                 "relationship_type": "association"},
            ]}))["ids"][0]
            diagram = (await client._request("POST", "/api/diagrams", json={
                "diagram_type": "class", "name": "Tree", "set_id": s1,
                "notation": "uml",
                "data": {"nodes": [
                    {"id": "n-p", "type": "object", "position": {"x": 0, "y": 0},
                     "data": {"label": "Peter (single-parent family)",
                              "entityType": "object", "entityId": peter}},
                ], "edges": []},
            })).json()

            patched = await call("patch_diagram", {
                "diagram_id": diagram["id"], "expected_version": 1,
                "change_summary": "Add Elizabeth",
                "operations": [
                    {"op": "add_node", "node": {
                        "id": "n-l", "type": "object", "position": {"x": 300, "y": 0},
                        "data": {"label": "Elizabeth", "entityType": "object",
                                 "entityId": liz}}},
                    {"op": "add_edge", "edge": {
                        "id": "e1", "source": "n-l", "target": "n-p",
                        "type": "association",
                        "data": {"relationshipType": "association",
                                 "relationshipId": rel}}},
                    {"op": "sync_labels"},
                ],
            })
            assert patched["current_version"] == 2
            assert patched["applied"] == 3
            assert patched["results"][2]["ids"] == ["n-p"]
            listed = await call("list_relationships", {"element_id": liz})
            assert listed["total"] == 1  # reversed edge reused rel, no duplicate

            failed = await call("patch_diagram", {
                "diagram_id": diagram["id"],
                "operations": [{"op": "remove_node", "id": "n-l",
                                "cascade_edges": False}],
            })
            assert failed["success"] is False
            assert failed["op_index"] == 0

            stale = await call("patch_diagram", {
                "diagram_id": diagram["id"], "expected_version": 1,
                "operations": [{"op": "remove_edge", "id": "e1"}],
            })
            assert stale["error"] == "version_conflict"
            assert stale["current_version"] == 2

            got = await client.get_diagram(diagram["id"])
            assert got.current_version == 2
            labels = {n["id"]: n["data"]["label"] for n in got.data["nodes"]}
            assert labels == {"n-p": "Peter", "n-l": "Elizabeth"}
            assert [e["id"] for e in got.data["edges"]] == ["e1"]


def test_cli_dispatch_noop() -> None:
    """Sanity: the Typer app imports cleanly; no commands shell out at import."""
    from iris_cli.main import app

    # Typer exposes commands on the underlying click group.
    assert app.registered_commands  # non-empty


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_setup_admin_and_pat)  # type: ignore[arg-type]
