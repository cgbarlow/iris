"""Tests for v3 example seed with all 31 diagram-type/notation permutations (ADR-083).

Tests verify: 5 packages, 32 diagrams covering all valid registry pairs,
55 elements across 4 notations, 50 relationships, tags, v2→v3 migration,
and idempotency.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import pytest

from app.seed.example_models import seed_example_models

if TYPE_CHECKING:
    import aiosqlite


# ── Helpers ──────────────────────────────────────────────────────────────────

_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
_DEFAULT_SET_ID = "00000000-0000-0000-0000-000000000001"
_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _gen_id(prefix: str, index: int) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"{prefix}-{index}"))


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Run all migrations needed for the seed to work."""
    from app.migrations.m001_roles_users import up as m001
    from app.migrations.m002_entities_relationships_models import up as m002
    from app.migrations.m004_comments_bookmarks import up as m004
    from app.migrations.m005_search import up as m005
    from app.migrations.m006_settings import up as m006
    from app.migrations.m007_thumbnails import up as m007
    from app.migrations.m008_entity_tags import up as m008
    from app.migrations.m009_model_tags import up as m009
    from app.migrations.m010_thumbnail_themes import up as m010
    from app.migrations.m011_model_hierarchy import up as m011
    from app.migrations.m012_sets import up as m012
    from app.migrations.m013_set_thumbnails import up as m013
    from app.migrations.m014_sets_partial_unique import up as m014
    from app.migrations.m015_model_relationships import up as m015
    from app.migrations.m016_naming_rename import up as m016
    from app.migrations.m017_views import up as m017
    from app.migrations.m018_package_bookmarks import up as m018
    from app.migrations.m019_recycle_bin import up as m019
    from app.migrations.m020_diagram_type_notation_registry import up as m020
    from app.migrations.m022_element_notation import up as m022
    from app.migrations.seed import seed_roles_and_permissions

    await m001(db)
    await m002(db)
    await m004(db)
    await m005(db)
    await m006(db)
    await m007(db)
    await m008(db)
    await m009(db)
    await m010(db)
    await m011(db)
    await m012(db)
    await m013(db)
    await m014(db)
    await m015(db)
    await m016(db)
    await m017(db)
    await m018(db)
    await m019(db)
    await m020(db)
    await m022(db)
    await seed_roles_and_permissions(db)


async def _create_active_user(db: aiosqlite.Connection) -> None:
    """Create an active admin user so the seed doesn't skip."""
    await db.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active) "
        "VALUES (?, ?, ?, ?, ?)",
        ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "testadmin",
         "!test-hash", "admin", 1),
    )
    await db.commit()


@pytest.fixture
async def seeded_db(main_db: aiosqlite.Connection) -> aiosqlite.Connection:
    """Fully migrated + seeded database."""
    await _run_migrations(main_db)
    await _create_active_user(main_db)
    await seed_example_models(main_db)
    return main_db


# ── All 31 valid (diagram_type, notation) pairs ─────────────────────────────

_ALL_VALID_PAIRS = [
    ("component", "simple"),
    ("sequence", "simple"),
    ("deployment", "simple"),
    ("process", "simple"),
    ("roadmap", "simple"),
    ("free_form", "simple"),
    ("use_case", "simple"),
    ("state_machine", "simple"),
    ("system_context", "simple"),
    ("container", "simple"),
    ("component", "uml"),
    ("sequence", "uml"),
    ("class", "uml"),
    ("deployment", "uml"),
    ("process", "uml"),
    ("free_form", "uml"),
    ("use_case", "uml"),
    ("state_machine", "uml"),
    ("component", "archimate"),
    ("deployment", "archimate"),
    ("process", "archimate"),
    ("roadmap", "archimate"),
    ("free_form", "archimate"),
    ("motivation", "archimate"),
    ("strategy", "archimate"),
    ("component", "c4"),
    ("sequence", "c4"),
    ("deployment", "c4"),
    ("free_form", "c4"),
    ("system_context", "c4"),
    ("container", "c4"),
]


