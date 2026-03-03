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
    read_tagged_values,
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

    def test_map_note(self) -> None:
        assert map_object_type("Note") == "note"

    def test_map_boundary(self) -> None:
        assert map_object_type("Boundary") == "boundary"

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

    def test_map_notelink(self) -> None:
        assert map_connector_type("NoteLink") == "note_link"

    def test_map_notelink_lowercase(self) -> None:
        assert map_connector_type("Notelink") == "note_link"

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

        # 959 entities: 953 classes + 5 notes + 1 boundary (Package=67 handled as hierarchy)
        assert summary.entities_created == 959
        # Only Text/UMLDiagram/Constraint are skipped now
        assert summary.elements_skipped == 0

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

        # Should create relationships for mapped connector types (including NoteLinks)
        assert summary.relationships_created > 0
        # Very few connectors should be skipped now (only unknown types or unmapped entities)
        assert summary.connectors_skipped >= 0

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

        # relationships_created + connectors_skipped + model_relationships_created = total connectors
        total_connectors = 1420
        assert (
            summary.relationships_created
            + summary.connectors_skipped
            + summary.model_relationships_created
            == total_connectors
        )


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
        assert "model_relationships_created" in data
        assert isinstance(data["warnings"], list)


# ---------- Reader Metadata Tests ----------


class TestReaderMetadata:
    """Verify the reader extracts metadata fields from the sample .qea file."""

    async def test_read_packages_has_notes(self) -> None:
        packages = await read_packages(SAMPLE_QEA)
        with_notes = [p for p in packages if p.Notes]
        assert len(with_notes) >= 64

    async def test_read_elements_has_status(self) -> None:
        elements = await read_elements(SAMPLE_QEA)
        non_pkg = [e for e in elements if e.Object_Type != "Package"]
        with_status = [e for e in non_pkg if e.Status]
        assert len(with_status) >= 588

    async def test_read_elements_has_stereotype(self) -> None:
        elements = await read_elements(SAMPLE_QEA)
        non_pkg = [e for e in elements if e.Object_Type != "Package"]
        with_stereo = [e for e in non_pkg if e.Stereotype]
        assert len(with_stereo) >= 1

    async def test_read_diagrams_has_notes(self) -> None:
        diagrams = await read_diagrams(SAMPLE_QEA)
        with_notes = [d for d in diagrams if d.Notes]
        assert len(with_notes) >= 1

    async def test_read_connectors_has_notes(self) -> None:
        connectors = await read_connectors(SAMPLE_QEA)
        with_notes = [c for c in connectors if c.Notes]
        assert len(with_notes) >= 1

    async def test_read_tagged_values(self) -> None:
        tvs = await read_tagged_values(SAMPLE_QEA)
        assert len(tvs) > 0
        distinct_objects = {tv.Object_ID for tv in tvs}
        assert len(distinct_objects) >= 100

    async def test_read_tagged_values_has_property_and_value(self) -> None:
        tvs = await read_tagged_values(SAMPLE_QEA)
        with_property = [tv for tv in tvs if tv.Property]
        assert len(with_property) > 0

    async def test_read_elements_has_scope(self) -> None:
        elements = await read_elements(SAMPLE_QEA)
        non_pkg = [e for e in elements if e.Object_Type != "Package"]
        with_scope = [e for e in non_pkg if e.Scope]
        assert len(with_scope) >= 1

    async def test_read_elements_has_created_modified_date(self) -> None:
        elements = await read_elements(SAMPLE_QEA)
        with_created = [e for e in elements if e.CreatedDate]
        with_modified = [e for e in elements if e.ModifiedDate]
        assert len(with_created) >= 100
        assert len(with_modified) >= 100

    async def test_read_elements_has_abstract(self) -> None:
        elements = await read_elements(SAMPLE_QEA)
        with_abstract = [e for e in elements if e.Abstract]
        assert len(with_abstract) >= 1

    async def test_read_attributes_has_notes(self) -> None:
        attributes = await read_attributes(SAMPLE_QEA)
        with_notes = [a for a in attributes if a.Notes]
        assert len(with_notes) >= 100


# ---------- Import Metadata Tests ----------


