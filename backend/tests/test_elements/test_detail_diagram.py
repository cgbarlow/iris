"""Integration tests for element → detail diagram drill link (ADR-221).

Covers:
- creating/updating an element with ``detail_diagram_id`` (tri-state);
- validation that the target diagram exists (422 otherwise);
- cross-set drill links are allowed;
- ``get_diagram`` exposes ``referenced_by_elements``;
- the smart-markdown ``{{element:<id>:detail_diagram}}`` token renders a
  link to the target diagram (and strikes through when unset).

Real FastAPI app + temp SQLite database (no mocks — protocol 9).
TDD: written alongside the implementation.
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
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
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


async def _create_set(
    client: httpx.AsyncClient, headers: dict, name: str = "S",
) -> str:
    resp = await client.post("/api/sets", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_diagram(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    set_id: str,
    name: str = "D",
    diagram_type: str = "component",
    data: dict | None = None,
) -> str:
    resp = await client.post(
        "/api/diagrams",
        json={
            "diagram_type": diagram_type,
            "name": name,
            "set_id": set_id,
            "data": data or {"nodes": [], "edges": []},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_element(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    name: str = "E",
    set_id: str | None = None,
    detail_diagram_id: str | None = None,
    element_type: str = "component",
) -> dict[str, object]:
    body: dict[str, object] = {
        "element_type": element_type,
        "name": name,
        "data": {},
    }
    if set_id is not None:
        body["set_id"] = set_id
    if detail_diagram_id is not None:
        body["detail_diagram_id"] = detail_diagram_id
    resp = await client.post("/api/elements", json=body, headers=headers)
    return {"status": resp.status_code, "body": resp.json()}


class TestCreateAndRead:
    async def test_create_with_detail_diagram_persists(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        diag = await _create_diagram(client, headers, set_id=set_id)

        created = await _create_element(
            client, headers, set_id=set_id, detail_diagram_id=diag,
        )
        assert created["status"] == 201, created
        assert created["body"]["detail_diagram_id"] == diag

        # And it round-trips on GET.
        resp = await client.get(f"/api/elements/{created['body']['id']}")
        assert resp.status_code == 200
        assert resp.json()["detail_diagram_id"] == diag

    async def test_create_with_missing_diagram_returns_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        created = await _create_element(
            client, headers, set_id=set_id,
            detail_diagram_id="00000000-0000-0000-0000-000000000000",
        )
        assert created["status"] == 422, created

    async def test_cross_set_detail_diagram_allowed(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_a = await _create_set(client, headers, name="A")
        set_b = await _create_set(client, headers, name="B")
        diag_in_b = await _create_diagram(client, headers, set_id=set_b)

        created = await _create_element(
            client, headers, set_id=set_a, detail_diagram_id=diag_in_b,
        )
        assert created["status"] == 201, created
        assert created["body"]["detail_diagram_id"] == diag_in_b


class TestUpdate:
    async def test_update_sets_detail_diagram(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        diag = await _create_diagram(client, headers, set_id=set_id)
        created = await _create_element(client, headers, set_id=set_id)
        eid = created["body"]["id"]
        ver = created["body"]["current_version"]

        resp = await client.put(
            f"/api/elements/{eid}",
            json={"name": "E", "data": {}, "detail_diagram_id": diag},
            headers={**headers, "If-Match": str(ver)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["detail_diagram_id"] == diag

    async def test_update_clears_detail_diagram(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        diag = await _create_diagram(client, headers, set_id=set_id)
        created = await _create_element(
            client, headers, set_id=set_id, detail_diagram_id=diag,
        )
        eid = created["body"]["id"]
        ver = created["body"]["current_version"]

        resp = await client.put(
            f"/api/elements/{eid}",
            json={"name": "E", "data": {}, "detail_diagram_id": None},
            headers={**headers, "If-Match": str(ver)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["detail_diagram_id"] is None

    async def test_update_omitting_leaves_untouched(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        diag = await _create_diagram(client, headers, set_id=set_id)
        created = await _create_element(
            client, headers, set_id=set_id, detail_diagram_id=diag,
        )
        eid = created["body"]["id"]
        ver = created["body"]["current_version"]

        resp = await client.put(
            f"/api/elements/{eid}",
            json={"name": "Renamed", "data": {}},  # detail_diagram_id omitted
            headers={**headers, "If-Match": str(ver)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["detail_diagram_id"] == diag

    async def test_update_missing_diagram_returns_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        created = await _create_element(client, headers, set_id=set_id)
        eid = created["body"]["id"]
        ver = created["body"]["current_version"]

        resp = await client.put(
            f"/api/elements/{eid}",
            json={
                "name": "E", "data": {},
                "detail_diagram_id": "00000000-0000-0000-0000-000000000000",
            },
            headers={**headers, "If-Match": str(ver)},
        )
        assert resp.status_code == 422, resp.text


class TestReferencedBy:
    async def test_get_diagram_lists_referencing_elements(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        diag = await _create_diagram(client, headers, set_id=set_id, name="Zone")
        e1 = await _create_element(
            client, headers, set_id=set_id, name="E1", detail_diagram_id=diag,
        )
        # E2 has no detail diagram → must not appear.
        await _create_element(client, headers, set_id=set_id, name="E2")

        resp = await client.get(f"/api/diagrams/{diag}")
        assert resp.status_code == 200, resp.text
        refs = resp.json()["referenced_by_elements"]
        ids = {r["id"] for r in refs}
        assert e1["body"]["id"] in ids
        assert all(r["name"] == "E1" for r in refs)
        assert len(refs) == 1


class TestSmartMarkdownToken:
    async def test_detail_diagram_token_renders_diagram_link(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        target = await _create_diagram(
            client, headers, set_id=set_id, name="Target Zone",
        )
        elem = await _create_element(
            client, headers, set_id=set_id, name="Cap", detail_diagram_id=target,
        )
        eid = elem["body"]["id"]
        source = f"# Demo\n\n- Cap {{{{element:{eid}:detail_diagram}}}}\n"
        smd = await _create_diagram(
            client, headers, set_id=set_id, name="SMD",
            diagram_type="smart_markdown", data={"markdown_source": source},
        )

        resp = await client.get(f"/api/diagrams/{smd}")
        assert resp.status_code == 200, resp.text
        content = resp.json()["data"]["content"]
        assert f"iris://diagram/{target}" in content
        assert "Target Zone" in content

    async def test_detail_diagram_token_strikes_through_when_unset(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        elem = await _create_element(client, headers, set_id=set_id, name="Cap")
        eid = elem["body"]["id"]
        source = f"- Cap {{{{element:{eid}:detail_diagram}}}}\n"
        smd = await _create_diagram(
            client, headers, set_id=set_id, name="SMD",
            diagram_type="smart_markdown", data={"markdown_source": source},
        )

        resp = await client.get(f"/api/diagrams/{smd}")
        assert resp.status_code == 200, resp.text
        content = resp.json()["data"]["content"]
        # Unresolvable token → strikethrough fallback.
        assert "~~" in content
        assert "iris://diagram/" not in content
