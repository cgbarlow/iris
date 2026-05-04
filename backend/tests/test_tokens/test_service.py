"""Unit tests for `app.tokens.service` - token mint + verification.

Covers ADR-127 / SPEC-127-A acceptance criteria 1-5 and the "happy path",
"bad secret", "revoked", "expired", "inactive user", and "touches
last_used_at" cases enumerated in the spec's test plan.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from app.config import AuthConfig
from app.migrations.m001_roles_users import up as m001_up
from app.migrations.m041_personal_access_tokens import up as m041_up
from app.tokens.service import (
    PAT_PREFIX,
    create_pat_hasher,
    create_token,
    generate_token,
    list_tokens,
    revoke_token,
    verify_pat,
)

if TYPE_CHECKING:
    import aiosqlite


@pytest.fixture
def hasher() -> object:
    # Light parameters - tests should be fast. Real config would be heavier.
    return create_pat_hasher(
        AuthConfig(argon2_time_cost=1, argon2_memory_cost=8192, argon2_parallelism=1),
    )


@pytest.fixture
async def seeded_db(main_db: aiosqlite.Connection) -> aiosqlite.Connection:
    """Apply the user + PAT migrations, seed roles, insert one active user."""
    await m001_up(main_db)
    await m041_up(main_db)
    # Roles are an FK target for users.role — seed the minimum set.
    for role_id in ("Admin", "Architect", "Reviewer", "Viewer"):
        await main_db.execute(
            "INSERT INTO roles (id, name, description) VALUES (?, ?, ?)",
            (role_id, role_id, f"{role_id} role"),
        )
    await main_db.execute(
        "INSERT INTO users (id, username, password_hash, role, is_active, created_at)"
        " VALUES (?, ?, ?, ?, 1, ?)",
        (
            "user-1",
            "alice",
            "$argon2id$dummy",
            "Architect",
            datetime.now(tz=UTC).isoformat(),
        ),
    )
    await main_db.commit()
    return main_db


class TestGenerate:
    def test_format_is_prefix_then_secret(self, hasher: object) -> None:
        full, prefix, token_hash = generate_token(hasher)  # type: ignore[arg-type]
        assert full.startswith(PAT_PREFIX)
        # iris_pat_<8 chars>_<secret>
        tail = full[len(PAT_PREFIX):]
        parts = tail.split("_", 1)
        assert len(parts) == 2
        assert parts[0] == prefix
        assert len(parts[0]) == 8
        assert len(parts[1]) > 20
        assert token_hash.startswith("$argon2id$")

    def test_secret_portion_is_verifiable(self, hasher: object) -> None:
        full, _prefix, token_hash = generate_token(hasher)  # type: ignore[arg-type]
        tail = full[len(PAT_PREFIX):]
        secret = tail.split("_", 1)[1]
        hasher.verify(token_hash, secret)  # type: ignore[attr-defined]  # raises on mismatch


class TestVerifyPat:
    async def test_happy_path(self, seeded_db: aiosqlite.Connection, hasher: object) -> None:
        record = await create_token(seeded_db, "user-1", "laptop", None, hasher)  # type: ignore[arg-type]

        user = await verify_pat(seeded_db, record["token"], hasher)  # type: ignore[arg-type]

        assert user is not None
        assert user["id"] == "user-1"
        assert user["username"] == "alice"
        assert user["role"] == "Architect"
        assert user["auth_type"] == "pat"
        assert user["jti"] == record["id"]

    async def test_malformed_token_returns_none(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        assert await verify_pat(seeded_db, "not-a-pat", hasher) is None  # type: ignore[arg-type]
        assert await verify_pat(seeded_db, "iris_pat_", hasher) is None  # type: ignore[arg-type]
        assert await verify_pat(seeded_db, "iris_pat_short", hasher) is None  # type: ignore[arg-type]

    async def test_unknown_prefix_returns_none(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        # Well-formed shape, no matching row.
        fake = "iris_pat_12345678_abcdefghijklmnopqrstuvwxyz"
        assert await verify_pat(seeded_db, fake, hasher) is None  # type: ignore[arg-type]

    async def test_wrong_secret_returns_none(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        record = await create_token(seeded_db, "user-1", "laptop", None, hasher)  # type: ignore[arg-type]
        # Tamper: replace the secret portion.
        prefix = record["prefix"]
        tampered = f"iris_pat_{prefix}_wrongsecretwrongsecret"
        assert await verify_pat(seeded_db, tampered, hasher) is None  # type: ignore[arg-type]

    async def test_revoked_returns_none(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        record = await create_token(seeded_db, "user-1", "laptop", None, hasher)  # type: ignore[arg-type]
        await revoke_token(seeded_db, "user-1", record["id"])
        assert await verify_pat(seeded_db, record["token"], hasher) is None  # type: ignore[arg-type]

    async def test_expired_returns_none(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        past = datetime.now(tz=UTC) - timedelta(minutes=1)
        record = await create_token(seeded_db, "user-1", "laptop", past, hasher)  # type: ignore[arg-type]
        assert await verify_pat(seeded_db, record["token"], hasher) is None  # type: ignore[arg-type]

    async def test_inactive_user_returns_none(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        record = await create_token(seeded_db, "user-1", "laptop", None, hasher)  # type: ignore[arg-type]
        await seeded_db.execute("UPDATE users SET is_active = 0 WHERE id = ?", ("user-1",))
        await seeded_db.commit()
        assert await verify_pat(seeded_db, record["token"], hasher) is None  # type: ignore[arg-type]

    async def test_touches_last_used_at(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        record = await create_token(seeded_db, "user-1", "laptop", None, hasher)  # type: ignore[arg-type]

        before = await _fetch_last_used(seeded_db, record["id"])
        assert before is None

        assert await verify_pat(seeded_db, record["token"], hasher) is not None  # type: ignore[arg-type]

        after = await _fetch_last_used(seeded_db, record["id"])
        assert after is not None


class TestListAndRevoke:
    async def test_list_scoped_to_user(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        await seeded_db.execute(
            "INSERT INTO users (id, username, password_hash, role, is_active, created_at)"
            " VALUES (?, ?, ?, ?, 1, ?)",
            ("user-2", "bob", "$argon2id$dummy", "Viewer", datetime.now(tz=UTC).isoformat()),
        )
        await seeded_db.commit()
        await create_token(seeded_db, "user-1", "alice-laptop", None, hasher)  # type: ignore[arg-type]
        await create_token(seeded_db, "user-1", "alice-ci", None, hasher)  # type: ignore[arg-type]
        await create_token(seeded_db, "user-2", "bob-laptop", None, hasher)  # type: ignore[arg-type]

        alice = await list_tokens(seeded_db, "user-1")
        bob = await list_tokens(seeded_db, "user-2")

        assert {row["name"] for row in alice} == {"alice-laptop", "alice-ci"}
        assert {row["name"] for row in bob} == {"bob-laptop"}
        for row in alice + bob:
            assert "token" not in row  # never return secret from list

    async def test_revoke_requires_owner(
        self, seeded_db: aiosqlite.Connection, hasher: object,
    ) -> None:
        record = await create_token(seeded_db, "user-1", "laptop", None, hasher)  # type: ignore[arg-type]

        # Wrong user cannot revoke.
        assert await revoke_token(seeded_db, "user-999", record["id"]) is False

        # Owner can revoke, and again (idempotent).
        assert await revoke_token(seeded_db, "user-1", record["id"]) is True
        assert await revoke_token(seeded_db, "user-1", record["id"]) is True


async def _fetch_last_used(db: aiosqlite.Connection, pat_id: str) -> str | None:
    cursor = await db.execute(
        "SELECT last_used_at FROM personal_access_tokens WHERE id = ?", (pat_id,),
    )
    row = await cursor.fetchone()
    return None if row is None else row[0]