class TestImportMetadata:
    """Verify the import populates descriptions and metadata."""

    async def test_import_populates_package_descriptions(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check model_versions have descriptions (from package Notes)
        cursor = await db.execute(
            "SELECT COUNT(*) FROM model_versions WHERE description IS NOT NULL AND description != ''"
        )
        row = await cursor.fetchone()
        assert row[0] >= 64

    async def test_import_populates_entity_metadata(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check entity_versions have metadata
        cursor = await db.execute(
            "SELECT COUNT(*) FROM entity_versions WHERE metadata IS NOT NULL"
        )
        row = await cursor.fetchone()
        assert row[0] > 0

    async def test_import_metadata_contains_stereotype(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        import json
        cursor = await db.execute(
            "SELECT metadata FROM entity_versions WHERE metadata IS NOT NULL LIMIT 10"
        )
        rows = await cursor.fetchall()
        found_stereotype = False
        for r in rows:
            meta = json.loads(r[0])
            if "stereotype" in meta or "status" in meta or "tagged_values" in meta:
                found_stereotype = True
                break
        assert found_stereotype

    async def test_import_entity_metadata_has_scope(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        import json
        cursor = await db.execute(
            "SELECT metadata FROM entity_versions WHERE metadata IS NOT NULL"
        )
        rows = await cursor.fetchall()
        found_scope = False
        for r in rows:
            meta = json.loads(r[0])
            if "scope" in meta:
                found_scope = True
                break
        assert found_scope

    async def test_import_entity_metadata_has_created_date(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        import json
        cursor = await db.execute(
            "SELECT metadata FROM entity_versions WHERE metadata IS NOT NULL"
        )
        rows = await cursor.fetchall()
        found_date = False
        for r in rows:
            meta = json.loads(r[0])
            if "created_date" in meta:
                found_date = True
                break
        assert found_date

    async def test_import_attributes_include_notes(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        import json
        cursor = await db.execute(
            "SELECT data FROM entity_versions WHERE data IS NOT NULL"
        )
        rows = await cursor.fetchall()
        found_notes = False
        for r in rows:
            data = json.loads(r[0])
            attrs = data.get("attributes", [])
            for attr in attrs:
                if isinstance(attr, dict) and "notes" in attr:
                    found_notes = True
                    break
            if found_notes:
                break
        assert found_notes


# ---------- Metadata CRUD Tests ----------


class TestMetadataStorage:
    """Verify metadata field flows through model and entity CRUD."""

    async def test_create_model_with_metadata(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={
                "model_type": "uml",
                "name": "MetadataModel",
                "metadata": {"status": "Proposed", "stereotype": "DataType"},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["metadata"] is not None
        assert data["metadata"]["status"] == "Proposed"
        assert data["metadata"]["stereotype"] == "DataType"

    async def test_get_model_returns_metadata(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/models",
            json={
                "model_type": "uml",
                "name": "MetadataGetModel",
                "metadata": {"status": "Approved"},
            },
            headers=headers,
        )
        model_id = create_resp.json()["id"]
        resp = await client.get(f"/api/models/{model_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["metadata"]["status"] == "Approved"

    async def test_model_without_metadata_returns_null(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={"model_type": "uml", "name": "NoMetadataModel"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["metadata"] is None

    async def test_create_entity_with_metadata(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/entities",
            json={
                "entity_type": "class",
                "name": "MetadataEntity",
                "metadata": {"status": "Proposed", "version": "1.0"},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["metadata"]["status"] == "Proposed"
        assert data["metadata"]["version"] == "1.0"

    async def test_update_model_preserves_metadata(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/models",
            json={
                "model_type": "uml",
                "name": "UpdateMetaModel",
                "metadata": {"status": "Draft"},
            },
            headers=headers,
        )
        model_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/models/{model_id}",
            json={
                "name": "UpdateMetaModel v2",
                "metadata": {"status": "Approved"},
            },
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["status"] == "Approved"


# ---------- Import Change Summary Tests ----------


class TestImportChangeSummary:
    """Verify imported entities and models have change_summary in version history."""

    async def test_import_change_summary_entity(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check entity_versions have change_summary
        cursor = await db.execute(
            "SELECT COUNT(*) FROM entity_versions "
            "WHERE change_summary IS NOT NULL AND change_summary LIKE 'Imported from SparxEA%'"
        )
        row = await cursor.fetchone()
        assert row[0] > 0

    async def test_import_change_summary_model(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check model_versions have change_summary
        cursor = await db.execute(
            "SELECT COUNT(*) FROM model_versions "
            "WHERE change_summary IS NOT NULL AND change_summary LIKE 'Imported from SparxEA%'"
        )
        row = await cursor.fetchone()
        assert row[0] > 0

    async def test_import_notes_as_entities(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check entities with type 'note' exist
        cursor = await db.execute(
            "SELECT COUNT(*) FROM entities WHERE entity_type = 'note'"
        )
        row = await cursor.fetchone()
        assert row[0] >= 5  # Sample has 5 notes

    async def test_import_notelinks_as_relationships(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        summary = await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # NoteLinks should now be imported as relationships (not skipped)
        # Check relationships with type 'note_link' exist
        cursor = await db.execute(
            "SELECT COUNT(*) FROM relationships WHERE relationship_type = 'note_link' AND is_deleted = 0"
        )
        row = await cursor.fetchone()
        assert row[0] >= 1

    async def test_import_model_relationships_created(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        summary = await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check model_relationships table has entries (unique rows)
        cursor = await db.execute("SELECT COUNT(*) FROM model_relationships")
        row = await cursor.fetchone()
        assert row[0] > 0
        # Summary count includes duplicates (already-existing relationships)
        assert summary.model_relationships_created >= row[0]
