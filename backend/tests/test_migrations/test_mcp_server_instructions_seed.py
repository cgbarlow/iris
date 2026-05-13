"""v5.18.0 (ADR-163, SPEC-163-A): static-parser test for the SQLite
m053 + Supabase m057 seed migrations that insert the singleton
`mcp_server_instructions` row into `ai_creation_prompts`.

Verifies:
- both migrations exist
- both reference the new purpose value
- both insert at layer=base with notation/diagram_type NULL
- both are idempotent (INSERT OR IGNORE / ON CONFLICT DO NOTHING)
- the seeded body contains the orient-first protocol + discovery markers
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m053_inserts_singleton_row() -> None:
    py = _read("app/migrations/m053_mcp_server_instructions_seed.py")
    assert "INSERT OR IGNORE INTO ai_creation_prompts" in py
    assert "mcp-server-instructions-v1" in py
    assert "mcp_server_instructions" in py
    # NULL for notation and diagram_type — singleton row.
    assert "VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, 0, 1)" in py


def test_sqlite_m053_seed_body_contains_protocol_markers() -> None:
    py = _read("app/migrations/m053_mcp_server_instructions_seed.py")
    assert "ORIENT-FIRST PROTOCOL" in py
    assert "DISCOVERY TOOLS" in py
    assert "WORKFLOW GUIDANCE" in py
    assert "AUTH RECOVERY" in py


def test_sqlite_m053_is_idempotent() -> None:
    py = _read("app/migrations/m053_mcp_server_instructions_seed.py")
    # Idempotency guards: INSERT OR IGNORE on the unique id, plus a
    # table-existence check that no-ops on isolated test fixtures.
    assert "INSERT OR IGNORE" in py
    assert "ai_creation_prompts" in py


def test_supabase_m057_inserts_singleton_row() -> None:
    sql = _read("app/migrations/supabase/m057_mcp_server_instructions_seed.sql")
    assert "INSERT INTO public.ai_creation_prompts" in sql
    assert "'mcp-server-instructions-v1'" in sql
    assert "'mcp_server_instructions'" in sql
    assert "'base'" in sql
    assert "ON CONFLICT (id) DO NOTHING" in sql


def test_supabase_m057_seed_body_matches_sqlite() -> None:
    sql = _read("app/migrations/supabase/m057_mcp_server_instructions_seed.sql")
    # Same canonical body markers as the SQLite seed.
    assert "ORIENT-FIRST PROTOCOL" in sql
    assert "DISCOVERY TOOLS" in sql
    assert "WORKFLOW GUIDANCE" in sql
    assert "AUTH RECOVERY" in sql
