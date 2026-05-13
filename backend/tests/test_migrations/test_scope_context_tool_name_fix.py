"""v6.0.2 (issue #115 follow-up): SQLite m056 + Supabase m060 — fix the
orient-protocol tool name in per-scope `mcp_system_context` fields.

v6.0.1's m055/m059 corrected the server-wide singleton; m056/m060
correct the per-scope content on `sets` and `collections`.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m056_replaces_in_sets_and_collections() -> None:
    py = _read("app/migrations/m056_fix_scope_context_tool_name.py")
    assert "REPLACE(mcp_system_context" in py
    assert "'iris_package_hierarchy'" in py
    assert "'package_hierarchy'" in py
    # Both tables targeted.
    assert '_fix(db, "sets")' in py
    assert '_fix(db, "collections")' in py


def test_sqlite_m056_table_and_column_guards() -> None:
    py = _read("app/migrations/m056_fix_scope_context_tool_name.py")
    # Guards so the migration no-ops on isolated test fixtures.
    assert "type='table'" in py
    assert "PRAGMA table_info" in py
    assert '"mcp_system_context" not in columns' in py


def test_sqlite_m056_skips_null_rows() -> None:
    py = _read("app/migrations/m056_fix_scope_context_tool_name.py")
    # WHERE clause avoids updating rows with NULL mcp_system_context.
    assert "WHERE mcp_system_context IS NOT NULL" in py


def test_supabase_m060_mirrors_sqlite() -> None:
    sql = _read("app/migrations/supabase/m060_fix_scope_context_tool_name.sql")
    assert "UPDATE public.sets" in sql
    assert "UPDATE public.collections" in sql
    assert "REPLACE(mcp_system_context" in sql
    assert "'iris_package_hierarchy'" in sql
    assert "'package_hierarchy'" in sql
    # Both UPDATEs scope to non-null rows.
    assert sql.count("WHERE mcp_system_context IS NOT NULL") == 2
