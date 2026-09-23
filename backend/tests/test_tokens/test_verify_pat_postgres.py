"""PAT verification against a real PostgreSQL schema (ADR-247, SPEC-247-A).

Every PAT 500'd on Supabase deployments with::

    asyncpg.exceptions.UndefinedFunctionError: operator does not exist: text = uuid

because ``verify_pat`` joined ``users.id`` (TEXT, the SQLite-era user
store) to ``personal_access_tokens.user_id`` (UUID → ``profiles.id`` in
Supabase mode). SQLite's loose typing hid it: every SQLite-backed PAT
test passed.

These tests apply the real Supabase migrations (m001 roles/users, m027
profiles, m042 PATs) to a throwaway database and drive ``verify_pat``
through ``SupabaseAdapter``. They need a PostgreSQL server, so they run
only when ``IRIS_TEST_POSTGRES_DSN`` is set, e.g.::

    docker run -d --name iris-test-pg -e POSTGRES_PASSWORD=iris -p 55499:5432 postgres:16-alpine
    IRIS_TEST_POSTGRES_DSN=postgresql://postgres:iris@localhost:55499/postgres \\
        pytest tests/test_tokens/test_verify_pat_postgres.py

Each test gets its own freshly-created database, dropped afterwards, so
the DSN's own database is never modified.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from app.auth.dependencies import get_current_user
from app.config import AuthConfig
from app.db.adapter import SupabaseAdapter
from app.tokens.service import create_pat_hasher, create_token, verify_pat

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from argon2 import PasswordHasher

DSN = os.environ.get("IRIS_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    not DSN, reason="IRIS_TEST_POSTGRES_DSN not set (needs a PostgreSQL server)",
)

asyncpg = pytest.importorskip("asyncpg") if DSN else None

MIGRATIONS = Path(__file__).resolve().parents[2] / "app" / "migrations" / "supabase"

# Stand-in for the parts of Supabase's `auth` schema the migrations reference.
AUTH_STUB = """
CREATE SCHEMA auth;
CREATE TABLE auth.users (id UUID PRIMARY KEY, email TEXT, raw_user_meta_data JSONB);
CREATE FUNCTION auth.uid() RETURNS UUID LANGUAGE sql STABLE AS 'SELECT NULL::uuid';
"""


@pytest.fixture
def hasher() -> PasswordHasher:
    return create_pat_hasher(
        AuthConfig(argon2_time_cost=1, argon2_memory_cost=8192, argon2_parallelism=1),
    )


@pytest.fixture
async def pg() -> AsyncIterator[SupabaseAdapter]:
    """A fresh database with the Supabase user + PAT schema applied."""
    db_name = f"iris_test_pat_{uuid.uuid4().hex[:12]}"
    admin = await asyncpg.connect(DSN)
    await admin.execute(f'CREATE DATABASE "{db_name}"')
    try:
        base, _, _ = DSN.rpartition("/")
        pool = await asyncpg.create_pool(f"{base}/{db_name}", min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                await conn.execute(AUTH_STUB)
                for name in ("m001_roles_users.sql", "m027_profiles.sql",
                             "m042_personal_access_tokens.sql"):
                    await conn.execute((MIGRATIONS / name).read_text(encoding="utf-8"))
            yield SupabaseAdapter(pool)
        finally:
            await pool.close()
    finally:
        await admin.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        await admin.close()


async def _add_profile(
    db: SupabaseAdapter, username: str, role: str = "architect", *, mirror: bool = True,
) -> str:
    """Create a Supabase user + profile; optionally mirror it into `users`
    the way `startup._initialize_supabase` does on every deploy."""
    user_id = str(uuid.uuid4())
    await db.execute("INSERT INTO auth.users (id, email) VALUES (?::uuid, ?)",
                     (user_id, f"{username}@example.test"))
    # The m027 trigger creates a viewer stub; set the name and role we want.
    await db.execute("UPDATE profiles SET username = ?, role = ? WHERE id::text = ?",
                     (username, role, user_id))
    if mirror:
        await db.execute(
            "INSERT INTO users (id, username, password_hash, role, is_active) "
            "SELECT id::text, username, 'supabase-managed', role, is_active "
            "FROM profiles WHERE id::text = ?",
            (user_id,),
        )
    return user_id


class TestVerifyPatOnPostgres:
    async def test_happy_path(self, pg: SupabaseAdapter, hasher: PasswordHasher) -> None:
        user_id = await _add_profile(pg, "alice")
        record = await create_token(pg, user_id, "laptop", None, hasher)  # type: ignore[arg-type]

        user = await verify_pat(pg, record["token"], hasher, db_backend="supabase")  # type: ignore[arg-type]

        assert user is not None
        assert user["id"] == user_id
        assert user["username"] == "alice"
        assert user["role"] == "architect"
        assert user["auth_type"] == "pat"
        assert user["jti"] == record["id"]

    async def test_profile_not_yet_mirrored_into_users(
        self, pg: SupabaseAdapter, hasher: PasswordHasher,
    ) -> None:
        """`users` is only synced from `profiles` at startup; a user who signed
        up since the last deploy must still be able to use their PAT."""
        user_id = await _add_profile(pg, "bob", mirror=False)
        record = await create_token(pg, user_id, "cli", None, hasher)  # type: ignore[arg-type]

        user = await verify_pat(pg, record["token"], hasher, db_backend="supabase")  # type: ignore[arg-type]

        assert user is not None
        assert user["username"] == "bob"

    async def test_role_comes_from_profiles(
        self, pg: SupabaseAdapter, hasher: PasswordHasher,
    ) -> None:
        """`profiles` is the authority for role (as on the JWT path), not the
        startup-time `users` mirror."""
        user_id = await _add_profile(pg, "carol", role="viewer")
        await pg.execute("UPDATE profiles SET role = 'admin' WHERE id::text = ?", (user_id,))
        record = await create_token(pg, user_id, "agent", None, hasher)  # type: ignore[arg-type]

        user = await verify_pat(pg, record["token"], hasher, db_backend="supabase")  # type: ignore[arg-type]

        assert user is not None
        assert user["role"] == "admin"

    async def test_inactive_profile_rejected(
        self, pg: SupabaseAdapter, hasher: PasswordHasher,
    ) -> None:
        user_id = await _add_profile(pg, "dave")
        await pg.execute("UPDATE profiles SET is_active = FALSE WHERE id::text = ?", (user_id,))
        record = await create_token(pg, user_id, "laptop", None, hasher)  # type: ignore[arg-type]

        assert await verify_pat(pg, record["token"], hasher, db_backend="supabase") is None  # type: ignore[arg-type]

    async def test_touches_last_used_at(
        self, pg: SupabaseAdapter, hasher: PasswordHasher,
    ) -> None:
        user_id = await _add_profile(pg, "erin")
        record = await create_token(pg, user_id, "laptop", None, hasher)  # type: ignore[arg-type]

        await verify_pat(pg, record["token"], hasher, db_backend="supabase")  # type: ignore[arg-type]

        cursor = await pg.execute(
            "SELECT last_used_at FROM personal_access_tokens WHERE id = ?::uuid", (record["id"],),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] is not None


class TestBearerPatOnSupabaseDeployment:
    async def test_get_current_user_accepts_pat(
        self, pg: SupabaseAdapter, hasher: PasswordHasher,
    ) -> None:
        """The request path hands the deployment's backend to `verify_pat`."""
        user_id = await _add_profile(pg, "frank")
        record = await create_token(pg, user_id, "mcp", None, hasher)  # type: ignore[arg-type]
        request = SimpleNamespace(
            headers={"Authorization": f"Bearer {record['token']}"},
            app=SimpleNamespace(state=SimpleNamespace(
                config=SimpleNamespace(db_backend="supabase"),
                db_manager=SimpleNamespace(main_db=pg),
                pat_hasher=hasher,
            )),
        )

        user = await get_current_user(request)  # type: ignore[arg-type]

        assert user["id"] == user_id
        assert user["username"] == "frank"
        assert user["auth_type"] == "pat"
