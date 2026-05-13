"""v6.0.1 (issue #115): static-parser test for SQLite m055 + Supabase
m059 migrations that fix the orient-protocol tool name in the live
`mcp_server_instructions` singleton row.

Verifies:
- Both migrations REPLACE the wrong name with the right one.
- Both scope the UPDATE to purpose='mcp_server_instructions'.
- Idempotency (REPLACE is no-op if substring absent).
- The underlying m053 / m057 seeds now use the correct name (so fresh
  installs don't regress).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m055_replaces_wrong_tool_name() -> None:
    py = _read("app/migrations/m055_fix_orient_protocol_tool_name.py")
    assert "REPLACE(prompt_text" in py
    assert "'iris_package_hierarchy'" in py
    assert "'package_hierarchy'" in py
    assert "purpose = 'mcp_server_instructions'" in py


def test_sqlite_m055_table_existence_guard() -> None:
    py = _read("app/migrations/m055_fix_orient_protocol_tool_name.py")
    # Guard so the migration no-ops in isolated test fixtures.
    assert "ai_creation_prompts" in py
    assert "type='table'" in py


def test_supabase_m059_mirrors_sqlite() -> None:
    sql = _read("app/migrations/supabase/m059_fix_orient_protocol_tool_name.sql")
    assert "UPDATE public.ai_creation_prompts" in sql
    assert "REPLACE(prompt_text" in sql
    assert "'iris_package_hierarchy'" in sql
    assert "'package_hierarchy'" in sql
    assert "purpose = 'mcp_server_instructions'" in sql


def test_m053_seeded_body_uses_correct_tool_name() -> None:
    """The v6.0.1 fix is point-in-time correction of live data; the
    underlying seed must also use the correct name so fresh installs
    don't regress."""
    py = _read("app/migrations/m053_mcp_server_instructions_seed.py")
    assert "iris_package_hierarchy" not in py
    assert "package_hierarchy" in py


def test_supabase_m057_seeded_body_uses_correct_tool_name() -> None:
    sql = _read("app/migrations/supabase/m057_mcp_server_instructions_seed.sql")
    assert "iris_package_hierarchy" not in sql
    assert "package_hierarchy" in sql