# ── Package tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_creates_five_packages(seeded_db: aiosqlite.Connection) -> None:
    """Seed creates exactly 5 packages in Default set."""
    cursor = await seeded_db.execute(
        "SELECT COUNT(*) FROM packages WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    row = await cursor.fetchone()
    assert row[0] == 5


@pytest.mark.asyncio
async def test_root_package_has_no_parent(seeded_db: aiosqlite.Connection) -> None:
    """Root package 'Iris' has no parent_package_id."""
    root_id = _gen_id("pkg", 0)
    cursor = await seeded_db.execute(
        "SELECT parent_package_id FROM packages WHERE id = ?",
        (root_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] is None


@pytest.mark.asyncio
async def test_root_package_named_iris(seeded_db: aiosqlite.Connection) -> None:
    """Root package is named 'Iris'."""
    root_id = _gen_id("pkg", 0)
    cursor = await seeded_db.execute(
        "SELECT name FROM package_versions WHERE package_id = ? AND version = 1",
        (root_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "Iris"


@pytest.mark.asyncio
async def test_four_children_reference_root(seeded_db: aiosqlite.Connection) -> None:
    """4 child packages reference the root 'Iris' package as parent."""
    root_id = _gen_id("pkg", 0)
    cursor = await seeded_db.execute(
        "SELECT COUNT(*) FROM packages WHERE parent_package_id = ? AND is_deleted = 0",
        (root_id,),
    )
    row = await cursor.fetchone()
    assert row[0] == 4


@pytest.mark.asyncio
async def test_notation_package_names(seeded_db: aiosqlite.Connection) -> None:
    """Child packages are named by notation."""
    expected = {
        1: "Simple Notation",
        2: "UML Notation",
        3: "ArchiMate Notation",
        4: "C4 Notation",
    }
    for idx, expected_name in expected.items():
        pkg_id = _gen_id("pkg", idx)
        cursor = await seeded_db.execute(
            "SELECT name FROM package_versions WHERE package_id = ? AND version = 1",
            (pkg_id,),
        )
        row = await cursor.fetchone()
        assert row is not None, f"Package pkg-{idx} not found"
        assert row[0] == expected_name


# ── Diagram tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_thirty_two_diagrams_total(seeded_db: aiosqlite.Connection) -> None:
    """Seed creates exactly 32 diagrams (31 permutations + 1 overview)."""
    cursor = await seeded_db.execute(
        "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    row = await cursor.fetchone()
    assert row[0] == 32


@pytest.mark.asyncio
async def test_all_diagrams_have_parent_package(seeded_db: aiosqlite.Connection) -> None:
    """All 32 diagrams have parent_package_id set (not NULL)."""
    cursor = await seeded_db.execute(
        "SELECT COUNT(*) FROM diagrams "
        "WHERE set_id = ? AND is_deleted = 0 AND parent_package_id IS NOT NULL",
        (_DEFAULT_SET_ID,),
    )
    row = await cursor.fetchone()
    assert row[0] == 32


@pytest.mark.asyncio
async def test_all_31_permutations_present(seeded_db: aiosqlite.Connection) -> None:
    """Every valid (diagram_type, notation) pair has at least one diagram."""
    cursor = await seeded_db.execute(
        "SELECT diagram_type, notation FROM diagrams "
        "WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    rows = await cursor.fetchall()
    found_pairs = {(r[0], r[1]) for r in rows}
    for pair in _ALL_VALID_PAIRS:
        assert pair in found_pairs, f"Missing diagram for {pair}"


@pytest.mark.asyncio
async def test_all_diagrams_have_example_tag(seeded_db: aiosqlite.Connection) -> None:
    """All seed diagrams have the 'example' tag."""
    cursor = await seeded_db.execute(
        "SELECT d.id FROM diagrams d "
        "WHERE d.set_id = ? AND d.is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    diagram_ids = [r[0] for r in await cursor.fetchall()]
    for did in diagram_ids:
        cursor = await seeded_db.execute(
            "SELECT COUNT(*) FROM diagram_tags WHERE diagram_id = ? AND tag = 'example'",
            (did,),
        )
        row = await cursor.fetchone()
        assert row[0] > 0, f"Diagram {did} missing 'example' tag"


@pytest.mark.asyncio
async def test_overview_diagram_has_modelrefs(seeded_db: aiosqlite.Connection) -> None:
    """System Overview diagram includes modelref nodes."""
    overview_id = _gen_id("diagram", 31)
    cursor = await seeded_db.execute(
        "SELECT dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.id = ?",
        (overview_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    data = json.loads(row[0])
    modelref_nodes = [n for n in data["nodes"] if n["type"] == "modelref"]
    assert len(modelref_nodes) >= 4


# ── Element and relationship tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_fifty_five_elements(seeded_db: aiosqlite.Connection) -> None:
    """Seed creates exactly 55 elements."""
    cursor = await seeded_db.execute(
        "SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    assert (await cursor.fetchone())[0] == 55


@pytest.mark.asyncio
async def test_fifty_relationships(seeded_db: aiosqlite.Connection) -> None:
    """Seed creates exactly 50 relationships."""
    cursor = await seeded_db.execute(
        "SELECT COUNT(*) FROM relationships WHERE is_deleted = 0",
    )
    assert (await cursor.fetchone())[0] == 50


@pytest.mark.asyncio
async def test_all_elements_have_example_tag(seeded_db: aiosqlite.Connection) -> None:
    """All seed elements have the 'example' tag."""
    cursor = await seeded_db.execute(
        "SELECT e.id FROM elements e "
        "WHERE e.set_id = ? AND e.is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    element_ids = [r[0] for r in await cursor.fetchall()]
    for eid in element_ids:
        cursor = await seeded_db.execute(
            "SELECT COUNT(*) FROM element_tags WHERE element_id = ? AND tag = 'example'",
            (eid,),
        )
        row = await cursor.fetchone()
        assert row[0] > 0, f"Element {eid} missing 'example' tag"


@pytest.mark.asyncio
async def test_elements_have_correct_notations(seeded_db: aiosqlite.Connection) -> None:
    """Elements have the correct notation set per their type grouping."""
    cursor = await seeded_db.execute(
        "SELECT notation, COUNT(*) FROM elements "
        "WHERE set_id = ? AND is_deleted = 0 GROUP BY notation",
        (_DEFAULT_SET_ID,),
    )
    rows = await cursor.fetchall()
    notation_counts = {r[0]: r[1] for r in rows}
    assert notation_counts.get("simple", 0) == 15
    assert notation_counts.get("uml", 0) == 12
    assert notation_counts.get("archimate", 0) == 18
    assert notation_counts.get("c4", 0) == 10


# ── Idempotency and migration tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_idempotent_no_duplicates(main_db: aiosqlite.Connection) -> None:
    """Running seed twice doesn't create duplicate data."""
    await _run_migrations(main_db)
    await _create_active_user(main_db)
    await seed_example_models(main_db)
    await seed_example_models(main_db)

    cursor = await main_db.execute(
        "SELECT COUNT(*) FROM packages WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    assert (await cursor.fetchone())[0] == 5

    cursor = await main_db.execute(
        "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    assert (await cursor.fetchone())[0] == 32


@pytest.mark.asyncio
async def test_v1_seed_cleared_on_reseed(main_db: aiosqlite.Connection) -> None:
    """Old v1 seed (element_tags exist, no root package) is cleared and reseeded."""
    await _run_migrations(main_db)
    await _create_active_user(main_db)

    # Simulate v1 seed: create system user + one element with 'example' tag but no packages
    from datetime import UTC, datetime
    now = datetime.now(tz=UTC).isoformat()
    await main_db.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active) "
        "VALUES (?, ?, ?, ?, ?)",
        (_SYSTEM_USER_ID, "system", "!no-login-seed-user", "viewer", 0),
    )
    elem_id = _gen_id("element", 0)
    await main_db.execute(
        "INSERT INTO elements (id, element_type, set_id, current_version, "
        "created_at, created_by, updated_at) VALUES (?, ?, ?, 1, ?, ?, ?)",
        (elem_id, "component", _DEFAULT_SET_ID, now, _SYSTEM_USER_ID, now),
    )
    await main_db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, created_at, created_by) VALUES (?, 1, ?, ?, '{}', 'create', ?, ?)",
        (elem_id, "Old Element", "Old", now, _SYSTEM_USER_ID),
    )
    await main_db.execute(
        "INSERT INTO element_tags (element_id, tag, created_at, created_by) "
        "VALUES (?, 'example', ?, ?)",
        (elem_id, now, _SYSTEM_USER_ID),
    )
    await main_db.commit()

    # Now run seed — should detect v1 format, clear, and reseed v3
    await seed_example_models(main_db)

    # Should now have v3 packages
    cursor = await main_db.execute(
        "SELECT COUNT(*) FROM packages WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    assert (await cursor.fetchone())[0] == 5

    # Should have 55 elements (not 56 — the old one was cleared)
    cursor = await main_db.execute(
        "SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    assert (await cursor.fetchone())[0] == 55


@pytest.mark.asyncio
async def test_v2_seed_upgraded_to_v3(main_db: aiosqlite.Connection) -> None:
    """Old v2 seed (4 packages, no pkg-4) is cleared and reseeded as v3."""
    await _run_migrations(main_db)
    await _create_active_user(main_db)

    # Simulate v2 seed: create root package but not pkg-4
    from datetime import UTC, datetime
    now = datetime.now(tz=UTC).isoformat()
    await main_db.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active) "
        "VALUES (?, ?, ?, ?, ?)",
        (_SYSTEM_USER_ID, "system", "!no-login-seed-user", "viewer", 0),
    )
    root_id = _gen_id("pkg", 0)
    await main_db.execute(
        "INSERT INTO packages (id, current_version, "
        "created_at, created_by, updated_at, set_id) "
        "VALUES (?, 1, ?, ?, ?, ?)",
        (root_id, now, _SYSTEM_USER_ID, now, _DEFAULT_SET_ID),
    )
    await main_db.execute(
        "INSERT INTO package_versions (package_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by) "
        "VALUES (?, 1, ?, ?, '{}', 'create', ?, ?, ?)",
        (root_id, "Iris", "Old root", "Seed", now, _SYSTEM_USER_ID),
    )
    await main_db.commit()

    # Run seed — should detect v2 (root exists, no pkg-4) and upgrade to v3
    await seed_example_models(main_db)

    # Should now have 5 packages
    cursor = await main_db.execute(
        "SELECT COUNT(*) FROM packages WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    assert (await cursor.fetchone())[0] == 5

    # Should have 32 diagrams
    cursor = await main_db.execute(
        "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
        (_DEFAULT_SET_ID,),
    )
    assert (await cursor.fetchone())[0] == 32
