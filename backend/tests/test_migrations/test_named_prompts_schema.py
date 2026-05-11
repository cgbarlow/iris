"""v5.9.0 (ADR-154, SPEC-154-A): static-parser test asserting the
SQLite migration m048_named_prompts.py and its Supabase mirror
m052_named_prompts.sql both create the `prompts` table with the
expected schema, constraints, indexes, and (Supabase) RLS policies."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m048_creates_prompts_table() -> None:
    py = _read("app/migrations/m048_named_prompts.py")
    assert "CREATE TABLE IF NOT EXISTS prompts" in py
    # All required columns appear in the CREATE TABLE body.
    for column in (
        "id",
        "scope_type",
        "scope_id",
        "name",
        "description",
        "body",
        "created_at",
        "updated_at",
        "created_by",
    ):
        assert column in py, f"column {column!r} missing from m048 CREATE TABLE"


def test_sqlite_m048_has_unique_and_check_constraints() -> None:
    py = _read("app/migrations/m048_named_prompts.py")
    # Per-scope uniqueness on prompt name.
    assert "UNIQUE (scope_type, scope_id, name)" in py
    # scope_type CHECK constraint.
    assert "scope_type IN ('collection','set')" in py.replace('"', "'")


def test_sqlite_m048_creates_scope_index() -> None:
    py = _read("app/migrations/m048_named_prompts.py")
    assert "CREATE INDEX IF NOT EXISTS idx_prompts_scope" in py
    assert "ON prompts(scope_type, scope_id)" in py


def test_sqlite_m048_is_idempotent() -> None:
    py = _read("app/migrations/m048_named_prompts.py")
    # Idempotency guards: CREATE TABLE IF NOT EXISTS and CREATE INDEX
    # IF NOT EXISTS mean rerunning on a partially-applied DB is safe.
    assert "CREATE TABLE IF NOT EXISTS prompts" in py
    assert "CREATE INDEX IF NOT EXISTS" in py


def test_supabase_m052_creates_prompts_table() -> None:
    sql = _read("app/migrations/supabase/m052_named_prompts.sql")
    assert "CREATE TABLE IF NOT EXISTS public.prompts" in sql
    for column in (
        "id",
        "scope_type",
        "scope_id",
        "name",
        "description",
        "body",
        "created_at",
        "updated_at",
        "created_by",
    ):
        assert column in sql, f"column {column!r} missing from m052 CREATE TABLE"
    assert "UNIQUE (scope_type, scope_id, name)" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_prompts_scope" in sql


def test_supabase_m052_has_rls_policies() -> None:
    sql = _read("app/migrations/supabase/m052_named_prompts.sql")
    # RLS enabled.
    assert "ENABLE ROW LEVEL SECURITY" in sql
    # Anonymous read + authenticated write — same posture as collections/sets.
    assert "prompts_anon_read" in sql
    assert "FOR SELECT" in sql
    assert "prompts_auth_insert" in sql
    assert "prompts_auth_update" in sql
    assert "prompts_auth_delete" in sql
