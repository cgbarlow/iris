"""v5.5.8 (issue #55 follow-up): static-parser test for the migration
that converts extensions.latest_version_checked_at from TEXT to
TIMESTAMPTZ.

Pre-fix the column was TEXT but the asyncpg adapter auto-converts
ISO strings to datetime objects; binding a datetime to a TEXT column
raised DataError and crashed the worker mid-response, so
/api/extensions/{id}/check-update returned a 500 with no CORS headers.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "app" / "migrations" / "supabase" / "m050_latest_version_checked_at_timestamptz.sql"


def test_migration_exists() -> None:
    assert MIGRATION.is_file()


def test_alters_column_to_timestamptz() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ALTER TABLE extensions" in sql
    assert "ALTER COLUMN latest_version_checked_at" in sql
    assert "TYPE TIMESTAMPTZ" in sql
    assert "USING latest_version_checked_at::timestamptz" in sql


def test_idempotent_via_information_schema_guard() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "information_schema.columns" in sql
    assert "data_type = 'text'" in sql
