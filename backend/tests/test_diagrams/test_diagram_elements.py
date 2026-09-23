"""Tests for GET /api/diagrams/{id}/elements (ADR-248, SPEC-248-A).

The diagram view used to hydrate its canvas with one
``GET /api/elements/{id}`` per node — four times per node on first
visit. This endpoint returns every element drawn on the diagram's
current canvas in one response, with the same payload per element as
``GET /api/elements/{id}``, computed in a bounded number of queries.

TDD: written before the endpoint existed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.db.adapter import SqliteAdapter
from app.main import create_app
from app.startup import initialize_databases

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
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_element(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str,
    **extra: Any,
) -> str:
    resp = await client.post(
        "/api/elements",
        json={"element_type": "component", "name": name, **extra},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _node(node_id: str, entity_id: str | None, label: str = "n") -> dict[str, Any]:
    data: dict[str, Any] = {"label": label, "entityType": "component"}
    if entity_id is not None:
        data["entityId"] = entity_id
    return {
        "id": node_id,
        "type": "component",
        "position": {"x": 0, "y": 0},
        "data": data,
    }


async def _create_diagram(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    nodes: list[dict[str, Any]],
    name: str = "Diagram",
) -> str:
    resp = await client.post(
        "/api/diagrams",
        json={
            "diagram_type": "component",
            "name": name,
            "data": {"nodes": nodes, "edges": []},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestDiagramElementsPayload:
    async def test_payload_matches_single_element_endpoint(
        self, client: httpx.AsyncClient
    ) -> None:
        """Every item equals GET /api/elements/{id} for that element —
        tags, relationship_count, diagram_usage_count, package_name,
        parent_element_name, stereotype, notation, collection_id."""
        headers = await _auth_headers(client)

        pkg = await client.post(
            "/api/packages", json={"name": "Pkg"}, headers=headers,
        )
        assert pkg.status_code == 201, pkg.text
        package_id = pkg.json()["id"]

        a = await _create_element(client, headers, "Alpha", package_id=package_id)
        b = await _create_element(
            client, headers, "Beta",
            parent_element_id=a,
            metadata={"stereotype": "ArchiMate_Capability"},
            notation="archimate",
            description="Beta description",
            data={"attributes": [{"name": "x"}]},
        )
        c = await _create_element(client, headers, "Gamma")

        for tag in ("zeta", "alpha"):
            r = await client.post(f"/api/elements/{a}/tags", json={"tag": tag}, headers=headers)
            assert r.status_code == 201, r.text

        for src, tgt in ((a, b), (b, c), (c, c)):
            r = await client.post(
                "/api/relationships",
                json={
                    "source_element_id": src,
                    "target_element_id": tgt,
                    "relationship_type": "uses",
                },
                headers=headers,
            )
            assert r.status_code == 201, r.text

        diagram_id = await _create_diagram(
            client, headers, [_node("n1", a), _node("n2", b), _node("n3", c)],
        )
        # A second diagram referencing A bumps A's diagram_usage_count to 2.
        await _create_diagram(client, headers, [_node("m1", a)], name="Other")

        resp = await client.get(f"/api/diagrams/{diagram_id}/elements", headers=headers)
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert [i["id"] for i in items] == [a, b, c]

        for item in items:
            single = await client.get(f"/api/elements/{item['id']}", headers=headers)
            assert single.status_code == 200
            assert item == single.json()

        by_id = {i["id"]: i for i in items}
        # Sanity: the enrichment fields are genuinely populated, so the
        # equality above is not vacuous.
        assert by_id[a]["tags"] == ["alpha", "zeta"]
        assert by_id[a]["diagram_usage_count"] == 2
        assert by_id[a]["package_name"] == "Pkg"
        assert by_id[a]["relationship_count"] == 1
        assert by_id[b]["relationship_count"] == 2
        assert by_id[c]["relationship_count"] == 2  # b->c plus self-loop once
        assert by_id[b]["parent_element_name"] == "Alpha"
        assert by_id[b]["stereotype"] == "ArchiMate_Capability"
        assert by_id[b]["notation"] == "archimate"
        assert by_id[c]["diagram_usage_count"] == 1

    async def test_dedups_preserving_first_occurrence_order(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        a = await _create_element(client, headers, "A")
        b = await _create_element(client, headers, "B")
        c = await _create_element(client, headers, "C")
        diagram_id = await _create_diagram(
            client, headers,
            [_node("1", b), _node("2", a), _node("3", b), _node("4", c), _node("5", a)],
        )
        resp = await client.get(f"/api/diagrams/{diagram_id}/elements", headers=headers)
        assert resp.status_code == 200
        assert [i["id"] for i in resp.json()] == [b, a, c]

    async def test_deleted_and_missing_elements_are_excluded(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        a = await _create_element(client, headers, "Keep")
        b = await _create_element(client, headers, "Delete me")
        diagram_id = await _create_diagram(
            client, headers,
            [_node("1", a), _node("2", b), _node("3", "no-such-element")],
        )
        d = await client.delete(f"/api/elements/{b}", headers={**headers, "If-Match": "1"})
        assert d.status_code == 204, d.text

        resp = await client.get(f"/api/diagrams/{diagram_id}/elements", headers=headers)
        assert resp.status_code == 200
        assert [i["id"] for i in resp.json()] == [a]

    async def test_nodes_without_entity_id_are_skipped(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        a = await _create_element(client, headers, "Only")
        nodes = [
            _node("free-text", None),
            _node("1", a),
            {"id": "no-data", "type": "note", "position": {"x": 0, "y": 0}},
            _node("blank", ""),
        ]
        diagram_id = await _create_diagram(client, headers, nodes)
        resp = await client.get(f"/api/diagrams/{diagram_id}/elements", headers=headers)
        assert resp.status_code == 200
        assert [i["id"] for i in resp.json()] == [a]

    async def test_empty_canvas_returns_empty_list(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        diagram_id = await _create_diagram(client, headers, [])
        resp = await client.get(f"/api/diagrams/{diagram_id}/elements", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestDiagramElementsAccess:
    async def test_missing_diagram_is_404(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/diagrams/does-not-exist/elements")
        assert resp.status_code == 404

    async def test_deleted_diagram_is_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        a = await _create_element(client, headers, "A")
        diagram_id = await _create_diagram(client, headers, [_node("1", a)])
        d = await client.delete(
            f"/api/diagrams/{diagram_id}", headers={**headers, "If-Match": "1"},
        )
        assert d.status_code == 204, d.text
        resp = await client.get(f"/api/diagrams/{diagram_id}/elements", headers=headers)
        assert resp.status_code == 404

    async def test_anonymous_can_read(self, client: httpx.AsyncClient) -> None:
        """Anonymous-readable, like GET /api/elements/{id}."""
        headers = await _auth_headers(client)
        a = await _create_element(client, headers, "Public")
        diagram_id = await _create_diagram(client, headers, [_node("1", a)])

        resp = await client.get(f"/api/diagrams/{diagram_id}/elements")
        assert resp.status_code == 200
        single = await client.get(f"/api/elements/{a}")
        assert resp.json() == [single.json()]


async def _batch_create(
    client: httpx.AsyncClient, headers: dict[str, str], count: int,
) -> list[str]:
    resp = await client.post(
        "/api/batch/elements/create",
        json={
            "elements": [
                {"element_type": "component", "name": f"E{i}"} for i in range(count)
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    ids = resp.json()["ids"]
    assert len(ids) == count
    return ids


class TestDiagramElementsQueryBound:
    """The endpoint's query count must not grow with the node count."""

    @staticmethod
    def _count_queries(monkeypatch: pytest.MonkeyPatch) -> list[str]:
        seen: list[str] = []
        original = SqliteAdapter.execute

        async def counting(self: SqliteAdapter, query: str, params: Any = ()) -> Any:
            seen.append(query)
            return await original(self, query, params)

        monkeypatch.setattr(SqliteAdapter, "execute", counting)
        return seen

    async def _queries_for(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
        count: int,
    ) -> tuple[int, list[dict[str, Any]], list[str]]:
        ids = await _batch_create(client, headers, count)
        for eid in ids[:5]:
            await client.post(f"/api/elements/{eid}/tags", json={"tag": "t"}, headers=headers)
        diagram_id = await _create_diagram(
            client, headers, [_node(f"n{i}", eid) for i, eid in enumerate(ids)],
        )
        seen = self._count_queries(monkeypatch)
        resp = await client.get(f"/api/diagrams/{diagram_id}/elements")
        monkeypatch.undo()
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert [i["id"] for i in items] == ids
        return len(seen), items, ids

    async def test_query_count_is_independent_of_node_count(
        self, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        headers = await _auth_headers(client)
        small, _, _ = await self._queries_for(client, headers, monkeypatch, 3)
        large, items, _ = await self._queries_for(client, headers, monkeypatch, 80)
        assert large == small, (large, small)
        # 1 canvas read + element rows + tags + relationship counts +
        # diagram usage counts (5 today), plus one query of headroom.
        assert large <= 6
        assert sum(1 for i in items if i["tags"] == ["t"]) == 5
        assert all(i["diagram_usage_count"] == 1 for i in items)

    async def test_large_id_lists_are_chunked(
        self, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """IN-lists are split so no single query exceeds the chunk size —
        keeps us under SQLite's bound-variable limit on huge diagrams."""
        import app.elements.service as element_service

        headers = await _auth_headers(client)
        baseline, _, _ = await self._queries_for(client, headers, monkeypatch, 3)

        monkeypatch.setattr(element_service, "_ID_CHUNK_SIZE", 7)
        ids = await _batch_create(client, headers, 30)
        diagram_id = await _create_diagram(
            client, headers, [_node(f"n{i}", eid) for i, eid in enumerate(ids)],
        )
        seen = self._count_queries(monkeypatch)
        resp = await client.get(f"/api/diagrams/{diagram_id}/elements")
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert [i["id"] for i in items] == ids
        assert all(i["diagram_usage_count"] == 1 for i in items)
        # 30 ids / 7 per chunk = 5 chunks; each chunk adds its batched
        # queries, so the total grows with chunks, never with nodes.
        per_chunk = baseline - 1  # baseline = 1 canvas read + one chunk
        assert len(seen) == 1 + 5 * per_chunk
