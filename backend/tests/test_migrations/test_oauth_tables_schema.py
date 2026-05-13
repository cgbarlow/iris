"""v6.0.0 (ADR-164, SPEC-164-A): static-parser test for SQLite m054 +
Supabase m058 OAuth-tables migrations.

Verifies:
- Both migrations drop the v5.15.0 pairing_codes table.
- Both create oauth_clients, oauth_authorization_codes, oauth_refresh_tokens.
- Foreign-key references to users (SQLite) / profiles (Supabase).
- Required indexes present.
- Idempotency (IF NOT EXISTS / DROP IF EXISTS).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m054_drops_pairing_codes() -> None:
    py = _read("app/migrations/m054_oauth_tables.py")
    assert "DROP TABLE IF EXISTS pairing_codes" in py


def test_sqlite_m054_creates_oauth_clients() -> None:
    py = _read("app/migrations/m054_oauth_tables.py")
    assert "CREATE TABLE IF NOT EXISTS oauth_clients" in py
    for col in (
        "client_id", "client_secret_hash", "client_name", "redirect_uris",
        "grant_types", "token_endpoint_auth_method", "created_at", "last_used_at",
    ):
        assert col in py, f"oauth_clients missing column {col}"


def test_sqlite_m054_creates_oauth_authorization_codes_with_index() -> None:
    py = _read("app/migrations/m054_oauth_tables.py")
    assert "CREATE TABLE IF NOT EXISTS oauth_authorization_codes" in py
    for col in (
        "code", "client_id", "user_id", "redirect_uri",
        "code_challenge", "code_challenge_method", "scope",
        "expires_at", "used_at",
    ):
        assert col in py, f"oauth_authorization_codes missing column {col}"
    assert "REFERENCES oauth_clients(client_id) ON DELETE CASCADE" in py
    assert "REFERENCES users(id) ON DELETE CASCADE" in py
    assert "idx_oauth_codes_expires" in py


def test_sqlite_m054_creates_oauth_refresh_tokens_with_indexes() -> None:
    py = _read("app/migrations/m054_oauth_tables.py")
    assert "CREATE TABLE IF NOT EXISTS oauth_refresh_tokens" in py
    for col in (
        "id", "client_id", "user_id", "family_id",
        "expires_at", "created_at", "used_at", "revoked",
    ):
        assert col in py, f"oauth_refresh_tokens missing column {col}"
    assert "idx_oauth_refresh_user" in py
    assert "idx_oauth_refresh_family" in py


def test_sqlite_m054_is_idempotent() -> None:
    py = _read("app/migrations/m054_oauth_tables.py")
    assert "CREATE TABLE IF NOT EXISTS" in py
    assert "CREATE INDEX IF NOT EXISTS" in py
    assert "DROP TABLE IF EXISTS" in py


def test_supabase_m058_mirrors_sqlite() -> None:
    sql = _read("app/migrations/supabase/m058_oauth_tables.sql")
    assert "DROP TABLE IF EXISTS public.pairing_codes" in sql
    assert "CREATE TABLE IF NOT EXISTS public.oauth_clients" in sql
    assert "CREATE TABLE IF NOT EXISTS public.oauth_authorization_codes" in sql
    assert "CREATE TABLE IF NOT EXISTS public.oauth_refresh_tokens" in sql


def test_supabase_m058_uses_uuid_profile_references() -> None:
    sql = _read("app/migrations/supabase/m058_oauth_tables.sql")
    assert "REFERENCES profiles(id) ON DELETE CASCADE" in sql
    # JSONB for redirect_uris in Postgres.
    assert "JSONB" in sql


def test_supabase_m058_has_rls_enabled() -> None:
    sql = _read("app/migrations/supabase/m058_oauth_tables.sql")
    assert "ALTER TABLE public.oauth_clients ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE public.oauth_authorization_codes ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE public.oauth_refresh_tokens ENABLE ROW LEVEL SECURITY" in sql
