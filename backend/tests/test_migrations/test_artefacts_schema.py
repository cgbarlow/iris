"""v6.2.0 (ADR-179, SPEC-179-A): static-parser tests for the SQLite
m060 + Supabase m064 migrations that create the `artefacts` table.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m060 ────────────────────────────────────────────────────────


def test_sqlite_m060_file_exists() -> None:
    assert (ROOT / "app/migrations/m060_artefacts_table.py").exists()


def test_sqlite_m060_creates_artefacts_table() -> None:
    py = _read("app/migrations/m060_artefacts_table.py")
    assert "CREATE TABLE IF NOT EXISTS artefacts" in py
    for col in (
        "id TEXT PRIMARY KEY",
        "filename TEXT NOT NULL",
        "mime TEXT NOT NULL",
        "bytes BLOB NOT NULL",
        "size_bytes INTEGER NOT NULL",
        "source_kind TEXT NOT NULL",
        "source_ref TEXT",
        "created_by TEXT",
        "created_at TEXT NOT NULL",
    ):
        assert col in py, f"missing column declaration: {col!r}"


def test_sqlite_m060_creates_source_ref_index() -> None:
    py = _read("app/migrations/m060_artefacts_table.py")
    assert "CREATE INDEX IF NOT EXISTS idx_artefacts_source_ref" in py
    assert "ON artefacts(source_ref)" in py


def test_sqlite_m060_registered_in_startup() -> None:
    startup = _read("app/startup.py")
    assert "from app.migrations.m060_artefacts_table import up as m060_up" in startup
    assert "await m060_up(main)" in startup


# ── Supabase m064 ──────────────────────────────────────────────────────


def test_supabase_m064_file_exists() -> None:
    assert (ROOT / "app/migrations/supabase/m064_artefacts_table.sql").exists()


def test_supabase_m064_creates_artefacts_table() -> None:
    sql = _read("app/migrations/supabase/m064_artefacts_table.sql")
    assert "CREATE TABLE IF NOT EXISTS public.artefacts" in sql
    # bytes column uses BYTEA on Postgres, not BLOB.
    assert "bytes BYTEA NOT NULL" in sql
    assert "source_kind TEXT NOT NULL" in sql
    assert "source_ref TEXT" in sql


def test_supabase_m064_creates_source_ref_index() -> None:
    sql = _read("app/migrations/supabase/m064_artefacts_table.sql")
    assert "CREATE INDEX IF NOT EXISTS idx_artefacts_source_ref" in sql
    assert "ON public.artefacts(source_ref)" in sql
