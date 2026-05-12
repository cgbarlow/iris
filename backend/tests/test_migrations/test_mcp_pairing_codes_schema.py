"""v5.15.0 (ADR-160, SPEC-160-A): static-parser test asserting the
SQLite migration m052_mcp_pairing_codes.py and its Supabase mirror
m056_mcp_pairing_codes.sql both create the `pairing_codes` table with
the expected schema, indexes, and (Supabase) RLS policies."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m052_creates_pairing_codes_table() -> None:
    py = _read("app/migrations/m052_mcp_pairing_codes.py")
    assert "CREATE TABLE IF NOT EXISTS pairing_codes" in py
    for column in (
        "code",
        "user_id",
        "created_at",
        "expires_at",
        "exchanged_at",
        "issued_pat_id",
        "issued_pat_name",
    ):
        assert column in py, f"column {column!r} missing from m052 CREATE TABLE"


def test_sqlite_m052_creates_user_and_expires_indexes() -> None:
    py = _read("app/migrations/m052_mcp_pairing_codes.py")
    assert "CREATE INDEX IF NOT EXISTS idx_pairing_codes_user" in py
    assert "CREATE INDEX IF NOT EXISTS idx_pairing_codes_expires" in py


def test_sqlite_m052_is_idempotent() -> None:
    py = _read("app/migrations/m052_mcp_pairing_codes.py")
    assert "CREATE TABLE IF NOT EXISTS pairing_codes" in py
    assert "CREATE INDEX IF NOT EXISTS" in py


def test_supabase_m056_creates_pairing_codes_table_with_rls() -> None:
    sql = _read("app/migrations/supabase/m056_mcp_pairing_codes.sql")
    assert "CREATE TABLE IF NOT EXISTS public.pairing_codes" in sql
    for column in (
        "code",
        "user_id",
        "created_at",
        "expires_at",
        "exchanged_at",
        "issued_pat_id",
        "issued_pat_name",
    ):
        assert column in sql, f"column {column!r} missing from m056 CREATE TABLE"
    assert "CREATE INDEX IF NOT EXISTS idx_pairing_codes_user" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_pairing_codes_expires" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "pairing_codes_owner_select" in sql
    assert "pairing_codes_owner_insert" in sql
    assert "pairing_codes_owner_update" in sql
    assert "pairing_codes_owner_delete" in sql
