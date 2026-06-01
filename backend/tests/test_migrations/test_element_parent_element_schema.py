"""ADR-231: assert the Supabase migration ``m087_element_parent_element.sql``
mirrors the SQLite migration ``m081_element_parent_element.py`` — both add a
nullable ``parent_element_id`` self-referencing column to ``elements`` with a
matching index, idempotently.

Mirrors ``test_element_detail_diagram_schema.py`` — a static-parser guard so a
SQLite-only column-add can't slip through and 500 on Supabase.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read_supabase_migration() -> str:
    path = ROOT / "app" / "migrations" / "supabase" / "m087_element_parent_element.sql"
    return path.read_text(encoding="utf-8")


def _read_sqlite_migration() -> str:
    path = ROOT / "app" / "migrations" / "m081_element_parent_element.py"
    return path.read_text(encoding="utf-8")


def test_supabase_m087_adds_parent_element_column_idempotently() -> None:
    sql = _read_supabase_migration()
    assert "ADD COLUMN IF NOT EXISTS parent_element_id" in sql, sql
    # Self-referencing FK to elements.
    assert "REFERENCES public.elements(id)" in sql, sql


def test_supabase_m087_creates_index() -> None:
    sql = _read_supabase_migration()
    assert "idx_elements_parent_element" in sql, sql
    assert "ON public.elements(parent_element_id)" in sql, sql
    assert "CREATE INDEX IF NOT EXISTS" in sql, sql


def test_supabase_m087_declares_mirror_of_sqlite() -> None:
    sql = _read_supabase_migration()
    assert "Mirrors SQLite m081" in sql, sql


def test_sqlite_m081_adds_parent_element_column_idempotently() -> None:
    py = _read_sqlite_migration()
    # PRAGMA-guarded ADD COLUMN.
    assert "PRAGMA table_info(elements)" in py, py
    assert "ADD COLUMN parent_element_id TEXT" in py, py
    assert "REFERENCES elements(id)" in py, py


def test_sqlite_m081_creates_index_if_not_exists() -> None:
    py = _read_sqlite_migration()
    assert "CREATE INDEX IF NOT EXISTS idx_elements_parent_element" in py, py
    assert "ON elements(parent_element_id)" in py, py
