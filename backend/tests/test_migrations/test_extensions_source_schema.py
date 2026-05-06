"""v5.5.0 (issue #48): static-parser test asserting the new
Supabase migration `m048_extensions_source.sql` mirrors the SQLite
migration `m046_extensions_source.py`."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_supabase_m048_adds_source_method_column() -> None:
    sql = _read("app/migrations/supabase/m048_extensions_source.sql")
    assert "ADD COLUMN IF NOT EXISTS source_method" in sql
    assert "DEFAULT 'local'" in sql


def test_supabase_m048_adds_source_url_column() -> None:
    sql = _read("app/migrations/supabase/m048_extensions_source.sql")
    assert "ADD COLUMN IF NOT EXISTS source_url" in sql


def test_supabase_m048_adds_latest_version_columns() -> None:
    sql = _read("app/migrations/supabase/m048_extensions_source.sql")
    assert "ADD COLUMN IF NOT EXISTS latest_version" in sql
    assert "ADD COLUMN IF NOT EXISTS latest_version_checked_at" in sql


def test_sqlite_m046_adds_same_columns() -> None:
    py = _read("app/migrations/m046_extensions_source.py")
    for col in (
        "source_method",
        "source_url",
        "latest_version",
        "latest_version_checked_at",
    ):
        assert f'ADD COLUMN {col}' in py, f"SQLite m046 should ADD COLUMN {col}: {py}"
