"""Tests for role and permission seed data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.migrations.m001_roles_users import up as m001_up
from app.migrations.seed import (
    ROLE_PERMISSIONS,
    seed_roles_and_permissions,
)

if TYPE_CHECKING:
    import aiosqlite


class TestSeedRolesAndPermissions:
    """Verify seed data matches SPEC-005-A permission matrix."""

    async def test_seeds_four_roles(self, main_db: aiosqlite.Connection) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        cursor = await main_db.execute("SELECT COUNT(*) FROM roles")
        row = await cursor.fetchone()
        assert row[0] == 4

    async def test_role_ids_match_spec(self, main_db: aiosqlite.Connection) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        cursor = await main_db.execute("SELECT id FROM roles ORDER BY id")
        role_ids = {row[0] for row in await cursor.fetchall()}
        assert role_ids == {"admin", "architect", "reviewer", "viewer"}

    async def test_admin_has_27_permissions(
        self, main_db: aiosqlite.Connection
    ) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        cursor = await main_db.execute(
            "SELECT COUNT(*) FROM role_permissions WHERE role_id='admin'"
        )
        row = await cursor.fetchone()
        assert row[0] == len(ROLE_PERMISSIONS["admin"])

    async def test_architect_permissions(
        self, main_db: aiosqlite.Connection
    ) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        cursor = await main_db.execute(
            "SELECT permission FROM role_permissions WHERE role_id='architect'"
        )
        perms = {row[0] for row in await cursor.fetchall()}
        assert "entity.create" in perms
        assert "entity.delete" not in perms
        assert "version.rollback" not in perms
        assert "user.create" not in perms

    async def test_reviewer_permissions(
        self, main_db: aiosqlite.Connection
    ) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        cursor = await main_db.execute(
            "SELECT permission FROM role_permissions WHERE role_id='reviewer'"
        )
        perms = {row[0] for row in await cursor.fetchall()}
        assert "comment.create" in perms
        assert "entity.create" not in perms
        assert "entity.read" in perms

    async def test_viewer_permissions(
        self, main_db: aiosqlite.Connection
    ) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        cursor = await main_db.execute(
            "SELECT permission FROM role_permissions WHERE role_id='viewer'"
        )
        perms = {row[0] for row in await cursor.fetchall()}
        assert "entity.read" in perms
        assert "comment.read" in perms
        assert "comment.create" not in perms
        assert "bookmark.manage" in perms

    async def test_seed_is_idempotent(self, main_db: aiosqlite.Connection) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        await seed_roles_and_permissions(main_db)  # Run twice
        cursor = await main_db.execute("SELECT COUNT(*) FROM roles")
        row = await cursor.fetchone()
        assert row[0] == 4

    async def test_total_permission_mappings(
        self, main_db: aiosqlite.Connection
    ) -> None:
        await m001_up(main_db)
        await seed_roles_and_permissions(main_db)
        cursor = await main_db.execute(
            "SELECT COUNT(*) FROM role_permissions"
        )
        row = await cursor.fetchone()
        total = sum(len(p) for p in ROLE_PERMISSIONS.values())
        assert row[0] == total
