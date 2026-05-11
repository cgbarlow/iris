"""v5.8.1: static-parser test asserting RLS is enabled on graph_settings.

The table was originally added by m039 (and re-created defensively at
runtime in startup._initialize_supabase as a v5.7.2 fix). Neither
location enabled RLS, so the Supabase advisor flagged graph_settings
as a public table without Row Level Security — out of line with the
deny-all posture ADR-095 set for every other table in the schema.

The fix is one ALTER statement in each place. These tests pin the
fix so future edits don't regress.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_supabase_m039_enables_rls_on_graph_settings() -> None:
    sql = _read("app/migrations/supabase/m039_graph_settings.sql")
    assert "ALTER TABLE graph_settings ENABLE ROW LEVEL SECURITY" in sql


def test_supabase_m039_alters_after_create_table() -> None:
    """The ALTER must come after the CREATE TABLE; otherwise Postgres
    rejects the statement on a fresh DB where the table doesn't exist
    yet."""
    sql = _read("app/migrations/supabase/m039_graph_settings.sql")
    create_idx = sql.find("CREATE TABLE")
    alter_idx = sql.find("ALTER TABLE graph_settings ENABLE ROW LEVEL SECURITY")
    assert create_idx != -1
    assert alter_idx != -1
    assert create_idx < alter_idx


def test_startup_enables_rls_on_graph_settings_after_runtime_create() -> None:
    """startup._initialize_supabase re-creates the table at runtime as
    a defensive fallback (v5.7.2). It must also enable RLS so that
    deployments which never ran the SQL migration still get the right
    posture."""
    py = _read("app/startup.py")
    assert "graph_settings ENABLE ROW LEVEL SECURITY" in py
    # The ALTER must appear after the runtime CREATE TABLE block in the
    # same function. We anchor on the comment referencing ADR-117 v5.7.2.
    create_idx = py.find("CREATE TABLE IF NOT EXISTS graph_settings")
    alter_idx = py.find("ALTER TABLE graph_settings ENABLE ROW LEVEL SECURITY")
    assert create_idx != -1
    assert alter_idx != -1
    assert create_idx < alter_idx
