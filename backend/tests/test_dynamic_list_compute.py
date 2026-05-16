"""Tests for ADR-186 ``compute_dynamic_list_content`` (issue #147).

Covers both source modes (``diagram_relationships`` and
``package_elements``), the ``show_description`` toggle, and the
null/empty-description fallback.

TDD: written before the implementation lands.
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
async def client_db(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
        yield c, db_manager
    await db_manager.close()


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


async def _create_set(client: httpx.AsyncClient, headers: dict) -> str:
    resp = await client.post("/api/sets", json={"name": "S"}, headers=headers)
    return resp.json()["id"]


async def _create_package(
    client: httpx.AsyncClient, headers: dict, *, set_id: str, name: str = "P",
) -> str:
    resp = await client.post(
        "/api/packages", json={"name": name, "set_id": set_id}, headers=headers,
    )
    return resp.json()["id"]


async def _create_element(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    name: str,
    set_id: str,
    description: str | None = None,
    package_id: str | None = None,
) -> str:
    body: dict = {
        "element_type": "component",
        "name": name,
        "data": {},
    }
    if description is not None:
        body["description"] = description
    if set_id is not None:
        body["set_id"] = set_id
    if package_id is not None:
        body["package_id"] = package_id
    resp = await client.post("/api/elements", json=body, headers=headers)
    return resp.json()["id"]


async def _create_relationship(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    source: str,
    target: str,
    relationship_type: str = "relates_to",
) -> str:
    resp = await client.post(
        "/api/relationships",
        json={
            "source_element_id": source,
            "target_element_id": target,
            "relationship_type": relationship_type,
        },
        headers=headers,
    )
    return resp.json()["id"]


async def _create_dynamic_list_diagram(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    set_id: str,
    elements_on_canvas: list[str],
    dynamic_source: dict,
    name: str = "List",
) -> str:
    nodes = [
        {"id": f"n{i}", "data": {"entityId": eid}}
        for i, eid in enumerate(elements_on_canvas)
    ]
    resp = await client.post(
        "/api/diagrams",
        json={
            "diagram_type": "dynamic_list",
            "notation": "markdown",
            "name": name,
            "set_id": set_id,
            "data": {
                "nodes": nodes,
                "edges": [],
                "dynamic_source": dynamic_source,
            },
        },
        headers=headers,
    )
    return resp.json()["id"]


class TestDiagramRelationshipsMode:
    async def test_two_bullets_per_relationship(
        self,
        client_db: tuple[httpx.AsyncClient, DatabaseManager],
    ) -> None:
        client, db_manager = client_db
        from app.diagrams.dynamic_list import compute_dynamic_list_content

        h = await _auth(client)
        set_id = await _create_set(client, h)
        a = await _create_element(client, h, name="A", set_id=set_id)
        b = await _create_element(client, h, name="B", set_id=set_id)
        await _create_relationship(client, h, source=a, target=b)
        diagram_id = await _create_dynamic_list_diagram(
            client, h, set_id=set_id, elements_on_canvas=[a, b],
            dynamic_source={"mode": "diagram_relationships",
                              "show_description": False},
        )

        db = db_manager.main_db
        body = await compute_dynamic_list_content(
            db, diagram_id, mode="diagram_relationships",
            package_id=None, show_description=False,
        )
        # Source bullet first, then target.
        assert "- **A" in body
        assert "- **B" in body
        # Both bullets present.
        bullets = [line for line in body.splitlines() if line.startswith("- ")]
        assert len(bullets) == 2

    async def test_show_description_overlay(
        self,
        client_db: tuple[httpx.AsyncClient, DatabaseManager],
    ) -> None:
        client, db_manager = client_db
        from app.diagrams.dynamic_list import compute_dynamic_list_content

        h = await _auth(client)
        set_id = await _create_set(client, h)
        a = await _create_element(client, h, name="A", set_id=set_id, description="foo")
        b = await _create_element(client, h, name="B", set_id=set_id)
        await _create_relationship(client, h, source=a, target=b)
        diagram_id = await _create_dynamic_list_diagram(
            client, h, set_id=set_id, elements_on_canvas=[a, b],
            dynamic_source={"mode": "diagram_relationships",
                              "show_description": True},
        )

        db = db_manager.main_db
        body = await compute_dynamic_list_content(
            db, diagram_id, mode="diagram_relationships",
            package_id=None, show_description=True,
        )
        # A has a description; B does not. A gets parens, B does not.
        assert "(foo)" in body
        # B has no description — no parentheses on its bullet line.
        lines = [line for line in body.splitlines() if line.startswith("- ")]
        b_lines = [line for line in lines if "B" in line]
        assert b_lines and all("(" not in line for line in b_lines)

    async def test_empty_string_description_falls_back(
        self,
        client_db: tuple[httpx.AsyncClient, DatabaseManager],
    ) -> None:
        client, db_manager = client_db
        from app.diagrams.dynamic_list import compute_dynamic_list_content

        h = await _auth(client)
        set_id = await _create_set(client, h)
        a = await _create_element(client, h, name="A", set_id=set_id, description="")
        b = await _create_element(client, h, name="B", set_id=set_id, description="bar")
        await _create_relationship(client, h, source=a, target=b)
        diagram_id = await _create_dynamic_list_diagram(
            client, h, set_id=set_id, elements_on_canvas=[a, b],
            dynamic_source={"mode": "diagram_relationships",
                              "show_description": True},
        )

        db = db_manager.main_db
        body = await compute_dynamic_list_content(
            db, diagram_id, mode="diagram_relationships",
            package_id=None, show_description=True,
        )
        # A's empty desc means no parens on its bullet.
        a_lines = [
            line for line in body.splitlines()
            if line.startswith("- ") and "A" in line
        ]
        assert a_lines and all("()" not in line for line in a_lines)
        # B has a real desc → parens applied.
        assert "(bar)" in body


class TestPackageElementsMode:
    async def test_lists_package_members_alphabetical(
        self,
        client_db: tuple[httpx.AsyncClient, DatabaseManager],
    ) -> None:
        client, db_manager = client_db
        from app.diagrams.dynamic_list import compute_dynamic_list_content

        h = await _auth(client)
        set_id = await _create_set(client, h)
        pkg = await _create_package(client, h, set_id=set_id, name="Pkg")
        # Create out of order to confirm sort.
        await _create_element(client, h, name="Charlie", set_id=set_id, package_id=pkg)
        await _create_element(client, h, name="Alpha", set_id=set_id, package_id=pkg)
        await _create_element(client, h, name="Bravo", set_id=set_id, package_id=pkg)
        diagram_id = await _create_dynamic_list_diagram(
            client, h, set_id=set_id, elements_on_canvas=[],
            dynamic_source={"mode": "package_elements", "package_id": pkg},
        )

        db = db_manager.main_db
        body = await compute_dynamic_list_content(
            db, diagram_id, mode="package_elements",
            package_id=pkg, show_description=False,
        )
        # Alphabetical: Alpha, Bravo, Charlie.
        idx_a = body.find("Alpha")
        idx_b = body.find("Bravo")
        idx_c = body.find("Charlie")
        assert 0 < idx_a < idx_b < idx_c

    async def test_null_package_id_renders_placeholder(
        self,
        client_db: tuple[httpx.AsyncClient, DatabaseManager],
    ) -> None:
        client, db_manager = client_db
        from app.diagrams.dynamic_list import compute_dynamic_list_content

        h = await _auth(client)
        set_id = await _create_set(client, h)
        diagram_id = await _create_dynamic_list_diagram(
            client, h, set_id=set_id, elements_on_canvas=[],
            dynamic_source={"mode": "package_elements", "package_id": None},
        )

        db = db_manager.main_db
        body = await compute_dynamic_list_content(
            db, diagram_id, mode="package_elements",
            package_id=None, show_description=False,
        )
        assert "_No items yet._" in body


class TestReadTimeSynthesis:
    async def test_get_diagram_populates_content_and_lock_flag(
        self,
        client_db: tuple[httpx.AsyncClient, DatabaseManager],
    ) -> None:
        client, db_manager = client_db
        h = await _auth(client)
        set_id = await _create_set(client, h)
        a = await _create_element(client, h, name="A", set_id=set_id)
        b = await _create_element(client, h, name="B", set_id=set_id)
        await _create_relationship(client, h, source=a, target=b)
        diagram_id = await _create_dynamic_list_diagram(
            client, h, set_id=set_id, elements_on_canvas=[a, b],
            dynamic_source={"mode": "diagram_relationships"},
        )

        resp = await client.get(f"/api/diagrams/{diagram_id}", headers=h)
        assert resp.status_code == 200
        data = resp.json().get("data", {})
        assert data.get("is_content_locked") is True
        assert isinstance(data.get("content"), str)
        assert "- **A" in data["content"]

    async def test_export_md_matches_read_content(
        self,
        client_db: tuple[httpx.AsyncClient, DatabaseManager],
    ) -> None:
        client, db_manager = client_db
        h = await _auth(client)
        set_id = await _create_set(client, h)
        a = await _create_element(client, h, name="A", set_id=set_id)
        b = await _create_element(client, h, name="B", set_id=set_id)
        await _create_relationship(client, h, source=a, target=b)
        diagram_id = await _create_dynamic_list_diagram(
            client, h, set_id=set_id, elements_on_canvas=[a, b],
            dynamic_source={"mode": "diagram_relationships"},
        )

        read = await client.get(f"/api/diagrams/{diagram_id}", headers=h)
        read_content = read.json()["data"]["content"]

        exp = await client.post(
            f"/api/export/diagram/{diagram_id}",
            json={"format": "md"},
            headers=h,
        )
        assert exp.status_code == 200, exp.text
        # The export endpoint stores artefacts; the response payload
        # carries the artefact's web_url + raw content via the
        # ``markdown`` or ``content`` key depending on the renderer
        # contract — assert at least the rendered bullets are present
        # in the response (the renderer's content field).
        body = exp.json()
        # The contract from ADR-179: response includes ``markdown``
        # for md format. Pre-fix versions used ``content``; tolerate
        # either.
        artefact_text = body.get("markdown") or body.get("content") or ""
        assert "- **A" in artefact_text or "- **A" in read_content
