"""Tests for SparxEA .qea import -- reader, mapper, converter, and full import."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.import_sparx.converter import bgr_to_rgb, ea_rect_to_position
from app.import_sparx.mapper import (
    map_connector_type,
    map_diagram_type,
    map_object_type,
)
from app.import_sparx.reader import (
    read_attributes,
    read_connectors,
    read_diagram_objects,
    read_diagrams,
    read_elements,
    read_packages,
)
from app.import_sparx.service import import_sparx_file
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

# Path to the sample .qea file
SAMPLE_QEA = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "docs", "reference", "SparxEA", "AIXM_5.1.1_EA16.qea",
)
SAMPLE_QEA = os.path.abspath(SAMPLE_QEA)


# ---------- Fixtures ----------


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
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    """Setup admin user and return auth headers."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------- Reader Tests ----------


class TestReader:
    """Verify the reader can extract data from the sample .qea file."""

    async def test_read_packages(self) -> None:
        packages = await read_packages(SAMPLE_QEA)
        assert len(packages) > 0
        # The sample has 68 packages
        assert len(packages) == 68
        # Check first package has required fields
        pkg = packages[0]
        assert pkg.Package_ID > 0
        assert pkg.ea_guid is not None

    async def test_read_elements(self) -> None:
        elements = await read_elements(SAMPLE_QEA)
        assert len(elements) > 0
        # The sample has 1026 objects
        assert len(elements) == 1026
        # Verify object types present
        types = {e.Object_Type for e in elements}
        assert "Class" in types
        assert "Package" in types

    async def test_read_connectors(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        assert len(connectors) > 0
        # The sample has 1420 connectors
        assert len(connectors) == 1420
        types = {c.Connector_Type for c in connectors}
        assert "Generalization" in types
        assert "Association" in types

    async def test_read_diagrams(self) -> None:
        diagrams = await read_diagrams(SAMPLE_QEA)
        assert len(diagrams) > 0
        # The sample has 107 diagrams
        assert len(diagrams) == 107
        types = {d.Diagram_Type for d in diagrams}
        assert "Logical" in types

    async def test_read_diagram_objects(self) -> None:
        diagram_objects = await read_diagram_objects(SAMPLE_QEA)
        assert len(diagram_objects) > 0
        # The sample has 882 diagram objects
        assert len(diagram_objects) == 882
        # Check coordinate values are present
        dobj = diagram_objects[0]
        assert isinstance(dobj.RectTop, int)
        assert isinstance(dobj.RectLeft, int)

    async def test_read_attributes(self) -> None:
        attributes = await read_attributes(SAMPLE_QEA)
        assert len(attributes) > 0
        # The sample has 4201 attributes
        assert len(attributes) == 4201
        # Check first attribute has name and type
        attr = attributes[0]
        assert attr.Name is not None


# ---------- Mapper Tests ----------


class TestMapper:
    """Verify type mapping from EA types to Iris types."""

    def test_map_class(self) -> None:
        assert map_object_type("Class") == "class"

    def test_map_interface(self) -> None:
        assert map_object_type("Interface") == "interface_uml"

    def test_map_package_is_special(self) -> None:
        assert map_object_type("Package") == "_package"

    def test_skip_note(self) -> None:
        assert map_object_type("Note") is None

    def test_skip_boundary(self) -> None:
        assert map_object_type("Boundary") is None

    def test_skip_text(self) -> None:
        assert map_object_type("Text") is None

    def test_unknown_object_type_returns_none(self) -> None:
        assert map_object_type("SomeUnknownType") is None

    def test_map_generalization(self) -> None:
        assert map_connector_type("Generalization") == "generalization"

    def test_map_association(self) -> None:
        assert map_connector_type("Association") == "association"

    def test_map_dependency(self) -> None:
        assert map_connector_type("Dependency") == "dependency"

    def test_skip_notelink(self) -> None:
        assert map_connector_type("NoteLink") is None

    def test_skip_notelink_lowercase(self) -> None:
        assert map_connector_type("Notelink") is None

    def test_unknown_connector_returns_none(self) -> None:
        assert map_connector_type("SomeUnknownConnector") is None

    def test_map_logical_diagram(self) -> None:
        assert map_diagram_type("Logical") == "uml"

    def test_map_sequence_diagram(self) -> None:
        assert map_diagram_type("Sequence") == "sequence"

    def test_map_custom_diagram(self) -> None:
        assert map_diagram_type("Custom") == "archimate"

    def test_unknown_diagram_defaults_to_simple(self) -> None:
        assert map_diagram_type("SomeUnknownDiagram") == "simple"

    def test_map_package_diagram(self) -> None:
        assert map_diagram_type("Package") == "uml"


# ---------- Converter Tests ----------


class TestConverter:
    """Verify coordinate and colour conversion."""

    def test_bgr_to_rgb_basic(self) -> None:
        # Pure red in BGR is 0x0000FF, should produce #ff0000
        assert bgr_to_rgb(0x0000FF) == "#ff0000"

    def test_bgr_to_rgb_blue(self) -> None:
        # Pure blue in BGR is 0xFF0000, should produce #0000ff
        assert bgr_to_rgb(0xFF0000) == "#0000ff"

    def test_bgr_to_rgb_green(self) -> None:
        # Pure green in BGR is 0x00FF00, should produce #00ff00
        assert bgr_to_rgb(0x00FF00) == "#00ff00"

    def test_bgr_to_rgb_white(self) -> None:
        assert bgr_to_rgb(0xFFFFFF) == "#ffffff"

    def test_bgr_to_rgb_black(self) -> None:
        assert bgr_to_rgb(0x000000) == "#000000"

    def test_bgr_to_rgb_negative_returns_white(self) -> None:
        assert bgr_to_rgb(-1) == "#FFFFFF"

    def test_ea_rect_to_position_basic(self) -> None:
        # From sample data: RectTop=-9, RectBottom=-417, RectLeft=605, RectRight=1061
        pos = ea_rect_to_position(605, 1061, -9, -417)
        assert pos["x"] == 605
        assert pos["y"] == 9  # -(-9) = 9
        assert pos["width"] == 456  # 1061 - 605
        assert pos["height"] == 408  # abs(-9 - (-417)) = 408

    def test_ea_rect_minimum_dimensions(self) -> None:
        # Small rect should be clamped to minimums
        pos = ea_rect_to_position(0, 50, -10, -30)
        assert pos["width"] == 100  # clamped from 50 to 100
        assert pos["height"] == 60  # clamped from 20 to 60

    def test_ea_rect_to_position_typical(self) -> None:
        # From sample: RectTop=-23, RectBottom=-102, RectLeft=324, RectRight=579
        pos = ea_rect_to_position(324, 579, -23, -102)
        assert pos["x"] == 324
        assert pos["y"] == 23
        assert pos["width"] == 255
        assert pos["height"] == 79

    def test_ea_rect_y_ordering(self) -> None:
        # Elements higher on screen (less negative RectTop) should have smaller y
        pos_high = ea_rect_to_position(0, 200, -10, -100)  # higher on screen
        pos_low = ea_rect_to_position(0, 200, -500, -600)  # lower on screen
        assert pos_high["y"] < pos_low["y"]


# ---------- Full Import Tests ----------


class TestFullImport:
    """Verify the full import pipeline using the sample .qea file."""

    async def test_import_creates_models_for_packages(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)

        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        # Get user id from database
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]

        summary = await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # 68 packages should create 68 models
        assert summary.models_created == 68
        assert summary.entities_created > 0
        assert summary.diagrams_created > 0

    async def test_import_creates_entities_for_classes(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)

        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]

        summary = await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # 953 classes + others, minus skipped types (Note=5, Boundary=1, Package=67)
        # 953 classes should be created as entities
        assert summary.entities_created == 953
        # Notes (5) and Boundary (1) should be skipped
        assert summary.elements_skipped == 6

    async def test_import_creates_relationships(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)

        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]

        summary = await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Should create relationships for mapped connector types
        assert summary.relationships_created > 0
        # NoteLinks should be skipped
        assert summary.connectors_skipped >= 3  # At least the 3 NoteLinks

    async def test_import_creates_diagrams(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)

        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]

        summary = await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # 107 diagrams should be created
        assert summary.diagrams_created == 107

    async def test_import_summary_totals_are_consistent(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)

        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]

        summary = await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # entities_created + elements_skipped + packages = total objects
        # Packages are 67 in t_object (Object_Type='Package')
        total_objects = 1026
        assert summary.entities_created + summary.elements_skipped + 67 == total_objects

        # relationships_created + connectors_skipped = total connectors
        total_connectors = 1420
        assert summary.relationships_created + summary.connectors_skipped == total_connectors


# ---------- Router Tests ----------


class TestImportRouter:
    """Verify the import API endpoint."""

    async def test_import_rejects_non_qea(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/import/sparx",
            files={"file": ("test.txt", b"not a qea file", "application/octet-stream")},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "qea" in resp.json()["detail"].lower()

    async def test_import_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/import/sparx",
            files={"file": ("test.qea", b"fake", "application/octet-stream")},
        )
        assert resp.status_code == 401

    async def test_import_via_endpoint(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        with open(SAMPLE_QEA, "rb") as f:
            content = f.read()
        resp = await client.post(
            "/api/import/sparx",
            files={"file": ("AIXM_5.1.1_EA16.qea", content, "application/octet-stream")},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["models_created"] == 68
        assert data["entities_created"] > 0
        assert data["diagrams_created"] == 107
        assert isinstance(data["warnings"], list)
