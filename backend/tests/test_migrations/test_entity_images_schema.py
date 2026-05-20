"""Schema test for entity_images migration (v6.17.0, ADR-209).

Pairs:
- SQLite  m073_entity_images.py
- Supabase m078_entity_images.sql

Both create:
- `entity_images` junction table with UNIQUE (entity_type, entity_id, image_id)
- Index on (entity_type, entity_id, display_order)
- (Supabase only) RLS policies for authenticated read/insert/delete
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m073 ────────────────────────────────────────────────────────


def test_sqlite_m073_creates_entity_images_table() -> None:
    py = _read("app/migrations/m073_entity_images.py")
    assert "CREATE TABLE IF NOT EXISTS entity_images" in py
    assert "entity_type   TEXT NOT NULL" in py
    assert "entity_id     TEXT NOT NULL" in py
    assert "image_id      TEXT NOT NULL" in py
    assert "display_order INTEGER NOT NULL DEFAULT 0" in py


def test_sqlite_m073_has_unique_constraint() -> None:
    py = _read("app/migrations/m073_entity_images.py")
    assert "UNIQUE (entity_type, entity_id, image_id)" in py


def test_sqlite_m073_has_lookup_index() -> None:
    py = _read("app/migrations/m073_entity_images.py")
    assert "idx_entity_images_entity" in py
    assert "CREATE INDEX IF NOT EXISTS idx_entity_images_entity" in py


# ── Supabase m078 ──────────────────────────────────────────────────────


def test_supabase_m078_creates_table() -> None:
    sql = _read("app/migrations/supabase/m078_entity_images.sql")
    assert "CREATE TABLE IF NOT EXISTS public.entity_images" in sql
    assert "UNIQUE (entity_type, entity_id, image_id)" in sql


def test_supabase_m078_creates_index() -> None:
    sql = _read("app/migrations/supabase/m078_entity_images.sql")
    assert "CREATE INDEX IF NOT EXISTS idx_entity_images_entity" in sql


def test_supabase_m078_enables_rls() -> None:
    sql = _read("app/migrations/supabase/m078_entity_images.sql")
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert 'CREATE POLICY "entity_images_read_authenticated"' in sql
    assert 'CREATE POLICY "entity_images_insert_own"' in sql
    assert 'CREATE POLICY "entity_images_delete_own"' in sql


def test_supabase_m078_references_sqlite_mirror() -> None:
    sql = _read("app/migrations/supabase/m078_entity_images.sql")
    assert "m073" in sql


def test_supabase_m078_idempotent() -> None:
    sql = _read("app/migrations/supabase/m078_entity_images.sql")
    assert "IF NOT EXISTS" in sql
    assert "DROP POLICY IF EXISTS" in sql


def test_supabase_m078_no_boolean_integer_literals() -> None:
    """Protocol §15 regression guard for the v5.12.x boolean-as-integer issue."""
    sql = _read("app/migrations/supabase/m078_entity_images.sql")
    # No `= 1` / `= 0` literals where a boolean would be expected.
    # entity_images has no booleans, so this should trivially pass.
    assert "= 1)" not in sql
    assert "= 0)" not in sql
