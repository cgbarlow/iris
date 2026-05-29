"""ADR-221: assert the Supabase migration ``m086_element_detail_diagram.sql``
mirrors the SQLite migration ``m080_element_detail_diagram.py`` — both add a
nullable ``detail_diagram_id`` column to ``elements`` with a matching index,
idempotently.

Mirrors the pattern in ``test_element_bookmarks_schema.py`` — a static-parser
guard so a SQLite-only column-add can't slip through and 500 on Supabase.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read_supabase_migration() -> str:
    path = ROOT / "app" / "migrations" / "supabase" / "m086_element_detail_diagram.sql"
    return path.read_text(encoding="utf-8")


def _read_sqlite_migration() -> str:
    path = ROOT / "app" / "migrations" / "m080_element_detail_diagram.py"
    return path.read_text(encoding="utf-8")


def test_supabase_m086_adds_detail_diagram_column_idempotently() -> None:
    sql = _read_supabase_migration()
    assert "ADD COLUMN IF NOT EXISTS detail_diagram_id" in sql, sql
    # FK to diagrams.
    assert "REFERENCES public.diagrams(id)" in sql, sql


def test_supabase_m086_creates_index() -> None:
    sql = _read_supabase_migration()
    assert "idx_elements_detail_diagram" in sql, sql
    assert "ON public.elements(detail_diagram_id)" in sql, sql
    assert "CREATE INDEX IF NOT EXISTS" in sql, sql


def test_supabase_m086_declares_mirror_of_sqlite() -> None:
    sql = _read_supabase_migration()
    assert "Mirrors SQLite m080" in sql, sql


def test_sqlite_m080_adds_detail_diagram_column_idempotently() -> None:
    py = _read_sqlite_migration()
    # PRAGMA-guarded ADD COLUMN.
    assert "PRAGMA table_info(elements)" in py, py
    assert 'ADD COLUMN detail_diagram_id TEXT' in py, py
    assert "REFERENCES diagrams(id)" in py, py


def test_sqlite_m080_creates_index_if_not_exists() -> None:
    py = _read_sqlite_migration()
    assert "CREATE INDEX IF NOT EXISTS idx_elements_detail_diagram" in py, py
    assert "ON elements(detail_diagram_id)" in py, py
