"""ADR-237: assert the Supabase migration ``m088_user_collection_scope.sql``
mirrors the SQLite migration ``m082_user_collection_scope.py`` — both create
the ``user_collection_scope`` junction (user_id, collection_id) with a matching
index, idempotently.

Mirrors ``test_element_parent_element_schema.py`` — a static-parser guard so a
SQLite-only table-add can't slip through and 500 on Supabase.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read_supabase_migration() -> str:
    path = ROOT / "app" / "migrations" / "supabase" / "m088_user_collection_scope.sql"
    return path.read_text(encoding="utf-8")


def _read_sqlite_migration() -> str:
    path = ROOT / "app" / "migrations" / "m082_user_collection_scope.py"
    return path.read_text(encoding="utf-8")


def test_supabase_m088_creates_table_idempotently() -> None:
    sql = _read_supabase_migration()
    assert "CREATE TABLE IF NOT EXISTS user_collection_scope" in sql, sql
    # user_id is the Supabase profiles UUID; collection_id is the TEXT id.
    assert "user_id       UUID" in sql or "user_id UUID" in sql, sql
    assert "REFERENCES public.profiles(id)" in sql, sql
    assert "REFERENCES public.collections(id)" in sql, sql
    assert "PRIMARY KEY (user_id, collection_id)" in sql, sql


def test_supabase_m088_creates_index() -> None:
    sql = _read_supabase_migration()
    assert "CREATE INDEX IF NOT EXISTS idx_ucs_user" in sql, sql
    assert "ON public.user_collection_scope(user_id)" in sql, sql


def test_supabase_m088_enables_rls() -> None:
    sql = _read_supabase_migration()
    assert "ENABLE ROW LEVEL SECURITY" in sql, sql


def test_supabase_m088_declares_mirror_of_sqlite() -> None:
    sql = _read_supabase_migration()
    assert "Mirrors SQLite m082" in sql, sql


def test_sqlite_m082_creates_table_idempotently() -> None:
    py = _read_sqlite_migration()
    assert "CREATE TABLE IF NOT EXISTS user_collection_scope" in py, py
    assert "REFERENCES users(id)" in py, py
    assert "REFERENCES collections(id)" in py, py
    assert "PRIMARY KEY (user_id, collection_id)" in py, py


def test_sqlite_m082_creates_index_if_not_exists() -> None:
    py = _read_sqlite_migration()
    assert "CREATE INDEX IF NOT EXISTS idx_ucs_user" in py, py
    assert "ON user_collection_scope(user_id)" in py, py
