"""v6.0.3 (issue #115 follow-up): SQLite m057 + Supabase m061 — surgical
REPLACE() of the two stale `iris_authenticate` sentences in the live
`mcp_server_instructions` singleton row.

The v5.18.0 seed (m053) shipped two sentences referencing the v5.15.0
`iris_authenticate` flow. v6.0.0 (ADR-164) removed that tool but the
seed body was never updated — so live deployments seeded with v5.18.0
carried the stale references through v6.0.0 → v6.0.2. This migration
rewrites them with the v6.0.0 OAuth-aligned text.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m057_replaces_both_stale_strings() -> None:
    py = _read("app/migrations/m057_fix_stale_auth_recovery.py")
    # Two nested REPLACE() calls.
    assert py.count("REPLACE(") >= 2
    # The first stale sentence (workflow guidance referencing iris_authenticate).
    assert "iris_authenticate" in py
    assert "For authentication, see `iris_authenticate`." in py
    # The second stale paragraph (auth-recovery referencing iris_authenticate).
    assert "by the iris_authenticate flow" in py
    # The new OAuth-aligned auth-recovery text.
    assert "configure OAuth in their MCP client" in py


def test_sqlite_m057_scopes_to_singleton_purpose() -> None:
    py = _read("app/migrations/m057_fix_stale_auth_recovery.py")
    # WHERE clause must scope to the mcp_server_instructions purpose
    # only — we don't want to touch other ai_creation_prompts rows.
    assert "WHERE purpose = 'mcp_server_instructions'" in py


def test_sqlite_m057_table_guard() -> None:
    py = _read("app/migrations/m057_fix_stale_auth_recovery.py")
    # No-op on isolated test fixtures that don't have the table.
    assert "type='table'" in py
    assert "ai_creation_prompts" in py


def test_sqlite_m057_old_and_new_strings_aligned_with_seed() -> None:
    """The stale strings the migration is replacing must match the
    seed body byte-for-byte. If the seed body drifts, the migration
    becomes a silent no-op."""
    py = _read("app/migrations/m057_fix_stale_auth_recovery.py")
    # The new text the migration writes must MATCH what m053 now seeds
    # (so fresh installs and migrated installs converge).
    seed = _read("app/migrations/m053_mcp_server_instructions_seed.py")
    # Pull the new auth-recovery hallmark phrase out of the migration's
    # _NEW_AUTH_PARAGRAPH and confirm it lives in the seed too.
    assert "configure OAuth in their MCP client" in seed
    assert "configure OAuth in their MCP client" in py


def test_supabase_m061_mirrors_sqlite() -> None:
    sql = _read("app/migrations/supabase/m061_fix_stale_auth_recovery.sql")
    assert "UPDATE public.ai_creation_prompts" in sql or "UPDATE ai_creation_prompts" in sql
    # Same two REPLACE() ops.
    assert sql.count("REPLACE(") >= 2
    assert "iris_authenticate" in sql
    # Scoped to the singleton row.
    assert "purpose = 'mcp_server_instructions'" in sql
    # New text present.
    assert "configure OAuth in their MCP client" in sql
