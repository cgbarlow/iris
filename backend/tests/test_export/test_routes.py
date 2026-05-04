"""Integration tests for /api/export/* (ADR-128 / SPEC-128-A).

Verifies:
- anonymous callers can export (ADR-123 parity)
- JSON bundles validate against their Pydantic schema
- Markdown output is deterministic and carries correct Content-Disposition
- 404 on missing id, 400 on bad format, 422 on missing format
- 413 when the bundle exceeds MAX_ELEMENTS_PER_BUNDLE
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.export.schemas import (
    DiagramExport,
    ElementExport,
    PackageExport,
    SetExport,
)
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
        rate_limit_anon=10_000,
        rate_limit_general=10_000,
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


async def _seed_minimal_entities(app_state: object) -> dict[str, str]:
    """Insert a set + package + diagram + element directly via the DB.

    Uses the versioned schema: each of elements/packages/diagrams has an
    identity row plus a single v1 row in its `_versions` sibling table.
    """
    db = app_state.db_manager.main_db  # type: ignore[attr-defined]

    # A 'tester' user is needed because entities created_by is an FK.
    import json

    user_id = "tester"
    set_id = str(uuid.uuid4())
    pkg_id = str(uuid.uuid4())
    diag_id = str(uuid.uuid4())
    elem_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active,"
        " created_at) VALUES (?, 'tester', '$argon2id$dummy', 'admin', 1, ?)",
        (user_id, now),
    )
    await db.execute(
        "INSERT INTO sets (id, name, description, created_at, created_by,"
        " updated_at, is_deleted)"
        " VALUES (?, ?, ?, ?, ?, ?, 0)",
        (set_id, "Export Test Set", "A set used by the export tests.", now, user_id, now),
    )

    # Package
    await db.execute(
        "INSERT INTO packages (id, current_version, parent_package_id, created_at,"
        " created_by, updated_at, is_deleted, set_id)"
        " VALUES (?, 1, NULL, ?, ?, ?, 0, ?)",
        (pkg_id, now, user_id, now, set_id),
    )
    await db.execute(
        "INSERT INTO package_versions (package_id, version, name, description,"
        " data, change_type, created_at, created_by)"
        " VALUES (?, 1, ?, ?, '{}', 'create', ?, ?)",
        (pkg_id, "Root Package", "The root.", now, user_id),
    )

    # Element
    await db.execute(
        "INSERT INTO elements (id, element_type, current_version, created_at,"
        " created_by, updated_at, is_deleted, set_id, notation)"
        " VALUES (?, ?, 1, ?, ?, ?, 0, ?, 'simple')",
        (elem_id, "Component", now, user_id, now, set_id),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description,"
        " data, change_type, created_at, created_by)"
        " VALUES (?, 1, ?, ?, '{}', 'create', ?, ?)",
        (elem_id, "Widget", "A component.", now, user_id),
    )

    # Diagram (canvas references the element).
    canvas = json.dumps({
        "nodes": [{"id": "n1", "data": {"element_id": elem_id, "label": "Widget"}}],
        "edges": [],
    })
    await db.execute(
        "INSERT INTO diagrams (id, diagram_type, current_version, parent_package_id,"
        " created_at, created_by, updated_at, is_deleted, set_id, notation)"
        " VALUES (?, 'simple', 1, ?, ?, ?, ?, 0, ?, 'simple')",
        (diag_id, pkg_id, now, user_id, now, set_id),
    )
    await db.execute(
        "INSERT INTO diagram_versions (diagram_id, version, name, description,"
        " data, change_type, created_at, created_by)"
        " VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (diag_id, "Overview", "An overview diagram.", canvas, now, user_id),
    )

    await db.commit()
    return {"set": set_id, "package": pkg_id, "diagram": diag_id, "element": elem_id}


class TestDiagramExport:
    async def test_json_roundtrips(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(
            f"/api/export/diagrams/{ids['diagram']}?format=json",
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert "overview" in resp.headers["content-disposition"].lower()
        bundle = DiagramExport.model_validate_json(resp.text)
        assert bundle.diagram.name == "Overview"
        assert len(bundle.elements) == 1
        assert bundle.elements[0].name == "Widget"

    async def test_markdown_is_deterministic(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        a = (await client.get(f"/api/export/diagrams/{ids['diagram']}?format=markdown")).text
        b = (await client.get(f"/api/export/diagrams/{ids['diagram']}?format=markdown")).text
        assert a == b
        assert a.startswith("# Overview")
        assert "| Type | simple |" in a
        assert "Widget" in a

    async def test_anonymous_allowed(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(f"/api/export/diagrams/{ids['diagram']}?format=json")
        assert resp.status_code == 200  # no Authorization header

    async def test_missing_format_422(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(f"/api/export/diagrams/{ids['diagram']}")
        assert resp.status_code == 422

    async def test_bad_format_422(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(f"/api/export/diagrams/{ids['diagram']}?format=pdf")
        assert resp.status_code == 422

    async def test_404_for_missing(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/api/export/diagrams/00000000-0000-0000-0000-000000000000?format=json",
        )
        assert resp.status_code == 404


class TestElementExport:
    async def test_json_links_back_to_diagrams(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(f"/api/export/elements/{ids['element']}?format=json")
        assert resp.status_code == 200
        bundle = ElementExport.model_validate_json(resp.text)
        assert bundle.element.name == "Widget"
        assert ids["diagram"] in bundle.linked_diagram_ids


class TestPackageExport:
    async def test_package_bundle(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(f"/api/export/packages/{ids['package']}?format=json")
        assert resp.status_code == 200
        bundle = PackageExport.model_validate_json(resp.text)
        assert bundle.package.name == "Root Package"
        assert len(bundle.diagrams) == 1
        assert len(bundle.elements) == 1  # only those referenced by diagrams in subtree

    async def test_markdown(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(
            f"/api/export/packages/{ids['package']}?format=markdown",
        )
        assert resp.status_code == 200
        assert resp.text.startswith("# Root Package")
        assert "Diagrams (1)" in resp.text


class TestSetExport:
    async def test_set_bundle(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(f"/api/export/sets/{ids['set']}?format=json")
        assert resp.status_code == 200
        bundle = SetExport.model_validate_json(resp.text)
        assert bundle.set_.name == "Export Test Set"
        assert len(bundle.packages) == 1
        assert len(bundle.diagrams) == 1
        assert len(bundle.elements) == 1

    async def test_set_markdown_filename(self, client: httpx.AsyncClient) -> None:
        ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
        resp = await client.get(f"/api/export/sets/{ids['set']}?format=markdown")
        assert resp.status_code == 200
        # "Export Test Set" → "export-test-set-<id>.md"
        assert (
            f'filename="export-test-set-{ids["set"]}.md"'
            in resp.headers["content-disposition"]
        )


class TestCollectionExport:
    async def test_missing_collection_404(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/api/export/collections/nope?format=json",
        )
        assert resp.status_code == 404


class TestBundleCap:
    async def test_oversize_set_returns_413(self, client: httpx.AsyncClient) -> None:
        # Monkey-patch the cap down so we don't need to insert 10k rows.
        from app.export import service as export_service

        original = export_service.MAX_ELEMENTS_PER_BUNDLE
        export_service.MAX_ELEMENTS_PER_BUNDLE = 1
        try:
            ids = await _seed_minimal_entities(client._transport.app.state)  # type: ignore[attr-defined]
            resp = await client.get(f"/api/export/sets/{ids['set']}?format=json")
            assert resp.status_code == 413
            body = resp.json()
            assert body["detail"]["limit"] == 1
            assert body["detail"]["count"] > 1
        finally:
            export_service.MAX_ELEMENTS_PER_BUNDLE = original
