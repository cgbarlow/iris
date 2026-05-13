"""Migration 054: OAuth 2.1 Authorization Server tables (ADR-164, SPEC-164-A).

v6.0.0 replaces the v5.15.0 pairing-code flow with full OAuth 2.1 for the
iris-mcp HTTP transport. This migration:

1. Drops the `pairing_codes` table (v5.15.0 / ADR-160 remnant — superseded).
2. Creates `oauth_clients` for Dynamic Client Registration (RFC 7591).
3. Creates `oauth_authorization_codes` for short-lived PKCE codes.
4. Creates `oauth_refresh_tokens` with family-id rotation/theft detection
   (mirrors the v5.x `refresh_tokens` schema pattern from m001).

Access tokens are issued as JWTs (HS256, existing JWT_SECRET) and are not
stored — they're stateless and validated by `get_current_user` via the
existing JWT pipeline. Refresh tokens are DB-stored for revocability.

Idempotent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m054_oauth_tables"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    # 1. Drop the v5.15.0 pairing-flow remnant.
    await db.execute("DROP TABLE IF EXISTS pairing_codes")

    # 2. oauth_clients — DCR registrations.
    await db.execute(
        "CREATE TABLE IF NOT EXISTS oauth_clients ("
        "  client_id TEXT PRIMARY KEY,"
        "  client_secret_hash TEXT,"
        "  client_name TEXT NOT NULL,"
        "  redirect_uris TEXT NOT NULL,"
        "  grant_types TEXT NOT NULL DEFAULT '[\"authorization_code\",\"refresh_token\"]',"
        "  token_endpoint_auth_method TEXT NOT NULL DEFAULT 'none',"
        "  created_at TEXT NOT NULL,"
        "  last_used_at TEXT"
        ")"
    )

    # 3. oauth_authorization_codes — short-lived PKCE codes.
    await db.execute(
        "CREATE TABLE IF NOT EXISTS oauth_authorization_codes ("
        "  code TEXT PRIMARY KEY,"
        "  client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,"
        "  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
        "  redirect_uri TEXT NOT NULL,"
        "  code_challenge TEXT NOT NULL,"
        "  code_challenge_method TEXT NOT NULL DEFAULT 'S256',"
        "  scope TEXT NOT NULL DEFAULT 'iris',"
        "  expires_at TEXT NOT NULL,"
        "  used_at TEXT"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_codes_expires"
        " ON oauth_authorization_codes(expires_at)"
    )

    # 4. oauth_refresh_tokens — DB-stored for revocability, family-id for
    #    rotation + theft detection (mirrors v5.x refresh_tokens pattern).
    await db.execute(
        "CREATE TABLE IF NOT EXISTS oauth_refresh_tokens ("
        "  id TEXT PRIMARY KEY,"
        "  client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,"
        "  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
        "  family_id TEXT NOT NULL,"
        "  expires_at TEXT NOT NULL,"
        "  created_at TEXT NOT NULL,"
        "  used_at TEXT,"
        "  revoked INTEGER NOT NULL DEFAULT 0"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_refresh_user"
        " ON oauth_refresh_tokens(user_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_refresh_family"
        " ON oauth_refresh_tokens(family_id)"
    )

    await db.commit()
