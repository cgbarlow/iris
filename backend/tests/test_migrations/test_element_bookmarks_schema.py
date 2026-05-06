"""v5.5.0 (issue #37 reopen): static-parser test asserting that the new
Supabase migration `m047_element_bookmarks.sql` mirrors the SQLite
migration `m038_element_bookmarks.py`.

Pre-fix the SQLite migration shipped without a Supabase mirror, which
caused 500s on `/api/bookmarks` against UAT (the bookmarks router
SELECTs an `element_id` column that didn't exist on Postgres).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read_supabase_migration() -> str:
    path = ROOT / "app" / "migrations" / "supabase" / "m047_element_bookmarks.sql"
    return path.read_text(encoding="utf-8")


def test_supabase_m047_adds_element_id_column() -> None:
    sql = _read_supabase_migration()
    # Idempotent ALTER … ADD COLUMN IF NOT EXISTS element_id …
    assert "ADD COLUMN IF NOT EXISTS element_id" in sql, sql


def test_supabase_m047_creates_element_index() -> None:
    sql = _read_supabase_migration()
    # Same index name as the SQLite migration.
    assert "idx_bookmarks_element" in sql, sql
    assert "ON bookmarks(element_id)" in sql, sql


def test_supabase_m047_replaces_two_way_check_with_three_way() -> None:
    sql = _read_supabase_migration()
    # The existing CHECK from m004 only covers diagram_id XOR package_id.
    # The new constraint must mention element_id alongside the others.
    assert "bookmarks_target_check" in sql, sql
    # All three columns referenced in the new constraint body.
    assert "element_id IS NOT NULL" in sql, sql
    assert "diagram_id IS NOT NULL" in sql, sql
    assert "package_id IS NOT NULL" in sql, sql


def test_supabase_m047_adds_unique_constraint_for_element_id() -> None:
    sql = _read_supabase_migration()
    assert "UNIQUE (user_id, element_id)" in sql, sql
